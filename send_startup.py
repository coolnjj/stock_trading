#!/usr/bin/env python3
# 虾跟班每日上线通知脚本
import subprocess
import json

# 调用openclaw发送飞书个人消息
result = subprocess.run(
    ['openclaw', 'message', '--channel', 'feishu', '--target', 'ou_51a14c42e587cd0f52446357c5819f08', '--message', '🦐【虾跟班每日上线通知】虾主好！小的已上线，随时为您服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆'],
    capture_output=True, text=True
)
print("个人消息:", result.returncode, result.stdout, result.stderr)

# 调用openclaw发送飞书群消息
result2 = subprocess.run(
    ['openclaw', 'message', '--channel', 'feishu', '--target', 'oc_56301c379e08be3687b4edf39b034cbc', '--message', '🦐【虾跟班每日上线通知】各位好！小的已上线，随时为大家服务😎\n📊 A股实时行情 | 📈 做T策略 | 🔍 多引擎搜索 | 🧠 长期记忆\n有需要随时@我~'],
    capture_output=True, text=True
)
print("群消息:", result2.returncode, result2.stdout, result2.stderr)
