#!/usr/bin/env python3
"""
启动通知脚本 - 每天首次启动时发送飞书通知
- 发送上线消息 + 福州天气
- 发送到个人会话和群聊
- 每天只发一次（通过flag文件判断）
"""
import os
import sys
import json
import urllib.request
from datetime import datetime

CONFIG_FILE = "/home/wenkun/.openclaw/openclaw.json"
FLAG_FILE = "/home/wenkun/.openclaw/workspace/.last_online_notification"

def load_config():
    with open(CONFIG_FILE) as f:
        d = json.load(f)
    feishu = d["channels"]["feishu"]
    return feishu["appId"], feishu["appSecret"]

def get_weather():
    try:
        url = "https://wttr.in/Fuzhou?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "curl"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        current = data["current_condition"][0]
        temp = current["temp_C"]
        desc = current["weatherDesc"][0]["value"]
        wind = current["windspeedKmph"]
        humidity = current["humidity"]
        return f"{temp}°C，{desc}，风速{wind}km/h，湿度{humidity}%"
    except Exception as e:
        return f"天气获取失败（{e}）"

def get_tenant_access_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["tenant_access_token"]

def send_message(token, to, content, receive_id_type="open_id"):
    url = f"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type={receive_id_type}"
    payload = {
        "receive_id": to,
        "msg_type": "text",
        "content": json.dumps({"text": content})
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())

def main():
    today = datetime.now().strftime("%Y-%m-%d")

    # 检查是否今天已发送
    if os.path.exists(FLAG_FILE):
        with open(FLAG_FILE) as f:
            last_date = f.read().strip()
        if last_date == today:
            print("今日已发送上线通知，跳过")
            return

    app_id, app_secret = load_config()
    weather = get_weather()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    USER_ID = "ou_51a14c42e587cd0f52446357c5819f08"
    GROUP_ID = "oc_56301c379e08be3687b4edf39b034cbc"

    msg = f"""🦐 虾跟班已上线！
━━━━━━━━━━━━━━━
⏰ 上线时间：{now}
🌤️ 福州天气：{weather}
━━━━━━━━━━━━━━━
今天有什么需要我帮忙的吗？"""

    try:
        token = get_tenant_access_token(app_id, app_secret)
        send_message(token, USER_ID, msg, "open_id")
        print("✅ 个人通知已发送")
        send_message(token, GROUP_ID, msg, "chat_id")
        print("✅ 群聊通知已发送")
        with open(FLAG_FILE, "w") as f:
            f.write(today)
        print("✅ 今日标记已记录")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
