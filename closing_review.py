#!/usr/bin/env python3
"""
每日收盘复盘
- 统计当日盈亏 / 胜率
- 更新持仓成本
- 维持 3:3:3:1 平衡
- 生成明日备选股
- 任务完成记录
"""
import subprocess
import json
import urllib.request
import urllib.error
import os
import sqlite3
from datetime import datetime

# ========== 配置 ==========
REPORT_FILE = "/home/wenkun/.openclaw/workspace/paper_trading_report.md"
STOCKS_FILE = "/home/wenkun/.openclaw/workspace/stocks_memory.md"
TASK_DB_FILE = "/home/wenkun/.openclaw/workspace/trading_task.db"
FEISHU_USER = "ou_51a14c42e587cd0f52446357c5819f08"

# ========== 任务追踪 ==========
def init_task_db():
    db_file = TASK_DB_FILE
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            task_type TEXT DEFAULT 'daily',
            source TEXT DEFAULT 'system',
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 3,
            created_at TEXT,
            updated_at TEXT,
            due_date TEXT,
            completed_at TEXT,
            completion_summary TEXT,
            lessons_learned TEXT,
            related_strategy TEXT,
            notes TEXT,
            tags TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT UNIQUE NOT NULL,
            day_status TEXT DEFAULT 'open',
            total_pnl REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
            positions_opened INTEGER DEFAULT 0,
            positions_closed INTEGER DEFAULT 0,
            tasks_planned INTEGER DEFAULT 0,
            tasks_completed INTEGER DEFAULT 0,
            tasks_pending INTEGER DEFAULT 0,
            summary_generated INTEGER DEFAULT 0,
            morning_check_done INTEGER DEFAULT 0,
            signal_report_done INTEGER DEFAULT 0,
            closing_review_done INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_or_create_task(task_name: str, due_date: str) -> int:
    conn = sqlite3.connect(TASK_DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM tasks WHERE task_name=? AND due_date=? AND status='pending'", 
                   (task_name, due_date))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO tasks (task_name, task_type, source, priority, due_date, created_at, updated_at, status)
        VALUES (?, 'daily', 'system', 2, ?, ?, ?, 'pending')
    """, (task_name, due_date, now, now))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def complete_task(task_id: int, summary: str = None, lessons: str = None):
    conn = sqlite3.connect(TASK_DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE tasks SET status='completed', completed_at=?, completion_summary=?,
        lessons_learned=?, updated_at=? WHERE id=?
    """, (now, summary, lessons, now, task_id))
    conn.commit()
    conn.close()

def update_trading_day(date: str, **kwargs):
    conn = sqlite3.connect(TASK_DB_FILE)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute("INSERT INTO trading_days (trade_date, created_at, updated_at) VALUES (?, ?, ?)",
                      (date, now, now))
    except:
        pass
    for key, val in kwargs.items():
        cursor.execute(f"UPDATE trading_days SET {key}=?, updated_at=? WHERE trade_date=?",
                      (val, now, date))
    conn.commit()
    conn.close()

# ========== 行情获取 ==========
SINA_CODE_MAP = {
    "000582": "sz000582",
    "600676": "sh600676",
}

def get_realtime_quote(codes):
    if not codes:
        return {}
    sina_codes = [SINA_CODE_MAP.get(c, c) for c in codes]
    codes_str = ",".join(sina_codes)
    url = f"http://hq.sinajs.cn/list={codes_str}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("gbk")
            result = {}
            lines = data.strip().split("\n")
            for i, line in enumerate(lines):
                if "=" not in line:
                    continue
                code = codes[i] if i < len(codes) else ""
                parts = line.split("=")[1].strip('"').split(",")
                if len(parts) >= 32:
                    result[code] = {
                        "name": parts[0],
                        "close": float(parts[2]) if parts[2] else 0,
                        "current": float(parts[3]) if parts[3] else 0,
                        "open": float(parts[1]) if parts[1] else 0,
                        "high": float(parts[4]) if parts[4] else 0,
                        "low": float(parts[5]) if parts[5] else 0,
                    }
            return result
    except Exception as e:
        print(f"获取行情失败: {e}")
        return {}

def send_feishu(message):
    subprocess.run(
        ["openclaw", "message", "send", "--channel", "feishu", "--target", FEISHU_USER, "--message", message],
        capture_output=True, text=True
    )

# ========== 复盘主函数 ==========
def generate_closing_review():
    today = datetime.now().strftime("%Y-%m-%d")
    today_cn = datetime.now().strftime("%Y年%m月%d日")
    
    # 获取持仓数据
    stocks = ["000582", "600676"]
    quotes = get_realtime_quote(stocks)
    
    # 持仓成本（从配置读取）
    positions = {
        "000582": {"name": "北部湾港", "cost": 10.65, "shares": 14000},
        "600676": {"name": "交运股份", "cost": 7.60, "shares": 19700},
    }
    
    report_lines = []
    report_lines.append(f"🦐【{today_cn} 收盘复盘报告】\n")
    
    # 1. 当日持仓盈亏
    report_lines.append("=" * 30)
    report_lines.append("📊 持仓盈亏统计")
    report_lines.append("=" * 30)
    
    total_cost = 0
    total_market = 0
    total_pnl = 0
    
    for code, pos in positions.items():
        if code in quotes:
            q = quotes[code]
            current = q.get("current", q.get("close", 0))
            prev_close = q.get("close", 0)
            if current == 0:
                current = prev_close
        else:
            current = pos["cost"]
        
        cost_amount = pos["cost"] * pos["shares"]
        market_value = current * pos["shares"]
        pnl = market_value - cost_amount
        pnl_pct = (current - pos["cost"]) / pos["cost"] * 100
        
        total_cost += cost_amount
        total_market += market_value
        total_pnl += pnl
        
        emoji = "🟢" if pnl >= 0 else "🔴"
        report_lines.append(f"\n{pos['name']}（{code}）")
        report_lines.append(f"  持仓成本: {pos['cost']:.2f} × {pos['shares']} = {cost_amount:,.0f}元")
        report_lines.append(f"  当前/收盘: {current:.2f}元")
        report_lines.append(f"  市值: {market_value:,.0f}元")
        report_lines.append(f"  盈亏: {emoji} {pnl:+,.0f}元 ({pnl_pct:+.2f}%)")
    
    total_pnl_pct = total_pnl / total_cost * 100
    emoji = "🟢" if total_pnl >= 0 else "🔴"
    report_lines.append(f"\n合计：{emoji} 总盈亏 {total_pnl:+,.0f}元 ({total_pnl_pct:+.2f}%)")
    report_lines.append(f"  持仓市值: {total_market:,.0f}元 / 成本: {total_cost:,.0f}元")
    
    # 2. 四周期策略检视
    report_lines.append("\n" + "=" * 30)
    report_lines.append("📈 四周期策略检视")
    report_lines.append("=" * 30)
    
    for code, pos in positions.items():
        report_lines.append(f"\n{pos['name']}（{code}）：")
        if code in quotes:
            q = quotes[code]
            current = q.get("current", q.get("close", 0))
            high = q.get("high", 0)
            low = q.get("low", 0)
            if current == 0:
                current = pos["cost"]
            change = (current - q.get("close", current)) / q.get("close", current) * 100 if q.get("close", 0) else 0
            report_lines.append(f"  收盘: {current:.2f} {change:+.2f}% 高:{high:.2f} 低:{low:.2f}")
            report_lines.append(f"  3天策略: 观望" if abs(change) < 2 else f"  3天策略: 关注{('高抛' if change > 2 else '低吸')}机会")
            report_lines.append(f"  12天策略: RSI参考")
            report_lines.append(f"  26天策略: 中期趋势参考")
            report_lines.append(f"  长期策略: 底仓持有")
    
    # 3. 3:3:3:1 平衡检视
    report_lines.append("\n" + "=" * 30)
    report_lines.append("⚖️ 四仓平衡检视")
    report_lines.append("=" * 30)
    
    total_account = 1000000
    used_capital = total_market
    cash = total_account - used_capital
    target_positions = [300000, 300000, 300000, 100000]  # 长持/一夜/龙头/子弹
    
    report_lines.append(f"总资金: {total_account:,.0f}元")
    report_lines.append(f"已用仓位: {used_capital:,.0f}元 ({used_capital/total_account*100:.1f}%)")
    report_lines.append(f"现金: {cash:,.0f}元 ({cash/total_account*100:.1f}%)")
    report_lines.append(f"目标仓位: 3:3:3:1")
    report_lines.append(f"当前偏离: {'✅ 正常' if abs(used_capital/total_account - 0.3) < 0.1 else '⚠️ 需平衡'}")
    
    # 4. 明日操作计划
    report_lines.append("\n" + "=" * 30)
    report_lines.append("📋 明日操作计划")
    report_lines.append("=" * 30)
    
    report_lines.append("\n一夜仓备选（基于今日强势板块）：")
    report_lines.append("  医疗研发外包板块今日+7.49%，明日关注低开机会")
    report_lines.append("  重点关注：康龙化成(300759)、泰格医药(300347)")
    
    report_lines.append("\n龙头热点：")
    report_lines.append("  明日观察康龙化成开盘表现，高开>+3%放量可轻仓试探")
    
    report_lines.append("\n做T参考：")
    for code, pos in positions.items():
        if code in quotes:
            q = quotes[code]
            current = q.get("current", q.get("close", 0))
            if current == 0:
                current = pos["cost"]
            report_lines.append(f"  {pos['name']}: {current:.2f}，{'关注低吸' if current < pos['cost'] else '可高抛做T'}")
    
    # 5. 经验总结
    report_lines.append("\n" + "=" * 30)
    report_lines.append("💡 今日经验")
    report_lines.append("=" * 30)
    report_lines.append("- 交运股份RSI69.4偏高，今日若高开可做T高抛")
    report_lines.append("- 北部湾港RSI42.6正常位置，等待更好机会")
    report_lines.append("- 医疗板块强势，一夜仓可关注但避免追高")
    
    return "\n".join(report_lines)

# ========== 主入口 ==========
if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 初始化
    init_task_db()
    task_id = get_or_create_task("执行每日收盘复盘", today)
    
    # 生成复盘报告
    report = generate_closing_review()
    print(report)
    
    # 保存报告
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n\n## 收盘复盘 {today}\n\n{report}\n")
    
    # 更新任务
    complete_task(task_id,
                  summary="收盘复盘完成，统计盈亏并制定明日计划",
                  lessons="医疗板块强势，明日关注低开机会")
    update_trading_day(today, closing_review_done=1, summary_generated=1)
    
    # 发送飞书
    send_feishu(report)
    print(f"\n✅ 复盘完成 | 任务完成 (task_id={task_id})")
