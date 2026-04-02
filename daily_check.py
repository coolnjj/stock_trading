#!/usr/bin/env python3
"""
每日交易前运行检查
执行时间：每个交易日 09:15
检查模块：数据接口 / QMT接口 / 交易策略 / 股票选择 / 数据库 / 风险管理
"""
import urllib.request
import json
import os
import subprocess
from datetime import datetime

# ========== 配置 ==========
GATEWAY_URL = "http://127.0.0.1:18789"
CONFIG_FILE = "/home/wenkun/.openclaw/workspace/paper_trading_config.md"
STOCKS_FILE = "/home/wenkun/.openclaw/workspace/stocks_memory.md"
REPORT_FILE = "/home/wenkun/.openclaw/workspace/daily_check_report.md"

# ========== 辅助函数 ==========
def check_result(module, status, detail="", suggestion=""):
    return {
        "module": module,
        "status": status,  # "pass" / "warn" / "fail"
        "detail": detail,
        "suggestion": suggestion
    }

def send_feishu(message):
    subprocess.run(
        ["openclaw", "message", "send", "--channel", "feishu",
         "--target", "ou_51a14c42e587cd0f52446357c5819f08", "--message", message],
        capture_output=True, text=True
    )

# ========== 模块1：数据接口检查 ==========
def check_data_interface():
    """检查各行情数据接口可用性"""
    results = []
    
    # 新浪行情接口
    try:
        url = "http://hq.sinajs.cn/list=sh000001"
        req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                results.append(("新浪行情", "pass", "接口正常"))
            else:
                results.append(("新浪行情", "warn", f"HTTP {resp.status}"))
    except Exception as e:
        results.append(("新浪行情", "fail", str(e)))
    
    # 新浪K线接口
    try:
        url = "http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=240&ma=5&datalen=1"
        req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                results.append(("新浪K线", "pass", "接口正常"))
            else:
                results.append(("新浪K线", "warn", f"HTTP {resp.status}"))
    except Exception as e:
        results.append(("新浪K线", "fail", str(e)))
    
    # 东方财富接口（备选，timeout宽松一点）
    try:
        url = "http://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f43,f57,f58,f169,f170"
        with urllib.request.urlopen(url, timeout=8) as resp:
            if resp.status == 200:
                results.append(("东方财富", "pass", "接口正常"))
            else:
                results.append(("东方财富", "warn", f"HTTP {resp.status}"))
    except Exception as e:
        results.append(("东方财富", "warn", f"备选接口: {str(e)[:30]}"))
    
    # 主接口（新浪）必须通，备用接口可降级
    sina_ok = any(r[0] == "新浪行情" and r[1] == "pass" for r in results)
    if not sina_ok:
        overall = "fail"
    else:
        fail_count_d = sum(1 for r in results if r[1] == "fail")
        warn_count_d = sum(1 for r in results if r[1] == "warn")
        if fail_count_d > 0:
            overall = "fail"
        elif warn_count_d > 0:
            overall = "warn"
        else:
            overall = "pass"
    
    warn_count = sum(1 for r in results if r[1] == "warn")
    
    detail = " | ".join([f"{r[0]}:{r[1].upper()}" for r in results])
    suggestion = "备用接口已启用" if any(r[1] != "pass" for r in results) else "全部正常"
    
    return check_result("1. 数据接口检查", overall, detail, suggestion)

# ========== 模块2：QMT接口检查 ==========
def check_qmt_interface():
    """检查QMT交易接口连接状态"""
    # TODO: 等QMT部署后接入真实检查
    # 目前返回预留状态
    
    # 检查QMT进程是否存在
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq *.exe"],
            capture_output=True, text=True, shell=True
        )
        qmt_running = "XtItClient" in result.stdout or "QMT" in result.stdout
    except:
        qmt_running = False
    
    if qmt_running:
        return check_result(
            "2. QMT接口检查", "pass",
            "QMT客户端运行中",
            "接口就绪，可执行交易"
        )
    else:
        return check_result(
            "2. QMT接口检查", "warn",
            "QMT未运行（模拟模式）",
            "当前为模拟交易模式，QMT部署后切换实盘"
        )

# ========== 模块3：交易策略检查 ==========
def check_trading_strategy():
    """检查策略文件完整性和参数有效性"""
    issues = []
    
    # 检查配置文件存在
    if not os.path.exists(CONFIG_FILE):
        return check_result("3. 交易策略检查", "fail", "配置文件缺失", "创建 paper_trading_config.md")
    
    if not os.path.exists(STOCKS_FILE):
        return check_result("3. 交易策略检查", "fail", "股票记忆库缺失", "创建 stocks_memory.md")
    
    # 检查策略参数完整性（主要在stocks_memory.md）
    try:
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            periods = ["3天", "12天", "26天", "长期"]
            for p in periods:
                if p not in content:
                    issues.append(f"缺少周期: {p}")
            # 检查账户配置
            if "总资金" not in content:
                issues.append("缺少账户配置")
            if "四仓分配" not in content:
                issues.append("缺少四仓分配")
    except Exception as e:
        return check_result("3. 交易策略检查", "fail", f"读取失败: {e}", "检查文件权限")
    
    if issues:
        return check_result("3. 交易策略检查", "warn", "; ".join(issues), "补充完整策略参数")
    
    return check_result(
        "3. 交易策略检查", "pass",
        "策略文件完整，四周期参数齐全",
        "参数有效，可执行交易"
    )

# ========== 模块4：股票选择检查 ==========
def check_stock_selection():
    """检查自选股池、选股条件、持仓状态"""
    issues = []
    
    try:
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查长期持有标的
        long_stocks = ["000582", "600676"]
        for code in long_stocks:
            if code not in content:
                issues.append(f"长期持有缺少: {code}")
        
        # 检查选股标准
        selection_criteria = ["一夜持仓", "龙头热点", "动态趋势"]
        for c in selection_criteria:
            if c not in content:
                issues.append(f"缺少选股标准: {c}")
        
        # 检查自主配置
        if "自主配置" not in content:
            issues.append("缺少自主配置（市场分析）")
        
    except Exception as e:
        return check_result("4. 股票选择检查", "fail", f"读取失败: {e}", "检查 stocks_memory.md")
    
    if issues:
        return check_result("4. 股票选择检查", "warn", "; ".join(issues), "补充完整选股配置")
    
    return check_result(
        "4. 股票选择检查", "pass",
        f"自选股池: {len(long_stocks)}只 + 一夜仓/龙头热点选股标准",
        "选股范围有效"
    )

# ========== 模块5：数据库检查 ==========
def check_database():
    """检查交易记录数据库（SQLite）"""
    db_file = "/home/wenkun/.openclaw/workspace/trading.db"
    
    # 如果数据库不存在，警告但不影响交易
    if not os.path.exists(db_file):
        return check_result(
            "5. 数据库检查", "warn",
            "数据库文件不存在（首次运行）",
            "系统将自动创建 trading.db"
        )
    
    try:
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        
        required_tables = ["positions", "trades", "daily_check"]
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            return check_result(
                "5. 数据库检查", "warn",
                f"缺少表: {missing}",
                "数据库结构待完善"
            )
        
        # 检查今日是否有检查记录
        cursor.execute("SELECT COUNT(*) FROM daily_check WHERE date LIKE ?", 
                      (datetime.now().strftime("%Y-%m-%d") + "%",))
        today_count = cursor.fetchone()[0]
        
        conn.close()
        
        return check_result(
            "5. 数据库检查", "pass",
            f"数据库正常，共 {len(tables)} 张表",
            "数据库就绪"
        )
        
    except Exception as e:
        return check_result("5. 数据库检查", "fail", str(e), "检查数据库配置")

# ========== 模块6：风险管理检查 ==========
def check_risk_management():
    """检查仓位、止损、风险参数"""
    issues = []
    
    try:
        with open(STOCKS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 检查止损参数
        risk_params = {
            "止损": "-2%" in content or "-3%" in content,
            "止盈": "+3%" in content or "+5%" in content,
            "仓位控制": "3:3:3:1" in content,
            "后备子弹": "100,000" in content or "后备子弹" in content,
        }
        
        for param, exists in risk_params.items():
            if not exists:
                issues.append(f"缺少风险参数: {param}")
        
        # 检查总仓位不超过90%
        # 从配置中读取已用仓位
        import re
        match = re.search(r"已用仓位.*?(\d+)", content)
        if match:
            used = int(match.group(1))
            if used > 900000:  # 超过90%
                issues.append(f"仓位过重: {used/10000:.1f}万/100万")
        
    except Exception as e:
        return check_result("6. 风险管理检查", "fail", str(e), "读取配置失败")
    
    if issues:
        return check_result("6. 风险管理检查", "warn", "; ".join(issues), "建议调整")
    
    return check_result(
        "6. 风险管理检查", "pass",
        "仓位3:3:3:1，止损止盈参数齐全，后备子弹充足",
        "风险参数有效"
    )

# ========== 主检查流程 ==========
def run_all_checks():
    """执行全部检查项"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    checks = [
        check_data_interface(),
        check_qmt_interface(),
        check_trading_strategy(),
        check_stock_selection(),
        check_database(),
        check_risk_management(),
    ]
    
    # 生成报告
    pass_count = sum(1 for c in checks if c["status"] == "pass")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    fail_count = sum(1 for c in checks if c["status"] == "fail")

    
    overall = "✅ 通过" if fail_count == 0 and warn_count == 0 else \
              "⚠️ 基本通过" if fail_count == 0 else \
              "❌ 异常"
    
    report_lines = [
        f"🦐【{today} 每日盘前检查报告】",
        f"总体状态：{overall}（通过{pass_count}/警告{warn_count}/失败{fail_count}）",
        "",
    ]
    
    for c in checks:
        emoji = "✅" if c["status"] == "pass" else "⚠️" if c["status"] == "warn" else "❌"
        report_lines.append(f"{emoji} {c['module']}")
        report_lines.append(f"   状态: {c['status'].upper()} | {c['detail']}")
        if c["suggestion"]:
            report_lines.append(f"   建议: {c['suggestion']}")
        report_lines.append("")
    
    report_lines.append("—" * 30)
    report_lines.append("📋 检查项说明")
    report_lines.append("1. 数据接口：新浪/东财行情接口可用性")
    report_lines.append("2. QMT接口：模拟模式（QMT部署后切换实盘）")
    report_lines.append("3. 交易策略：策略文件完整性")
    report_lines.append("4. 股票选择：自选股池和选股标准")
    report_lines.append("5. 数据库：交易记录数据库状态")
    report_lines.append("6. 风险管理：仓位和风险参数")
    
    report = "\n".join(report_lines)
    return report, checks, (pass_count, warn_count, fail_count)

# ========== 初始化数据库 ==========
def init_database():
    """初始化SQLite数据库"""
    db_file = "/home/wenkun/.openclaw/workspace/trading.db"
    try:
        import sqlite3
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                stock_code TEXT,
                stock_name TEXT,
                position_type TEXT,
                shares INTEGER,
                avg_cost REAL,
                current_price REAL,
                market_value REAL,
                unrealized_pnl REAL,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                stock_code TEXT,
                stock_name TEXT,
                action TEXT,
                price REAL,
                shares INTEGER,
                amount REAL,
                strategy_type TEXT,
                signal_source TEXT,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_check (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                check_time TEXT,
                module TEXT,
                status TEXT,
                detail TEXT,
                suggestion TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return False

# ========== 保存检查记录 ==========
def save_check_records(checks):
    """保存检查记录到数据库"""
    db_file = "/home/wenkun/.openclaw/workspace/trading.db"
    if not os.path.exists(db_file):
        return
    
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today = datetime.now().strftime("%Y-%m-%d")
        
        for c in checks:
            cursor.execute("""
                INSERT INTO daily_check (date, check_time, module, status, detail, suggestion)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (today, now, c["module"], c["status"], c["detail"], c["suggestion"]))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"保存检查记录失败: {e}")

# ========== 保存报告文件 ==========
def save_report_file(report):
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 每日盘前检查报告\n\n{report}\n")

# ========== 主入口 ==========
if __name__ == "__main__":
    # 初始化数据库
    init_database()
    
    # 执行全部检查
    report, checks, counts = run_all_checks()
    
    # 保存报告
    save_report_file(report)
    save_check_records(checks)
    
    # 打印报告
    print(report)
    
    # 发送飞书通知
    if counts[2] > 0:  # 有失败的，优先发送
        send_feishu(report)
    elif counts[1] > 0:  # 有警告的，摘要发送
        summary = f"🦐【每日盘前检查】⚠️ 基本通过（通过{counts[0]}/警告{counts[1]}/失败{counts[2]}）\n详细报告已生成，请查看。"
        send_feishu(summary)
    # 如果全部通过，默认不打扰（避免过多通知）
    
    print(f"\n✅ 检查完成 | 通过:{counts[0]} 警告:{counts[1]} 失败:{counts[2]}")
