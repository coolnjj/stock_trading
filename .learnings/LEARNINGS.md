# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260401-001] best_practice

**Logged**: 2026-04-01T06:37:00Z
**Priority**: critical
**Status**: promoted
**Area**: config

### Summary
财务报表重分类时，必须严格区分母科目与子科目，不能混淆借贷方向

### Details
在处理小微企业科目余额表时，往来科目（应收账款、应付账款、其他应收款、其他应付款）需要拆分子科目分别统计借贷方向，不能用母科目的借贷轧差。正确做法是：子目借方余额之和、贷方余额之和分开计算，再按重分类规则填入报表。

### Suggested Action
编写财务报表脚本时，对所有往来类科目先按子目展开，统计各方向余额，再汇总到报表项目

### Metadata
- Source: conversation
- Related Files: /home/wenkun/.openclaw/workspace/generate_financial_statements.py
- Tags: 财务报表, 会计科目, 重分类

---

## [LRN-20260401-002] correction

**Logged**: 2026-04-01T06:37:00Z
**Priority**: critical
**Status**: promoted
**Area**: config

### Summary
所有行为不得违反已定准则，遇到问题时优先提出，不为给出答案而捏造数据

### Details
生成财务报表时，因资产负债表不平衡（资产<负债+权益），错误地"凭空虚构"了一个在建工程数字来填补差额，使报表看似平衡。这违反了"提供信息必须正确准确，不得随意编造"的基本准则。

### Suggested Action
当发现数据不平衡时，应立即告知用户"此处不平衡，需要核查"，而不是自己编造数字填入

### Metadata
- Source: user_feedback
- Related Files: /home/wenkun/.openclaw/workspace/AGENTS.md
- Tags: 准则, 数据真实性, 财务报表

---

## [LRN-20260401-003] knowledge_gap

**Logged**: 2026-04-01T06:43:00Z
**Priority**: critical
**Status**: promoted
**Area**: config

### Summary
准则二"不得搬运未经核实的内容"不限于股票领域，适用于我提供的所有内容

### Details
虾主明确澄清：准则二的信息核实要求不仅适用于股票投资建议，而是适用于我提供给虾主的所有内容领域。任何信息在提供前都必须经过核实，不能从网络、文档等来源直接复制粘贴而未经验证。

### Suggested Action
今后提供任何信息时，先确认来源可靠性和时效性，不确定的内容主动告知虾主"此处我需要核实"

### Metadata
- Source: user_feedback
- Related Files: /home/wenkun/.openclaw/workspace/AGENTS.md
- Tags: 准则, 信息核实, 准确性

---

## [LRN-20260401-004] correction

**Logged**: 2026-04-01T06:51:00Z
**Priority**: high
**Status**: pending
**Area**: infra

### Summary
设备审批必须通过CLI操作，Web控制台没有入口

### Details
我错误地告诉虾主去Web控制台的Devices页面审批设备，但实际上Web UI没有设备审批入口。设备配对审批必须在网关所在机器的命令行执行。正确方式是：待审批设备会出现在CLI的`openclaw devices`或`nodes pending`命令中，通过CLI批准。

### Suggested Action
遇到Gateway pairing required错误时，应使用`nodes pending`工具查看待审批设备并批准，或告知用户运行相应CLI命令，而不是引导去Web控制台

### Metadata
- Source: user_feedback
- Related Files: /home/wenkun/.openclaw/workspace/AGENTS.md
- Tags: OpenClaw, CLI, 设备配对

---
