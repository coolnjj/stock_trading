# Feature Requests

Capabilities requested by the user.

---

## [FEAT-20260401-001] cross_session_memory

**Logged**: 2026-04-01T06:37:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Requested Capability
跨会话记忆功能：新窗口中能自动记住之前聊过的事情

### User Context
用户反映在新的聊天窗口中，我不会主动记得之前的对话内容，希望具备持续记忆能力

### Complexity Estimate
medium

### Suggested Implementation
需要配置 memory.backend=builtin 和 memory.citations=auto，但目前配置被 pairing 拦截，需解决 Gateway 配对授权问题

### Metadata
- Frequency: first_time
- Related Features: memory-setup skill

---
