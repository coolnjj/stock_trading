# Errors

Command failures and integration errors.

---

## [ERR-20260401-001] config_patch

**Logged**: 2026-04-01T06:37:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
Gateway配置patch失败，提示pairing required

### Error
```
gateway closed (1008): pairing required
Gateway target: ws://127.0.0.1:18789
```

### Context
尝试执行 `gateway config.patch` 添加 memory.backend 和 memory.citations 配置时，Gateway要求配对授权

### Suggested Fix
用户需在 Web 控制台（http://127.0.0.1:18789）批准设备配对

### Metadata
- Reproducible: yes
- Related Files: /home/wenkun/.openclaw/openclaw.json

---

## 2026-04-01 股票数据错误

**问题**：cron推送的收盘价与实际不符
- 原因：新浪hq.sinajs.cn接口字段解析错误，把开盘价（open）当作收盘价（close）使用了
- 正确字段顺序：name,open,close,high,low,vol,...（不是open在第三位！）

**正确做法**：使用东方财富K线接口(`push2his.eastmoney.com`)获取日K线数据，收盘价是第3个字段(索引2)
备用验证：新浪实时行情接口，收盘价是第4个字段(索引3)

**教训**：任何接口返回的数据都要对照文档或实际验证字段顺序，不能凭记忆或假设
