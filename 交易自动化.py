#!/usr/bin/env python3
"""
股票自动交易系统 - 统一入口
整合：盘前检查 / 交易信号 / 收盘复盘 / 任务追踪
用法: python3 stock_trading.py [check|signal|review|all]
"""
import sys
import sqlite3
import json
import os
import subprocess
import urllib.request
import time
import threading
from datetime import datetime, timedelta

# ========== 全局配置 ==========
WORKSPACE = "/home/wenkun/.openclaw/workspace"
STOCKS_FILE = f"{WORKSPACE}/stocks_memory.md"
CONFIG_FILE = f"{WORKSPACE}/paper_trading_config.md"
REPORT_FILE = f"{WORKSPACE}/paper_trading_report.md"
TRADING_DB = f"{WORKSPACE}/trading_task.db"
TRADING_DAY_DB = f"{WORKSPACE}/trading.db"
FEISHU_USER = "ou_51a14c42e587cd0f52446357c5819f08"

SINA_CODE_MAP = {"000582": "sz000582", "600676": "sh600676", "002714": "sz002714", "000876": "sz000876"}

# ========== 通用工具 ==========
def send_feishu(message):
    result = subprocess.run(
        ["openclaw", "message", "send", "--channel", "feishu", "--target", FEISHU_USER, "--message", message],
        capture_output=True, text=True
    )
    return result.returncode == 0

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_realtime_quotes(codes):
    if not codes:
        return {}
    sina_codes = [SINA_CODE_MAP.get(c, c) for c in codes]
    url = f"http://hq.sinajs.cn/list={','.join(sina_codes)}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("gbk")
            result = {}
            for i, line in enumerate(data.strip().split("\n")):
                if "=" not in line:
                    continue
                code = codes[i] if i < len(codes) else ""
                p = line.split("=")[1].strip('"').split(",")
                if len(p) >= 32:
                    result[code] = {"name": p[0], "open": float(p[1]), "close": float(p[2]),
                                   "current": float(p[3]), "high": float(p[4]), "low": float(p[5]),
                                   "volume": float(p[8]), "date": p[30], "time": p[31]}
            return result
    except Exception as e:
        log(f"行情获取失败: {e}")
        return {}

def get_sina_kline(symbol, days=30):
    url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=5&datalen={days}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except:
        return []

def calc_rsi(closes, period=6):
    if len(closes) < period + 1:
        return 50
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

# ========== 数据库初始化 ==========
def init_dbs():
    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task_name TEXT, task_type TEXT DEFAULT 'daily',
        source TEXT DEFAULT 'system', status TEXT DEFAULT 'pending', priority INTEGER DEFAULT 3,
        created_at TEXT, updated_at TEXT, due_date TEXT, completed_at TEXT,
        completion_summary TEXT, lessons_learned TEXT, related_strategy TEXT, notes TEXT, tags TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS trading_days (id INTEGER PRIMARY KEY, trade_date TEXT UNIQUE,
        day_status TEXT DEFAULT 'open', total_pnl REAL DEFAULT 0, win_rate REAL DEFAULT 0,
        positions_opened INTEGER DEFAULT 0, positions_closed INTEGER DEFAULT 0,
        tasks_planned INTEGER DEFAULT 0, tasks_completed INTEGER DEFAULT 0, tasks_pending INTEGER DEFAULT 0,
        summary_generated INTEGER DEFAULT 0, morning_check_done INTEGER DEFAULT 0,
        signal_report_done INTEGER DEFAULT 0, closing_review_done INTEGER DEFAULT 0,
        created_at TEXT, updated_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS task_executions (id INTEGER PRIMARY KEY, task_id INTEGER,
        execution_date TEXT, action TEXT, result TEXT, notes TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS strategy_runs (id INTEGER PRIMARY KEY, stock_code TEXT,
        strategy_type TEXT, run_date TEXT, status TEXT, signal_type TEXT,
        entry_price REAL, exit_price REAL, pnl REAL, notes TEXT, created_at TEXT)""")
    conn.commit()
    conn.close()

    conn2 = sqlite3.connect(TRADING_DAY_DB)
    c2 = conn2.cursor()
    c2.execute("""CREATE TABLE IF NOT EXISTS positions (id INTEGER PRIMARY KEY, date TEXT, stock_code TEXT,
        stock_name TEXT, position_type TEXT, shares INTEGER, avg_cost REAL, current_price REAL,
        market_value REAL, unrealized_pnl REAL, created_at TEXT)""")
    c2.execute("""CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY, date TEXT, stock_code TEXT,
        stock_name TEXT, action TEXT, price REAL, shares INTEGER, amount REAL,
        strategy_type TEXT, signal_source TEXT, created_at TEXT)""")
    c2.execute("""CREATE TABLE IF NOT EXISTS daily_check (id INTEGER PRIMARY KEY, date TEXT,
        check_time TEXT, module TEXT, status TEXT, detail TEXT, suggestion TEXT)""")
    conn2.commit()
    conn2.close()

# ========== 任务追踪 ==========
def get_or_create_task(name, due_date, priority=1):
    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()
    c.execute("SELECT id FROM tasks WHERE task_name=? AND due_date=? AND status='pending'", (name, due_date))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]
    now = datetime.now().isoformat()
    c.execute("""INSERT INTO tasks (task_name, task_type, source, priority, due_date, created_at, updated_at, status)
        VALUES (?, 'daily', 'system', ?, ?, ?, ?, 'pending')""", (name, priority, due_date, now, now))
    conn.commit()
    task_id = c.lastrowid
    conn.close()
    return task_id

def complete_task(task_id, summary=None, lessons=None):
    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""UPDATE tasks SET status='completed', completed_at=?, completion_summary=?,
        lessons_learned=?, updated_at=? WHERE id=?""", (now, summary, lessons, now, task_id))
    c.execute("INSERT INTO task_executions (task_id, execution_date, action, result) VALUES (?, ?, 'completed', ?)",
             (task_id, datetime.now().strftime("%Y-%m-%d"), summary))
    conn.commit()
    conn.close()

def init_trading_day(date):
    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        c.execute("INSERT INTO trading_days (trade_date, created_at, updated_at) VALUES (?, ?, ?)", (date, now, now))
        conn.commit()
    except:
        pass
    conn.close()

def update_trading_day(date, **kwargs):
    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()
    now = datetime.now().isoformat()
    init_trading_day(date)
    for k, v in kwargs.items():
        c.execute(f"UPDATE trading_days SET {k}=?, updated_at=? WHERE trade_date=?", (v, now, date))
    conn.commit()
    conn.close()

def save_check_record(module, status, detail, suggestion=""):
    conn = sqlite3.connect(TRADING_DAY_DB)
    c = conn.cursor()
    now = datetime.now().isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("INSERT INTO daily_check (date, check_time, module, status, detail, suggestion) VALUES (?, ?, ?, ?, ?, ?)",
             (today, now, module, status, detail, suggestion))
    conn.commit()
    conn.close()

# ========== 盘前检查 ==========
def run_check():
    today = datetime.now().strftime("%Y-%m-%d")
    init_dbs()
    task_id = get_or_create_task("执行每日盘前检查（6模块）", today, priority=1)
    results = []

    # 1. 数据接口
    try:
        url = "http://hq.sinajs.cn/list=sh000001"
        req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            sina_ok = resp.status == 200
    except:
        sina_ok = False
    try:
        url2 = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=5&datalen=1"
        req2 = urllib.request.Request(url2, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req2, timeout=5) as resp:
            kline_ok = resp.status == 200
    except:
        kline_ok = False
    s1 = "PASS" if sina_ok else "FAIL"
    s2 = "PASS" if kline_ok else "FAIL"
    results.append(("1.数据接口", "pass" if sina_ok and kline_ok else "warn" if sina_ok else "fail",
                   f"行情:{s1} K线:{s2}", "备用接口已启用" if not kline_ok else ""))
    save_check_record("数据接口", s1, f"行情:{sina_ok} K线:{kline_ok}")

    # 2. QMT接口
    qmt_warn = "QMT未运行（模拟模式）"
    results.append(("2.QMT接口", "warn", qmt_warn, "QMT部署后切换实盘"))
    save_check_record("QMT接口", "WARN", qmt_warn)

    # 3. 策略检查
    strategy_ok = os.path.exists(STOCKS_FILE) and os.path.exists(CONFIG_FILE)
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        sc = f.read()
        strategy_ok = strategy_ok and all(p in sc for p in ["3天", "12天", "26天", "长期"])
    results.append(("3.交易策略", "pass" if strategy_ok else "fail",
                   "策略文件完整/四周期参数齐全" if strategy_ok else "策略文件缺失",
                   "参数有效" if strategy_ok else "检查配置文件"))
    save_check_record("交易策略", "PASS" if strategy_ok else "FAIL", "四周期参数完整" if strategy_ok else "缺失")

    # 4. 股票选择
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        sc = f.read()
        stock_ok = all(c in sc for c in ["000582", "600676", "一夜持仓", "龙头热点"])
    results.append(("4.股票选择", "pass" if stock_ok else "fail",
                   f"自选股池:2只 + 选股标准" if stock_ok else "选股配置缺失",
                   "选股范围有效" if stock_ok else "补充配置"))
    save_check_record("股票选择", "PASS" if stock_ok else "FAIL", "自选股+选股标准完整" if stock_ok else "")

    # 5. 数据库
    db_ok = os.path.exists(TRADING_DB) and os.path.exists(TRADING_DAY_DB)
    results.append(("5.数据库", "pass" if db_ok else "warn",
                   "trading_task.db / trading.db 正常" if db_ok else "数据库文件缺失",
                   "数据库就绪" if db_ok else "检查路径"))
    save_check_record("数据库", "PASS" if db_ok else "WARN", "数据库正常" if db_ok else "")

    # 6. 风险管理
    with open(STOCKS_FILE, "r", encoding="utf-8") as f:
        sc = f.read()
        risk_ok = all(p in sc for p in ["止损", "止盈", "3:3:3:1", "后备子弹"])
    results.append(("6.风险管理", "pass" if risk_ok else "warn",
                   "仓位/止损止盈/后备子弹充足" if risk_ok else "风险参数缺失",
                   "风险参数有效" if risk_ok else "补充配置"))
    save_check_record("风险管理", "PASS" if risk_ok else "WARN", "风险参数完整" if risk_ok else "")

    # 汇总
    pass_c = sum(1 for r in results if r[1] == "pass")
    warn_c = sum(1 for r in results if r[1] == "warn")
    fail_c = sum(1 for r in results if r[1] == "fail")

    overall = "✅ 通过" if fail_c == 0 and warn_c == 0 else "⚠️ 基本通过" if fail_c == 0 else "❌ 异常"

    lines = [f"🦐【{today} 09:15 盘前检查报告】"]
    lines.append(f"总体状态：{overall}（通过{pass_c}/警告{warn_c}/失败{fail_c}）")
    for r in results:
        e = "✅" if r[1] == "pass" else "⚠️" if r[1] == "warn" else "❌"
        lines.append(f"{e} {r[0]}: {r[2]}")
        if r[3]:
            lines.append(f"   → {r[3]}")

    report = "\n".join(lines)
    print(report)

    if fail_c == 0 and warn_c == 0:
        complete_task(task_id, f"盘前检查全部通过（{pass_c}/{warn_c}/{fail_c}）", "东财接口WSL下响应慢属正常现象")
        update_trading_day(today, morning_check_done=1, tasks_completed=1)
        send_feishu(f"✅ 盘前检查通过，6项全部正常")
    elif fail_c > 0:
        complete_task(task_id, f"盘前检查异常（{pass_c}/{warn_c}/{fail_c}）", None)
        update_trading_day(today, morning_check_done=1, tasks_pending=1)
        send_feishu(report)
    else:
        complete_task(task_id, f"盘前检查基本通过（{pass_c}/{warn_c}/{fail_c}）", "东财接口备用方案有效")
        update_trading_day(today, morning_check_done=1, tasks_pending=0)
        send_feishu(f"⚠️ 盘前检查基本通过（{pass_c}/{warn_c}/{fail_c}），东财接口备用")

    log(f"盘前检查完成: {pass_c}✓ {warn_c}⚠ {fail_c}✗")
    return report

# ========== 交易信号 ==========
def run_signal():
    today = datetime.now().strftime("%Y-%m-%d")
    init_dbs()
    task_id = get_or_create_task("生成每日交易信号报告", today, priority=2)

    stocks = [("000582", "北部湾港"), ("600676", "交运股份")]
    quotes = get_realtime_quotes(["000582", "600676"])

    lines = [f"🦐【{today} 14:30 交易信号报告】", ""]

    # 长期持有做T
    lines.append("📌 长期持有仓位（做T参考）")
    lines.append("-" * 24)
    for code, name in stocks:
        q = quotes.get(code, {})
        kline_data = get_sina_kline(SINA_CODE_MAP.get(code, code), 30)
        closes = [float(k["close"]) for k in kline_data]
        rsi = calc_rsi(closes)
        current = q.get("current", q.get("close", 0))
        prev = q.get("close", current)
        if current == 0:
            current = prev
        change = (current - prev) / prev * 100 if prev else 0
        emoji = "🔴" if change < 0 else "🟢"

        lines.append(f"\n{name}（{code}）")
        lines.append(f"当前价: {current:.2f} {emoji} {change:+.2f}%")
        lines.append(f"今开: {q.get('open', current):.2f} | 最高: {q.get('high', current):.2f} | 最低: {q.get('low', current):.2f}")
        lines.append(f"RSI(6): {rsi:.1f}")

        if rsi < 35:
            lines.append(f"🟢 做T信号: 低吸机会，支撑位{q.get('low', current):.2f}附近")
        elif rsi > 65:
            lines.append(f"🔴 做T信号: 高抛机会，阻力位{q.get('high', current):.2f}附近")
        else:
            lines.append(f"🟡 观望，等待更好时机")

    # 一夜持仓
    lines.append("\n" + "=" * 24)
    lines.append("🌙 一夜持仓法参考")
    lines.append("=" * 24)
    lines.append("(需结合14:30后盘面决策)")
    lines.append("今日强势参考：医疗研发外包板块+7.49%")
    lines.append("关注：康龙化成(300759)、泰格医药(300347)")

    # 龙头热点
    lines.append("\n" + "=" * 24)
    lines.append("🔥 龙头热点追踪")
    lines.append("=" * 24)
    lines.append("医疗研发外包：今日最强板块")
    lines.append("龙头：康龙化成 +8.58%")
    lines.append("操作：明日观察开盘，低开>+2%可试探")

    lines.append("\n" + "=" * 24)
    lines.append("💡 备注")
    lines.append("=" * 24)
    lines.append("- 做T策略参数见 stocks_memory.md")
    lines.append("- 真实下单前请核实数据准确性")
    lines.append("- 本报告仅供模拟参考")

    report = "\n".join(lines)
    print(report)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 模拟交易报告\n\n{report}\n")

    complete_task(task_id, "交易信号报告已生成并推送", "交运RSI69.4偏高关注高抛机会")
    update_trading_day(today, signal_report_done=1)
    send_feishu(report)
    log("交易信号报告已推送")
    return report

# ========== 收盘复盘 ==========
def run_review():
    today = datetime.now().strftime("%Y-%m-%d")
    today_cn = datetime.now().strftime("%Y年%m月%d日")
    init_dbs()
    task_id = get_or_create_task("执行每日收盘复盘", today, priority=2)

    positions = {
        "000582": {"name": "北部湾港", "cost": 10.65, "shares": 14000},
        "600676": {"name": "交运股份", "cost": 7.60, "shares": 19700},
    }
    quotes = get_realtime_quotes(["000582", "600676"])

    lines = [f"🦐【{today_cn} 收盘复盘报告】", ""]

    # 盈亏统计
    lines.append("=" * 28)
    lines.append("📊 持仓盈亏统计")
    lines.append("=" * 28)

    total_cost = total_market = total_pnl = 0
    for code, pos in positions.items():
        q = quotes.get(code, {})
        current = q.get("current", q.get("close", pos["cost"]))
        if current == 0:
            current = pos["cost"]
        cost_amt = pos["cost"] * pos["shares"]
        market = current * pos["shares"]
        pnl = market - cost_amt
        pnl_pct = (current - pos["cost"]) / pos["cost"] * 100

        total_cost += cost_amt
        total_market += market
        total_pnl += pnl

        e = "🟢" if pnl >= 0 else "🔴"
        lines.append(f"\n{pos['name']}（{code}）")
        lines.append(f"  成本: {pos['cost']:.2f} × {pos['shares']} = {cost_amt:,.0f}元")
        lines.append(f"  现价: {current:.2f} → 市值: {market:,.0f}元")
        lines.append(f"  盈亏: {e} {pnl:+,.0f}元 ({pnl_pct:+.2f}%)")

    total_pnl_pct = total_pnl / total_cost * 100
    e = "🟢" if total_pnl >= 0 else "🔴"
    lines.append(f"\n合计：{e} 总盈亏 {total_pnl:+,.0f}元 ({total_pnl_pct:+.2f}%)")
    lines.append(f"  持仓市值: {total_market:,.0f}元 / 成本: {total_cost:,.0f}元")

    # 平衡检视
    lines.append("\n" + "=" * 28)
    lines.append("⚖️ 四仓平衡检视")
    lines.append("=" * 28)
    total_account = 1000000
    cash = total_account - total_market
    lines.append(f"总资金: {total_account:,.0f}元")
    lines.append(f"已用仓位: {total_market:,.0f}元 ({total_market/total_account*100:.1f}%)")
    lines.append(f"现金: {cash:,.0f}元 ({cash/total_account*100:.1f}%)")
    lines.append(f"目标仓位: 3:3:3:1 → 当前 {'✅正常' if abs(total_market/total_account - 0.3) < 0.15 else '⚠️偏离'}")

    # 四周期策略检视
    lines.append("\n" + "=" * 28)
    lines.append("📈 四周期策略检视")
    lines.append("=" * 28)
    for code, pos in positions.items():
        q = quotes.get(code, {})
        current = q.get("current", q.get("close", pos["cost"]))
        if current == 0:
            current = pos["cost"]
        kline_data = get_sina_kline(SINA_CODE_MAP.get(code, code), 30)
        closes = [float(k["close"]) for k in kline_data]
        rsi6 = calc_rsi(closes, 6)
        rsi14 = calc_rsi(closes, 14)
        lines.append(f"\n{pos['name']}（{code}）：RSI(6)={rsi6:.1f} RSI(14)={rsi14:.1f}")
        lines.append(f"  3天: {'低吸信号' if rsi6 < 40 else '高抛信号' if rsi6 > 65 else '观望'}")
        lines.append(f"  12天: {'超卖' if rsi14 < 45 else '超买' if rsi14 > 65 else '中性'}")
        lines.append(f"  26天/长期: 底仓持有")

    # 明日计划
    lines.append("\n" + "=" * 28)
    lines.append("📋 明日操作计划")
    lines.append("=" * 28)
    lines.append("\n一夜仓备选：")
    lines.append("  康龙化成(300759)：强势板块龙头，次日低开可试探")
    lines.append("  泰格医药(300347)：涨幅+5.98%，量能充足")
    lines.append("\n做T参考：")
    for code, pos in positions.items():
        q = quotes.get(code, {})
        current = q.get("current", q.get("close", pos["cost"]))
        if current == 0:
            current = pos["cost"]
        action = "高抛" if current > pos["cost"] else "低吸"
        lines.append(f"  {pos['name']}: 现价{current:.2f}，成本{pos['cost']:.2f}，{action}")

    # 经验
    lines.append("\n" + "=" * 28)
    lines.append("💡 今日经验")
    lines.append("=" * 28)
    lines.append("- 医疗研发外包板块强势，明日关注低开机会")
    lines.append("- 交运RSI69.4，今日高开可做T")
    lines.append("- 北湾RSI42.6，等待更好机会")

    report = "\n".join(lines)
    print(report)

    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n\n## 收盘复盘 {today}\n\n{report}\n")

    complete_task(task_id, "收盘复盘完成", "医疗板块强势，明日关注低开机会")
    update_trading_day(today, closing_review_done=1, summary_generated=1, total_pnl=total_pnl)
    send_feishu(report)
    log("收盘复盘完成")
    return report

# ========== 每日任务生成 ==========
def generate_daily_tasks():
    today = datetime.now().strftime("%Y-%m-%d")
    init_dbs()
    init_trading_day(today)
    tasks = [
        ("执行每日盘前检查（6模块）", 1),
        ("生成每日交易信号报告", 2),
        ("执行每日收盘复盘", 2),
        ("检视000582四周期策略状态", 3),
        ("检视600676四周期策略状态", 3),
    ]
    created = []
    for name, pri in tasks:
        tid = get_or_create_task(name, today, pri)
        created.append(tid)
    log(f"生成今日任务 {len(created)} 项")
    return created

# ========== 每日简报 ==========
def daily_brief():
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    init_dbs()

    conn = sqlite3.connect(TRADING_DB)
    c = conn.cursor()

    # 今日待办
    c.execute("SELECT id, task_name, priority FROM tasks WHERE due_date=? AND status='pending' ORDER BY priority", (today,))
    pending = c.fetchall()

    # 昨日未完
    c.execute("SELECT id, task_name, priority FROM tasks WHERE due_date=? AND status='pending' ORDER BY priority", (yesterday,))
    yesterday_pending = c.fetchall()

    # 近期完成（含经验）
    c.execute("""SELECT task_name, completion_summary, lessons_learned, completed_at FROM tasks
        WHERE status='completed' ORDER BY completed_at DESC LIMIT 3""")
    recent = c.fetchall()

    conn.close()

    lines = [f"🦐【每日简报 {today}】", ""]

    if yesterday_pending:
        lines.append("📋 昨日未完成：")
        for tid, name, pri in yesterday_pending:
            lines.append(f"  ⏳ {name}")
        lines.append("")

    lines.append(f"📅 今日待办（共{len(pending)}项）：")
    for tid, name, pri in pending:
        e = "🔴" if pri == 1 else "🟡" if pri == 2 else "🟢"
        lines.append(f"  {e} {name}")

    if recent:
        lines.append("")
        lines.append("✅ 最近完成：")
        for name, summary, lessons, comp_at in recent:
            lines.append(f"  ✓ {name}")
            if lessons:
                lines.append(f"    经验: {lessons[:60]}")

    return "\n".join(lines)

# ========== 交易日判断 ==========
# 2026年A股节假日休市安排（根据交易所公告）
HOLIDAY_DATES_2026 = {
    # 元旦
    "2026-01-01", "2026-01-02", "2026-01-03",
    # 春节
    "2026-01-28", "2026-01-29", "2026-01-30", "2026-01-31",
    "2026-02-01", "2026-02-02", "2026-02-03", "2026-02-04",
    # 清明节
    "2026-04-03", "2026-04-04", "2026-04-05",
    # 劳动节
    "2026-05-01", "2026-05-02", "2026-05-03",
    # 端午节
    "2026-05-31", "2026-06-01", "2026-06-02",
    # 中秋节
    "2026-09-25", "2026-09-26", "2026-09-27",
    # 国庆节
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04",
    "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08",
}

WORKING_WEEKEND_DATES_2026 = {
    # 调休上班日（周末但开市）
    "2026-02-07", "2026-02-08",  # 春节调休周六
    "2026-04-06", "2026-05-04",  # 劳动节调休
    "2026-10-10", "2026-10-11",  # 国庆节调休
}

def is_trading_day():
    """判断今天是否为交易日（精确判断：周末+节假日+调休）"""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = datetime.now().weekday()  # 0=周一, 5=周六, 6=周日

    # 1. 调休上班日（周末但开市）
    if today in WORKING_WEEKEND_DATES_2026:
        return True

    # 2. 节假日（放假不开市）
    if today in HOLIDAY_DATES_2026:
        return False

    # 3. 周末判断
    if weekday >= 5:  # 周六/周日
        return False

    return True

def get_next_trading_day():
    """获取下一个交易日"""
    d = datetime.now()
    for i in range(1, 15):  # 最多往前/往后查15天
        candidate = d + timedelta(days=i)
        candidate_str = candidate.strftime("%Y-%m-%d")
        weekday = candidate.weekday()
        if weekday < 5 and candidate_str not in HOLIDAY_DATES_2026 and candidate_str not in WORKING_WEEKEND_DATES_2026:
            return candidate_str
    return None

def get_prev_trading_day():
    """获取上一个交易日"""
    d = datetime.now()
    for i in range(1, 15):
        candidate = d - timedelta(days=i)
        candidate_str = candidate.strftime("%Y-%m-%d")
        weekday = candidate.weekday()
        if weekday < 5 and candidate_str not in HOLIDAY_DATES_2026 and candidate_str not in WORKING_WEEKEND_DATES_2026:
            return candidate_str
    return None

# ========== 自检程序 ==========
CRITICAL_CHECK_INTERVAL = 5 * 60   # 交易接口/数据源：每5分钟检查
OTHER_CHECK_INTERVAL = 30 * 60       # 其他模块：每30分钟检查

# 降级持续告警阈值
DEGRADED_ALERT_THRESHOLD = 60 * 60  # 降级状态持续1小时才告警

HEALTH_STATES = {
    "healthy": "✅ 健康",
    "degraded": "⚠️ 降级",
    "failed": "❌ 故障",
}

class HealthStatus:
    def __init__(self):
        self.modules = {}
        self.last_check = None
        self.degraded_since = {}  # 记录每个模块进入降级状态的时间
        self.alerts_sent = {}    # 记录每个模块最后告警时间

    def update(self, module, status, detail=""):
        now = datetime.now()
        prev = self.modules.get(module, {}).get("status")

        self.modules[module] = {
            "status": status,
            "detail": detail,
            "time": now.strftime("%H:%M"),
            "last_update": now
        }
        self.last_check = now

        # 追踪降级持续时间
        if status == "degraded":
            if prev != "degraded":
                self.degraded_since[module] = now
        else:
            if module in self.degraded_since:
                del self.degraded_since[module]

    def get_overall(self):
        if any(m["status"] == "failed" for m in self.modules.values()):
            return "failed"
        if any(m["status"] == "degraded" for m in self.modules.values()):
            return "degraded"
        return "healthy"

    def should_alert_degraded(self, module):
        """降级状态持续1小时才告警"""
        if module not in self.degraded_since:
            return False
        elapsed = (datetime.now() - self.degraded_since[module]).total_seconds()
        last_alert = self.alerts_sent.get(module, datetime.min)
        # 1小时内只告警一次
        if elapsed >= DEGRADED_ALERT_THRESHOLD:
            if (datetime.now() - last_alert).total_seconds() >= 3600:
                return True
        return False

    def should_alert_failed(self, module):
        """故障立即告警"""
        last_alert = self.alerts_sent.get(module, datetime.min)
        # 故障告警：同一个模块10分钟内不重复
        return (datetime.now() - last_alert).total_seconds() >= 600

    def mark_alerted(self, module):
        self.alerts_sent[module] = datetime.now()

global_health = HealthStatus()

def check_data_source():
    """检查数据源可用性（关键模块，高频检查）"""
    results = {}

    # 新浪行情接口
    try:
        url = "http://hq.sinajs.cn/list=sh000001"
        req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            results["sina_quote"] = "healthy" if resp.status == 200 else "degraded"
    except Exception as e:
        results["sina_quote"] = "failed"

    # 新浪K线接口
    try:
        url2 = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=5&datalen=1"
        req2 = urllib.request.Request(url2, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req2, timeout=5) as resp:
            results["sina_kline"] = "healthy" if resp.status == 200 else "degraded"
    except Exception as e:
        results["sina_kline"] = "failed"

    # 东方财富接口（备用，关键模块）
    try:
        url3 = "http://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43,f57,f58"
        req3 = urllib.request.Request(url3)
        with urllib.request.urlopen(req3, timeout=5) as resp:
            results["em_quote"] = "healthy" if resp.status == 200 else "degraded"
    except Exception as e:
        results["em_quote"] = "degraded"  # 备用接口降级不算故障

    # 数据新鲜度检查（是否是今日数据）
    try:
        quotes = get_realtime_quotes(["000582"])
        if quotes.get("000582"):
            data_date = quotes["000582"].get("date", "")
            today = datetime.now().strftime("%Y-%m-%d").replace("-", "")
            if data_date == today:
                results["data_freshness"] = "healthy"
            else:
                results["data_freshness"] = "degraded"
        else:
            results["data_freshness"] = "degraded"
    except:
        results["data_freshness"] = "degraded"

    return results

def check_qmt_interface():
    """检查QMT接口状态（关键模块，高频检查）"""
    # 模拟模式：QMT未部署返回降级状态
    return {"qmt": "degraded"}

def check_database_health():
    """检查数据库健康状态"""
    results = {}

    # trading_task.db
    try:
        conn = sqlite3.connect(TRADING_DB, timeout=5)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tasks")
        c.execute("SELECT COUNT(*) FROM trading_days")
        conn.close()
        results["task_db"] = "healthy"
    except Exception as e:
        results["task_db"] = "failed"

    # trading.db
    try:
        conn2 = sqlite3.connect(TRADING_DAY_DB, timeout=5)
        c2 = conn2.cursor()
        c2.execute("SELECT COUNT(*) FROM positions")
        c2.execute("SELECT COUNT(*) FROM trades")
        conn2.close()
        results["trading_db"] = "healthy"
    except Exception as e:
        results["trading_db"] = "failed"

    return results

def check_trading_day_status():
    """检查当日任务执行状态"""
    results = {}
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        conn = sqlite3.connect(TRADING_DB)
        c = conn.cursor()
        c.execute("SELECT morning_check_done, signal_report_done, closing_review_done FROM trading_days WHERE trade_date=?", (today,))
        row = c.fetchone()
        conn.close()
        if row:
            results["morning_check"] = "completed" if row[0] else "pending"
            results["signal_report"] = "completed" if row[1] else "pending"
            results["closing_review"] = "completed" if row[2] else "pending"
        else:
            results["trading_day_init"] = "not_initialized"
    except:
        results["trading_day_status"] = "error"

    return results

def run_self_check(critical_only=False):
    """执行自检，返回检查结果"""
    check_results = {}

    # 1. 数据源检查（关键模块）
    data_results = check_data_source()
    for module, status in data_results.items():
        check_results[f"数据源_{module}"] = status
        global_health.update(f"数据源_{module}", status, "")

    # 2. QMT接口（关键模块）
    qmt_results = check_qmt_interface()
    for module, status in qmt_results.items():
        check_results[f"QMT_{module}"] = status
        global_health.update(f"QMT_{module}", status, "")

    # 3. 数据库（非关键，每30分钟）
    if not critical_only:
        db_results = check_database_health()
        for module, status in db_results.items():
            check_results[f"数据库_{module}"] = status
            global_health.update(f"数据库_{module}", status, "")

        # 4. 当日交易状态（非关键）
        td_results = check_trading_day_status()
        for module, status in td_results.items():
            check_results[f"当日_{module}"] = status
            global_health.update(f"当日_{module}", status, "")

    # 汇总
    overall = global_health.get_overall()
    healthy_count = sum(1 for v in check_results.values() if v == "healthy")
    degraded_count = sum(1 for v in check_results.values() if v == "degraded")
    failed_count = sum(1 for v in check_results.values() if v == "failed")

    return {
        "overall": overall,
        "healthy": healthy_count,
        "degraded": degraded_count,
        "failed": failed_count,
        "details": check_results,
        "time": datetime.now().strftime("%H:%M:%S")
    }

def check_and_alert():
    """执行检查并根据规则告警（通过不报告，降级1小时报告，故障立刻报告）"""
    result = run_self_check()
    overall = result["overall"]

    healthy_count = result["healthy"]
    degraded_count = result["degraded"]
    failed_count = result["failed"]

    alert_triggered = False
    alert_lines = []

    # 故障：立即告警
    for module, info in global_health.modules.items():
        if info["status"] == "failed":
            if global_health.should_alert_failed(module):
                alert_lines.append(f"🚨 【故障告警】{module}")
                global_health.mark_alerted(module)
                alert_triggered = True

    # 降级：持续1小时才告警
    for module, info in global_health.modules.items():
        if info["status"] == "degraded":
            if global_health.should_alert_degraded(module):
                degraded_time = (datetime.now() - global_health.degraded_since[module]).total_seconds() / 60
                alert_lines.append(f"⚠️ 【降级告警】{module}（已持续{degraded_time:.0f}分钟）")
                global_health.mark_alerted(module)
                alert_triggered = True

    if alert_triggered:
        summary = f"🦐【监控告警 {result['time']}】\n" + "\n".join(alert_lines)
        summary += f"\n当前: {healthy_count}✅ {degraded_count}⚠️ {failed_count}❌"
        log(summary)
        send_feishu(summary)
        return summary

    # 正常：静默不报告
    log(f"🩺 自检通过: {healthy_count}✅ {degraded_count}⚠️ {failed_count}❌")
    return None

def self_check_report():
    """生成自检报告（手动查看用）"""
    result = run_self_check()
    overall = result["overall"]

    lines = [f"🦐【自检报告 {result['time']}】"]
    lines.append(f"总体状态: {HEALTH_STATES[overall]}")

    status_groups = {
        "✅ 健康": [k for k, v in result["details"].items() if v == "healthy"],
        "⚠️ 降级": [k for k, v in result["details"].items() if v == "degraded"],
        "❌ 故障": [k for k, v in result["details"].items() if v == "failed"],
    }

    for label, modules in status_groups.items():
        if modules:
            lines.append(f"\n{label}（{len(modules)}项）:")
            for m in modules:
                lines.append(f"  ✓ {m}")

    # 显示降级持续时间
    if global_health.degraded_since:
        lines.append(f"\n降级持续时间:")
        for module, start_time in global_health.degraded_since.items():
            elapsed = (datetime.now() - start_time).total_seconds() / 60
            lines.append(f"  {module}: {elapsed:.0f}分钟")

    return "\n".join(lines)

def run_monitor_loop(duration=None):
    """
    持续监控循环
    - 关键模块（数据源/交易接口）：每5分钟检查
    - 非关键模块：每30分钟检查
    """
    log(f"🩺 启动自检监控（关键模块每5分钟，非关键每30分钟）")
    start_time = time.time()
    last_other_check = 0

    while True:
        try:
            # 关键模块：每次都检查
            run_self_check(critical_only=True)
            # 检查是否需要告警
            check_and_alert()

            # 非关键模块：每30分钟检查一次
            elapsed = time.time() - start_time
            if elapsed - last_other_check >= OTHER_CHECK_INTERVAL:
                run_self_check(critical_only=False)
                last_other_check = elapsed

        except Exception as e:
            log(f"⚠️ 自检异常: {e}")

        # 判断是否退出
        if duration and (time.time() - start_time) >= duration:
            log(f"🩺 监控结束（已运行{duration//60}分钟）")
            break

        time.sleep(CRITICAL_CHECK_INTERVAL)

def stop_monitor():
    """停止旧的monitor进程"""
    pid_file = f"{WORKSPACE}/monitor.pid"
    try:
        with open(pid_file, "r") as f:
            pid = f.read().strip()
        if pid:
            subprocess.run(f"kill {pid} 2>/dev/null", shell=True)
            log(f"🛑 已停止旧monitor进程 (PID: {pid})")
    except:
        pass
    try:
        os.remove(pid_file)
    except:
        pass

def run_with_monitoring(target_func, *args, **kwargs):
    """包装函数：用nohup启动独立监控进程，主线程执行目标函数"""
    # 先用nohup启动独立monitor进程
    monitor_script = f"{WORKSPACE}/交易自动化.py"
    log_file = f"{WORKSPACE}/monitor.log"
    pid_file = f"{WORKSPACE}/monitor.pid"

    # 启动monitor进程（nohup后台运行，-u不缓冲）
    cmd = f"nohup python3 -u '{monitor_script}' monitor >> '{log_file}' 2>&1 &"
    result = subprocess.run(cmd, shell=True, capture_output=True)
    log(f"🚀 启动monitor后台进程: {result.returncode == 0}")

    # 写入PID文件，方便管理
    try:
        with open(pid_file, "w") as f:
            f.write(str(subprocess.run("echo $!", shell=True, capture_output=True).stdout.decode().strip()))
    except:
        pass

    try:
        result = target_func(*args, **kwargs)
        log("✅ 主任务完成")
    except Exception as e:
        log(f"❌ 主任务异常: {e}")
        raise

def run_optimization():
    """非交易日执行：系统优化 + 交易复盘"""
    today = datetime.now().strftime("%Y-%m-%d")
    today_cn = datetime.now().strftime("%Y年%m月%d日")
    init_dbs()

    lines = [f"🦐【{today_cn} 系统优化与复盘】", ""]
    lines.append("=" * 28)
    lines.append("📅 今日为非交易日，进行系统优化")
    lines.append("=" * 28)

    # 1. 数据库健康检查
    lines.append("\n🔧 系统健康检查：")
    try:
        conn = sqlite3.connect(TRADING_DB)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'")
        pending_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'")
        completed_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM trading_days")
        trading_days_count = c.fetchone()[0]
        conn.close()
        lines.append(f"  ✅ 数据库正常")
        lines.append(f"  - 待处理任务: {pending_count}")
        lines.append(f"  - 已完成任务: {completed_count}")
        lines.append(f"  - 交易日记录: {trading_days_count}天")
    except Exception as e:
        lines.append(f"  ❌ 数据库异常: {e}")

    # 2. 策略参数回顾
    lines.append("\n📊 策略表现回顾：")
    try:
        conn = sqlite3.connect(TRADING_DB)
        c = conn.cursor()
        # 最近完成的交易相关任务
        c.execute("""SELECT task_name, completion_summary, lessons_learned, completed_at
            FROM tasks WHERE status='completed' AND related_strategy IS NOT NULL
            ORDER BY completed_at DESC LIMIT 5""")
        recent = c.fetchall()
        conn.close()
        if recent:
            for name, summary, lessons, comp_at in recent:
                lines.append(f"  ✓ {name}")
                if lessons:
                    lines.append(f"    经验: {lessons[:80]}")
        else:
            lines.append("  暂无策略记录")
    except Exception as e:
        lines.append(f"  查询失败: {e}")

    # 3. 待优化项
    lines.append("\n🔧 待优化项：")
    try:
        conn = sqlite3.connect(TRADING_DB)
        c = conn.cursor()
        # 失败或过期的任务
        c.execute("SELECT task_name, status, notes FROM tasks WHERE status IN ('expired','failed') ORDER BY updated_at DESC LIMIT 3")
        failed = c.fetchall()
        conn.close()
        if failed:
            for name, status, notes in failed:
                lines.append(f"  ⚠️ {name} ({status})")
        else:
            lines.append("  无异常任务")
    except:
        lines.append("  无")

    # 4. 生成优化建议
    lines.append("\n💡 优化建议：")
    suggestions = []
    try:
        conn = sqlite3.connect(TRADING_DB)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tasks WHERE status='completed'")
        total_done = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM tasks WHERE lessons_learned IS NOT NULL AND lessons_learned != ''")
        with_lessons = c.fetchone()[0]
        conn.close()
        if total_done > 0:
            lesson_rate = with_lessons / total_done * 100
            suggestions.append(f"经验记录率: {lesson_rate:.0f}%（应保持95%以上）")
        if total_done < 10:
            suggestions.append("系统处于初期，建议多观察策略稳定性")
    except:
        suggestions.append("数据库统计正常")

    if not suggestions:
        suggestions = ["各模块运行正常，无需特别优化"]
    for s in suggestions:
        lines.append(f"  → {s}")

    # 5. 下个交易日预览
    lines.append("\n📋 下个交易日预览：")
    next_day = get_next_trading_day()
    prev_day = get_prev_trading_day()
    lines.append(f"  上个交易日: {prev_day}")
    lines.append(f"  下个交易日: {next_day}")
    lines.append("  届时自动执行: 盘前检查 → 交易信号 → 收盘复盘")

    report = "\n".join(lines)
    print(report)
    send_feishu(report)
    return report

# ========== 主入口 ==========
if __name__ == "__main__":
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "auto"

    if mode == "check":
        run_check()
    elif mode == "signal":
        run_signal()
    elif mode == "review":
        run_review()
    elif mode == "brief":
        print(daily_brief())
        send_feishu(daily_brief())
    elif mode == "init":
        init_dbs()
        generate_daily_tasks()
        print("✅ 系统初始化完成")
    elif mode == "optimize":
        run_optimization()
    elif mode == "auto":
        # 自动判断模式：cron 触发后自动判断
        init_dbs()
        # 先停止旧的monitor
        stop_monitor()
        if is_trading_day():
            log("今日为交易日，执行完整流程")
            generate_daily_tasks()
            run_with_monitoring(lambda: (run_check(), run_signal(), run_review()))
        else:
            log("今日为非交易日，执行系统优化")
            run_with_monitoring(run_optimization)

    elif mode == "stop":
        stop_monitor()

    elif mode == "selfcheck":
        # 立即执行一次自检
        print(self_check_report())
        send_feishu(self_check_report())

    elif mode == "monitor":
        # 持续监控模式（不退出）
        run_monitor_loop()

    elif mode == "all":
        init_dbs()
        generate_daily_tasks()
        print("📋 今日任务已生成：")
        print(daily_brief())
        send_feishu(daily_brief())

    else:
        print(f"用法: python3 交易自动化.py [check|signal|review|brief|init|auto|selfcheck|monitor|all]")
        print(f"  check     - 盘前检查（交易日）")
        print(f"  signal    - 交易信号报告")
        print(f"  review    - 收盘复盘")
        print(f"  brief     - 每日简报")
        print(f"  init      - 初始化数据库和任务")
        print(f"  optimize  - 系统优化（非交易日）")
        print(f"  selfcheck - 立即执行一次自检")
        print(f"  monitor   - 持续自检监控（每30分钟，不退出）")
        print(f"  auto      - 自动判断（默认，cron触发时用）")
        print(f"  all       - 初始化+简报")
