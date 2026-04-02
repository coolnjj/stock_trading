#!/usr/bin/env python3
"""
任务追踪系统 - trading_task.db
功能：每日任务管理 / 未完成任务追踪 / 已完成任务经验总结
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict

DB_FILE = "/home/wenkun/.openclaw/workspace/trading_task.db"

# ========== 数据库初始化 ==========
def init_task_db():
    """初始化任务追踪数据库"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 任务表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            task_type TEXT DEFAULT 'daily',  -- daily/one_time/recurring
            source TEXT DEFAULT 'system',    -- 虾主/system/strategy
            status TEXT DEFAULT 'pending',   -- pending/in_progress/completed/expired/cancelled
            priority INTEGER DEFAULT 3,      -- 1=最高 5=最低
            created_at TEXT,
            updated_at TEXT,
            due_date TEXT,
            completed_at TEXT,
            completion_summary TEXT,
            lessons_learned TEXT,
            related_strategy TEXT,
            notes TEXT,
            tags TEXT                        -- JSON数组
        )
    """)
    
    # 每日交易日追踪表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT UNIQUE NOT NULL,
            day_status TEXT DEFAULT 'open',  -- open/closed
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
    
    # 任务执行日志
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            execution_date TEXT,
            action TEXT,           -- started/completed/failed/extended
            result TEXT,
            notes TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)
    
    # 策略运行记录（追踪四周期策略状态）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strategy_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT,
            strategy_type TEXT,     -- 3day/12day/26day/longterm
            run_date TEXT,
            status TEXT,           -- running/completed/signal_triggered
            signal_type TEXT,       -- buy/sell/hold
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            notes TEXT,
            created_at TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"✅ 任务追踪数据库初始化完成: {DB_FILE}")

# ========== 任务管理 ==========
class TaskManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def __del__(self):
        self.conn.close()
    
    def create_task(self, name: str, task_type: str = "daily",
                   source: str = "system", priority: int = 3,
                   due_date: str = None, related_strategy: str = None,
                   notes: str = None, tags: List[str] = None) -> int:
        """创建新任务"""
        now = datetime.now().isoformat()
        self.cursor.execute("""
            INSERT INTO tasks (task_name, task_type, source, priority, 
                             due_date, related_strategy, notes, tags,
                             created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (name, task_type, source, priority, due_date,
              related_strategy, notes, json.dumps(tags or []), now, now))
        self.conn.commit()
        return self.cursor.lastrowid
    
    def complete_task(self, task_id: int, summary: str = None,
                     lessons: str = None) -> bool:
        """完成任务并记录总结"""
        now = datetime.now().isoformat()
        self.cursor.execute("""
            UPDATE tasks SET 
                status = 'completed',
                completed_at = ?,
                completion_summary = ?,
                lessons_learned = ?,
                updated_at = ?
            WHERE id = ?
        """, (now, summary, lessons, now, task_id))
        self.conn.commit()
        
        # 记录执行日志
        self.log_execution(task_id, "completed", result=summary)
        return self.cursor.rowcount > 0
    
    def expire_task(self, task_id: int, notes: str = None) -> bool:
        """任务过期（交易日结束未完成）"""
        now = datetime.now().isoformat()
        self.cursor.execute("""
            UPDATE tasks SET status = 'expired', notes = ?, updated_at = ?
            WHERE id = ?
        """, (notes, now, task_id))
        self.conn.commit()
        self.log_execution(task_id, "expired", result=notes)
        return self.cursor.rowcount > 0
    
    def get_pending_tasks(self, date: str = None) -> List[Dict]:
        """获取待处理任务（可指定日期）"""
        if date:
            self.cursor.execute("""
                SELECT * FROM tasks 
                WHERE status IN ('pending', 'in_progress')
                AND (due_date IS NULL OR due_date <= ?)
                ORDER BY priority ASC, created_at ASC
            """, (date,))
        else:
            self.cursor.execute("""
                SELECT * FROM tasks 
                WHERE status IN ('pending', 'in_progress')
                ORDER BY priority ASC, created_at ASC
            """)
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_yesterday_pending(self, yesterday: str) -> List[Dict]:
        """获取昨日未完成任务"""
        self.cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'pending'
            AND due_date = ?
            ORDER BY priority ASC
        """, (yesterday,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def get_completed_tasks(self, days: int = 7) -> List[Dict]:
        """获取最近完成的任务（含经验总结）"""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        self.cursor.execute("""
            SELECT * FROM tasks 
            WHERE status = 'completed'
            AND completed_at >= ?
            ORDER BY completed_at DESC
        """, (since,))
        return [dict(row) for row in self.cursor.fetchall()]
    
    def log_execution(self, task_id: int, action: str, result: str = None, notes: str = None):
        """记录任务执行日志"""
        now = datetime.now().date().isoformat()
        self.cursor.execute("""
            INSERT INTO task_executions (task_id, execution_date, action, result, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, now, action, result, notes))
        self.conn.commit()
    
    def init_trading_day(self, date: str) -> int:
        """初始化交易日记录"""
        now = datetime.now().isoformat()
        try:
            self.cursor.execute("""
                INSERT INTO trading_days (trade_date, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (date, now, now))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return self.get_trading_day(date)["id"]
    
    def get_trading_day(self, date: str) -> Optional[Dict]:
        """获取特定交易日记录"""
        self.cursor.execute("SELECT * FROM trading_days WHERE trade_date = ?", (date,))
        row = self.cursor.fetchone()
        return dict(row) if row else None
    
    def update_trading_day(self, date: str, **kwargs) -> bool:
        """更新交易日状态"""
        now = datetime.now().isoformat()
        fields = ["day_status", "total_pnl", "win_rate", "positions_opened",
                  "positions_closed", "tasks_planned", "tasks_completed",
                  "tasks_pending", "summary_generated", "morning_check_done",
                  "signal_report_done", "closing_review_done"]
        updates = []
        values = []
        for f in fields:
            if f in kwargs:
                updates.append(f"{f} = ?")
                values.append(kwargs[f])
        if not updates:
            return False
        updates.append("updated_at = ?")
        values.append(now)
        values.append(date)
        self.cursor.execute(f"""
            UPDATE trading_days SET {', '.join(updates)} WHERE trade_date = ?
        """, values)
        self.conn.commit()
        return self.cursor.rowcount > 0

# ========== 每日任务生成 ==========
def generate_daily_tasks(tm: TaskManager, date: str) -> List[int]:
    """生成每日常规任务"""
    task_ids = []
    
    # 1. 盘前检查任务
    task_ids.append(tm.create_task(
        name="执行每日盘前检查（6模块）",
        task_type="daily",
        source="system",
        priority=1,
        due_date=date,
        related_strategy="system_check",
        tags=["daily", "morning", "routine"]
    ))
    
    # 2. 交易信号生成
    task_ids.append(tm.create_task(
        name="生成每日交易信号报告",
        task_type="daily",
        source="system",
        priority=2,
        due_date=date,
        related_strategy="all",
        tags=["daily", "afternoon", "signal"]
    ))
    
    # 3. 收盘复盘
    task_ids.append(tm.create_task(
        name="执行每日收盘复盘",
        task_type="daily",
        source="system",
        priority=2,
        due_date=date,
        related_strategy="all",
        tags=["daily", "closing", "review"]
    ))
    
    # 4. 四周期策略检视
    stocks = [("000582", "北部湾港"), ("600676", "交运股份")]
    for code, name in stocks:
        task_ids.append(tm.create_task(
            name=f"检视{name}({code})四周期策略状态",
            task_type="daily",
            source="strategy",
            priority=3,
            due_date=date,
            related_strategy=f"4cycle_{code}",
            notes=f"3天/12天/26天/长期策略运行状态",
            tags=["daily", "strategy", code]
        ))
    
    return task_ids

# ========== 每日简报生成 ==========
def generate_daily_brief(tm: TaskManager, date: str, yesterday: str) -> str:
    """生成每日简报"""
    today_tasks = tm.get_pending_tasks(date)
    yesterday_pending = tm.get_yesterday_pending(yesterday)
    recent_completed = tm.get_completed_tasks(days=3)
    trading_day = tm.get_trading_day(date)
    
    lines = []
    lines.append(f"🦐【每日简报 {date}】")
    lines.append("")
    
    # 昨日未完成任务
    if yesterday_pending:
        lines.append("📋 昨日未完成：")
        for t in yesterday_pending:
            lines.append(f"  ⏳ {t['task_name']} (优先级{t['priority']})")
        lines.append("")
    
    # 今日待办
    lines.append(f"📅 今日待办（共{len(today_tasks)}项）：")
    for t in today_tasks:
        priority_emoji = "🔴" if t["priority"] == 1 else "🟡" if t["priority"] == 2 else "🟢"
        lines.append(f"  {priority_emoji} {t['task_name']}")
    lines.append("")
    
    # 近期完成（含经验）
    if recent_completed:
        lines.append(f"✅ 最近完成（共{len(recent_completed)}项）：")
        for t in recent_completed[:3]:
            lines.append(f"  ✓ {t['task_name']}")
            if t.get("lessons_learned"):
                lines.append(f"    经验: {t['lessons_learned'][:50]}...")
        lines.append("")
    
    # 交易日状态
    if trading_day:
        lines.append("📊 今日进度：")
        checks = []
        if trading_day.get("morning_check_done"):
            checks.append("盘前检查")
        if trading_day.get("signal_report_done"):
            checks.append("交易信号")
        if trading_day.get("closing_review_done"):
            checks.append("收盘复盘")
        if checks:
            lines.append(f"  已完成: {', '.join(checks)}")
        else:
            lines.append("  今日任务即将开始")
        lines.append("")
    
    return "\n".join(lines)

# ========== 虾主任务布置 ==========
def assign_task_from_master(tm: TaskManager, task_name: str, 
                           priority: int = 2, due_date: str = None,
                           notes: str = None) -> int:
    """虾主布置的任务"""
    return tm.create_task(
        name=task_name,
        task_type="one_time",
        source="虾主",
        priority=priority,
        due_date=due_date,
        notes=notes,
        tags=["虾主布置"]
    )

# ========== 主测试 ==========
if __name__ == "__main__":
    init_task_db()
    tm = TaskManager()
    
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # 初始化今日交易日
    tm.init_trading_day(today)
    
    # 生成今日任务
    task_ids = generate_daily_tasks(tm, today)
    print(f"✅ 生成今日任务 {len(task_ids)} 项")
    
    # 生成每日简报
    brief = generate_daily_brief(tm, today, yesterday)
    print("\n" + brief)
    
    # 演示：标记任务完成并记录经验
    # tm.complete_task(task_ids[0], summary="检查通过", lessons="东财接口响应慢，备用接口方案有效")
    # print("\n✅ 演示：已完成第一个任务")
    
    # 查询今日待办
    pending = tm.get_pending_tasks(today)
    print(f"\n📋 当前待办任务: {len(pending)} 项")
    for t in pending:
        print(f"  - [{t['priority']}] {t['task_name']}")
    
    tm.conn.close()
