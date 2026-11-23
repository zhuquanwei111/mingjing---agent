# 路线 B 架构准入与最短端到端方案审查任务

**当前状态：所有新业务开发暂停。首轮文档级独立评审已完成，结论为修订后复审。W0 与 MVP 均未获实施许可。**
**日期：** 2026-11-23。**来源基线：** `main` `3b5b9d2c285de011c523174d794792eb7cafbd97`。**工作分支：** `codex/review-route-b-architecture-20261123`。本分支只提交供独立评审的需求和候选方案，不接管现有开发工作区。

## 目标与交付

1. 审查总体 Python + PostgreSQL + Temporal + Pydantic AI 路线 B 的独立性、可行性、安全、技术取舍、长期成本和历史资产边界，而不只是审核首个质量判定函数。
2. 用 [本任务的冻结审查需求](../requirements/route-b-architecture-gate.md)与 [W0 / MVP 候选方案](../designs/route-b-walking-skeleton-mvp.md)明确受审对象。独立审查后由原设计者逐项回应；本轮逐项回复和证据提交给独立评审者复核。
3. 评审通过并由用户处理重大决定后，才可根据正式任务拆分启动最短端到端技术链路。继续的业务 MVP 需另外确定用户价值和正式业务范围。

## 权威输入和限制

- **完整需求：**《明镜智能体应用——通用工程架构需求说明书》v0.4.1（2026-11-21，SHA-256 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`）。原件属于用户资料，其状态“待评审”应保留。**公开仓库中的摘要不等于完整原件。** 在用户授权的审查环境核对全文和指纹；未读到原件不得声称“全需求审查已完成”。
- **当前分支与已有工作：** [主线](https://github.com/zhuquanwei111/mingjing---agent/tree/3b5b9d2c285de011c523174d794792eb7cafbd97)、[架构 A/B 实验 PR #5](https://github.com/zhuquanwei111/mingjing---agent/pull/5)、[路线 B 首项开发 PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6)；本任务不删除、修改或合并它们。
- **核心取舍：** [A/B 实验报告](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md)、[路线 B 架构](https://github.com/zhuquanwei111/mingjing---agent/blob/c22aff11d48bd6bc0accf245e799e889e7c8f4a1/mingjing-codex-engineering-v2/architecture.md)、[交付顺序](https://github.com/zhuquanwei111/mingjing---agent/blob/c22aff11d48bd6bc0accf245e799e889e7c8f4a1/mingjing-codex-engineering-v2/delivery.md)。需由独立 Reviewer 按材料原文核验，不用先前 Agent 的评价替代审查。
- **实施状态：** PR #6 的质量库已经有聚焦测试和独立增量评审记录，但新路线的正式端到端系统尚未得到贯通验收。

## 按既有工程规范实施审查

[通用开发规范](../../engineering-standard/workflow.md)、[独立评审契约](../../engineering-standard/templates/review.md)与 [Codex CLI 关卡](../../engineering-standard/adapters/codex-cli/README.md)继续适用。

1. 独立 Reviewer 从**全新、只读、无原设计聊天历史**的上下文开始。固定需求、方案、基线版本，提供必要项目事实。若本机子代理无只读权限或 CLI 初始化失败，改用用户允许的独立只读会话人工转交；不得假称已独立评审。
2. Reviewer 根据 TS-01–07、FR-01–41、NFR-01–11 与 AC-01–17 的实际覆盖范围，对候选方案给出 **阻断 / 必要修正 / 待实测 / 可选**，每条有证据、影响和建议处理。评审中不修改正式业务代码。
3. 原设计者逐项回应和修订。实质架构修改与新的实验结果应检查旧评审是否失效，必要时重新独立评审；重大业务和架构取舍由用户决定。
4. 只有**完整源文件可读、关键问题关闭、必要 Spike 有可重现证据、W0 的目标与验收经评审、用户需要的决定已明确**，才将开发状态从暂停改为已授权。阶段验证不能冒称生产可用或正式 MVP 已完成。
5. 本次仅提交需求、设计候选与任务记录至 Draft PR；检查链接和 PR CI 的结果只证明文档集成，没有独立架构准入结论。

## 当前完成、未完成与下一安全动作

| 项目 | 状态 | 证据和下一步 |
| --- | --- | --- |
| 冻结审查任务和版本输入 | 文档已备 | [审查需求](../requirements/route-b-architecture-gate.md) |
| Walking Skeleton 与 MVP 区分 | 评审草案已备 | [候选纵切与验收](../designs/route-b-walking-skeleton-mvp.md) |
| 独立架构评审 | **首轮完成，需修订后复审** | [首轮终审](https://github.com/zhuquanwei111/mingjing---agent/pull/7#issuecomment-7099754918)核对了 v0.4.1 原件及七幅图；原件仍标注待评审 |
| 原设计者处理与复审 | **七项已答复，复审待执行** | [修订协议与 W0 顺序](../designs/route-b-architecture-revisions.md) · [固定版本与复算证据](../designs/route-b-review-evidence.md) |
| 最短端到端实施 | **未授权 / 未开发** | 架构准入后，按新任务分支和分阶段验收执行 |
| 正式 MVP 业务范围 | **待用户确认** | 根据已评审架构确定第一类用户任务及验收 |
| PR #6 合并及后续编码 | **继续暂停** | 核对时 #6 为 Open、非 Draft，未合并；本任务保持编码暂停 |

原冻结需求的历史快照保留，关于 #6 的 Draft 状态以本次查询为准。下一步由新的独立上下文核对同一 PR 的最新提交、七项回复及来源，逐条给出已关闭、需补证或阻断的理由。用户确认实质取舍并另行授权后再进入相应阶段。
