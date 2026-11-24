# 明镜工程文档索引

**状态：当前仓库文档导航。** 目录迁移按单独任务执行；本索引在 W0、MVP 与后续重要开发交付时持续核对更新。 本页负责帮助维护者和 Codex 找到现行资料，不以目录是否存在替代正式评审或 Git 证据。实际工作分支、提交、PR 和 CI 状态应在使用时重新核对。本次整理不得自动恢复已暂停的业务开发。

## 从哪里开始

| 目的 | 当前权威入口 | 备注 |
| --- | --- | --- |
| 仓库状态与使用方法 | [根 README](../README.md) 与 [根 AGENTS](../AGENTS.md) | 开发前检查实际分支、工作区和相关 PR |
| 已合并 P2 的代码和行为 | [P2 操作说明](../core/README.md) 与 [旧版本说明](../core/VERSIONING.md) | 只代表对应代码版本，不等于新路线 B 已完成 |
| P1 验证与可复现环境 | [P1 说明](../p1-walking-skeleton/README.md)、[P1 历史报告](../p1-walking-skeleton/P1_REPORT.md) | 历史记录以原 SHA 和 CI 为准 |
| 通用 Codex 工程规范 | [通用规范包](../engineering-standard/README.md) | 含执行脚本、Skills、模板，不是明镜业务交付包 |
| 明镜如何采用工程规范 | [项目接入说明](engineering-standard.md)、[执行性审查](engineering-standard-execution.md) | 通用层与项目例外分开 |
| 开发与任务接续 | [开发流程](development.md)、[长任务计划](PLANS.md)、[设置及环境边界](configuration.md) | 任务具体状态以所属任务记录和实际 Git 状态核对 |
| 需求与验收 | [通用工程规范需求](requirements/engineering-standard.md)、[任务记录目录](tasks/) | 已有项目需求摘要不代替用户持有的完整需求原件 |
| 正式产品架构与选型 | [PR #14 独立终裁](designs/whole-product-decision.md)、[需求验收与证据](requirements/whole-product-acceptance-results.md) | 经调整的路线 B 已作为开发基线；W0、MVP 和上线各有后续验收 |
| 技术决定 | [ADR 目录](adr/) | 记录拟议、接受、替代与撤回，状态必须与当前事实一致 |

## 按阶段推进产品

[完整产品分阶段实施方案](designs/whole-product-phased-implementation.md)给出各阶段进入条件、交付物、责任接口、放行与后续工作。[需求到阶段索引](requirements/whole-product-phase-index.md)逐项对应原 23 组、76 个编号。

## 当前架构与历史的区别

- [v1 历史工程交付包](../mingjing-codex-engineering-v1/README.md) 仍暂存仓库根目录。这是**历史来源**，不应单凭其 `03_TECH_STACK.md` 或启动词确定新开发路线；其中仍被根 AGENTS 引用的安全/阶段约束必须在迁移前识别并保留。
- [v2 路线 B 开发包候选 PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 是**未合并的候选交付**，当前 main 不含该目录；不能用 PR 描述等同于独立架构评审完成。
- [早期架构评审 PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 已合并，曾要求修订；[后续完整产品独立终裁 PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) **已合并并确认调整后的路线 B 为开发基线**。两次评审对应不同阶段和修订，须保留历史证据。
- [独立 Reviewer 机制 PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 已合并，属于工程流程，不替代产品架构终裁。
- [A/B 隔离实验 PR #5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) 保存两路实际实验材料；它不是合并到 main 的产品实现。

**当前正式架构入口：**[PR #14 终裁文件](designs/whole-product-decision.md)。它不表示正式 W0、MVP 或真实流量已完成；仍未合并的 v2 交付包必须对齐终裁中的模型出站与 Agent 回合恢复调整，不能直接冒充 `main` 的已批准成品。

## 目录治理及资料规则

参见 [目录职责、迁移映射和验收](repository-layout.md)。目前优先完成入口梳理、引用清单及目录规范，**历史包搬迁与候选方案定版另作为后续受审迁移**，避免与进行中的 PR 冲突。`docs/designs/` 已保存完整产品选型与审查正文。`docs/architecture/` 仅在需要独立维护当前架构地图时再建，不为排版创建空目录。正式工程记录留在 Git；Space 可用于讨论和链接，但不自动替代正式提交。
## W0、MVP 和后续开发如何持续维护

- **已有开发分支**不能假定自动继承本规范；启动 W0/MVP 或接续旧 PR 时要与最新 `main` 比较，安全同步适用规则及文档入口，再以该候选复验。不得为同步而覆盖未提交的他人改动。
- **每次阶段交付之前**，实施者根据实际代码、受控需求与验收结果核对本索引、根 README、受影响的架构设计/ADR、任务记录、运行说明和相关引用；完成状态必须给出具体 PR、提交及运行证据，不能只凭 CI 绿灯宣布用户目标完成。
- **W0 通过时**，标明最短端到端技术链路实测范围和剩余风险，不写成 MVP 或生产已完成；**MVP 通过时**，单独补用户任务、业务权限、目标环境与业务验收。后续功能/架构/目录变化同样执行“检查影响→更新相关文档或说明不适用→审查→CI→合并”的流程。
- 新的正式技术决定覆盖旧版时更新此入口；旧版方案保留版本和来源，但明确标注为历史。规范详情见[目录治理规则](repository-layout.md)，自动链接检查由 [make check](../Makefile) 执行，语义正确性由实施者和 Reviewer 核对。
