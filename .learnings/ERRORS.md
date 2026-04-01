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
