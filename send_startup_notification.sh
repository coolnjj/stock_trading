#!/bin/bash
# 虾跟班每日上线通知脚本
# 使用方法：添加到Windows开机启动项，每次开机自动执行

# 发送飞书个人消息
curl -X POST "http://127.0.0.1:18789/api/send" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "feishu",
    "target": "ou_51a14c42e587cd0f52446357c5819f08",
    "message": "🦐【虾跟班每日上线通知】虾主好！小的已上线，随时为您服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆"
  }'

# 发送飞书群消息
curl -X POST "http://127.0.0.1:18789/api/send" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "feishu",
    "target": "oc_56301c379e08be3687b4edf39b034cbc",
    "message": "🦐【虾跟班每日上线通知】各位好！小的已上线，随时为大家服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆\n有需要随时@我~"
  }'

echo "[$(date)] 虾跟班上线通知已发送"
