#!/usr/bin/env python3
# 通过Gateway API发送飞书消息
import urllib.request
import urllib.error
import json
import os

GATEWAY_URL = "http://127.0.0.1:18789"
# 从环境变量或配置文件获取token
TOKEN = os.environ.get("OPENCLAW_TOKEN", "")

def send_feishu_message(target, message):
    """通过OpenClaw Gateway API发送飞书消息"""
    data = json.dumps({
        "channel": "feishu",
        "action": "send",
        "target": target,
        "message": message
    }).encode('utf-8')
    
    req = urllib.request.Request(
        f"{GATEWAY_URL}/api/message/send",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TOKEN}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # 发送个人消息
    result1 = send_feishu_message(
        "ou_51a14c42e587cd0f52446357c5819f08",
        "🦐【虾跟班每日上线通知】虾主好！小的已上线，随时为您服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆"
    )
    print("个人消息:", result1)
    
    # 发送群消息
    result2 = send_feishu_message(
        "oc_56301c379e08be3687b4edf39b034cbc",
        "🦐【虾跟班每日上线通知】各位好！小的已上线，随时为大家服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆\n有需要随时@我~"
    )
    print("群消息:", result2)
