#!/usr/bin/env python3
"""
每日模拟交易信号生成
- 14:30 前：生成做T参考建议
- 14:50：生成一夜持仓法建议
- 15:05：收盘数据更新 + 龙头热点分析
- 15:10：生成当日交易报告推送
"""
import subprocess
import json
import urllib.request
import urllib.error
import os
from datetime import datetime

# ========== 配置 ==========
CONFIG_FILE = "/home/wenkun/.openclaw/workspace/paper_trading_config.md"
REPORT_FILE = "/home/wenkun/.openclaw/workspace/paper_trading_report.md"
GATEWAY_URL = "http://127.0.0.1:18789"
FEISHU_USER = "ou_51a14c42e587cd0f52446357c5819f08"
FEISHU_GROUP = "oc_56301c379e08be3687b4edf39b034cbc"

# ========== 行情获取 ==========
SINA_CODE_MAP = {
    "000582": "sz000582",  # 深市
    "600676": "sh600676",  # 沪市
    "002714": "sz002714",  # 深市
    "000876": "sz000876",  # 深市
}

def get_realtime_quote(codes):
    """获取新浪实时行情"""
    if not codes:
        return {}
    sina_codes = [SINA_CODE_MAP.get(c, c) for c in codes]
    codes_str = ",".join(sina_codes)
    url = f"http://hq.sinajs.cn/list={codes_str}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("gbk")
            return parse_sina_data(data, codes)
    except Exception as e:
        print(f"获取行情失败: {e}")
        return {}

def parse_sina_data(data, codes):
    """解析新浪行情数据"""
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
                "open": float(parts[1]) if parts[1] else 0,
                "close": float(parts[2]) if parts[2] else 0,  # 昨收
                "current": float(parts[3]) if parts[3] else 0,  # 当前/收盘价
                "high": float(parts[4]) if parts[4] else 0,
                "low": float(parts[5]) if parts[5] else 0,
                "volume": float(parts[8]) if parts[8] else 0,  # 成交量（手）
                "amount": float(parts[9]) if parts[9] else 0,  # 成交额（元）
                "date": parts[30] if len(parts) > 30 else "",
                "time": parts[31] if len(parts) > 31 else "",
            }
    return result

# ========== 新浪K线获取 ==========
def get_sina_kline(symbol, days=30):
    """获取新浪日K线数据 (240=日K)"""
    # symbol: sh600676, sz000582
    url = f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=5&datalen={days}"
    req = urllib.request.Request(url, headers={"Referer": "http://finance.sina.com.cn"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        print(f"获取K线失败 {symbol}: {e}")
        return []

def parse_klines(klines):
    """解析新浪K线数据"""
    result = []
    for k in klines:
        result.append({
            "date": k.get("day", ""),
            "open": float(k.get("open", 0)),
            "close": float(k.get("close", 0)),
            "high": float(k.get("high", 0)),
            "low": float(k.get("low", 0)),
            "volume": float(k.get("volume", 0)),
        })
    return result

def fval(s):
    try: return float(s)
    except: return 0

# ========== RSI计算 ==========
def calc_rsi(prices, period=6):
    """计算RSI"""
    if len(prices) < period + 1:
        return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ========== 发送飞书消息 ==========
def send_feishu(target, message):
    """通过openclaw CLI发送飞书消息"""
    result = subprocess.run(
        ["openclaw", "message", "send", "--channel", "feishu", "--target", target, "--message", message],
        capture_output=True, text=True
    )
    return {"code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

# ========== 主报告生成 ==========
def generate_day_report():
    """生成当日交易信号报告"""
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 长期持有股票
    long_stocks = ["000582", "600676"]
    long_data = get_realtime_quote(long_stocks)
    klines_000582 = parse_klines(get_sina_kline("sz000582", 30))
    klines_600676 = parse_klines(get_sina_kline("sh600676", 30))
    
    # 生成报告
    report = []
    report.append(f"🦐【{today} 模拟交易信号报告】\n")
    
    # 1. 长期持有做T信号
    report.append("=" * 30)
    report.append("📌 长期持有仓位（做T参考）")
    report.append("=" * 30)
    
    for code, name in [("000582", "北部湾港"), ("600676", "交运股份")]:
        if code in long_data:
            d = long_data[code]
            klines = klines_000582 if code == "000582" else klines_600676
            closes = [k["close"] for k in klines]
            rsi = calc_rsi(closes)
            
            change = (d["current"] - d["close"]) / d["close"] * 100
            emoji = "🔴" if change < 0 else "🟢"
            
            report.append(f"\n{name}（{code}）")
            report.append(f"当前价: {d['current']} {emoji} {change:+.2f}%")
            report.append(f"今开: {d['open']} | 最高: {d['high']} | 最低: {d['low']}")
            report.append(f"RSI(6): {rsi:.1f}")
            
            # 做T建议
            if rsi < 35:
                report.append(f"🟢 做T信号: 低吸机会，支撑位{d['low']}附近")
            elif rsi > 65:
                report.append(f"🔴 做T信号: 高抛机会，阻力位{d['high']}附近")
            else:
                report.append(f"🟡 观望，等待更好时机")
    
    # 2. 一夜持仓法
    report.append("\n" + "=" * 30)
    report.append("🌙 一夜持仓法参考")
    report.append("=" * 30)
    report.append("(需结合14:30后盘面决策，建议关注今日强势非涨停股)")
    
    # 3. 龙头热点
    report.append("\n" + "=" * 30)
    report.append("🔥 龙头热点追踪")
    report.append("=" * 30)
    report.append("(热点分析待14:30后补充)")
    
    report.append("\n" + "=" * 30)
    report.append("💡 备注")
    report.append("=" * 30)
    report.append("- 做T策略参数见 paper_trading_config.md")
    report.append("- 真实下单前请核实数据准确性")
    report.append("- 本报告仅供模拟参考，不构成投资建议")
    
    return "\n".join(report)

if __name__ == "__main__":
    report = generate_day_report()
    print(report)
    # 保存报告
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 模拟交易报告\n\n{report}\n")
    # 推送到飞书
    result = send_feishu(FEISHU_USER, report)
    print("\n发送结果:", result)
