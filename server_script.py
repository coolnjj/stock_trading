#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, sqlite3, json, subprocess, urllib.request
from datetime import datetime

WORKSPACE = "C:\\stock_trading"
TRADING_DB = "C:\\stock_trading\\trading_task.db"
TRADING_DAY_DB = "C:\\stock_trading\\trading.db"
FEISHU_USER = "ou_51a14c42e587cd0f52446357c5819f08"
SINA_MAP = {"000582": "sz000582", "600676": "sh600676", "300759": "sz300759", "300347": "sz300347"}

def send_feishu(target, message):
    try:
        msg = message.replace("'", "\\'").replace("\n", " ")
        openclaw_path = os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming", "npm", "openclaw.ps1")
        cmd = [
            "powershell.exe", "-ExecutionPolicy", "Bypass", "-Command",
            f"& '{openclaw_path}' message send --channel feishu --target {target} --message '{msg}'"
        ]
        r = subprocess.run(cmd, shell=False, capture_output=True, text=True)
        return r.returncode == 0
    except Exception as e:
        print(f"send_feishu error: {e}")
        return False

def get_quote(code):
    sc = SINA_MAP.get(code)
    if not sc:
        return None
    url = f"http://hq.sinajs.cn/list={sc}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode("gbk")
            p = data.split('="')[1].strip('"').split(",")
            if len(p) > 5:
                return {
                    "name": p[0],
                    "open": float(p[1]),
                    "prev": float(p[2]),
                    "current": float(p[3]),
                    "high": float(p[4]),
                    "low": float(p[5])
                }
    except Exception as e:
        print(f"get_quote error: {e}")
    return None

def selfcheck():
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{today}] Self check")
    q = get_quote("000582")
    if q:
        print(f"[OK] Sina quote: {q['current']}")
    else:
        print("[FAIL] Sina quote")
    try:
        sqlite3.connect(TRADING_DB)
        print("[OK] trading_task.db")
    except:
        print("[FAIL] trading_task.db")
    try:
        sqlite3.connect(TRADING_DAY_DB)
        print("[OK] trading.db")
    except:
        print("[FAIL] trading.db")

def monitor_loop():
    print("[Monitor] Started - checking every 5 minutes")
    while True:
        selfcheck()
        time.sleep(300)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selfcheck":
        selfcheck()
    elif len(sys.argv) > 1 and sys.argv[1] == "monitor":
        monitor_loop()
    else:
        print("Usage: python server_script.py [selfcheck|monitor]")
