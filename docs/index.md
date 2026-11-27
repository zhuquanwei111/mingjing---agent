# 明镜工程文档索引

**状态：当前仓库文档导航。** 目录迁移按单独任务执行；本索引在 W0、MVP 与后续重要开发交付时持续核对更新。 本页负责帮助维护者和 Codex 找到现行资料，不以目录是否存在替代正式评审或 Git 证据。实际工作分支、提交、PR 和 CI 状态应在使用时重新核对。本次整理不得自动恢复已暂停的业务开发。

## 从哪里开始

| 目的 | 当前权威入口 | 备注 |
| --- | --- | --- |
| 仓库状态与使用方法 | [根 README](../README.md) 与 [根 AGENTS](../AGENTS.md) | 开发前检查实际分支、工作区和相关 PR |
| 历史 P2 实现与回归 | [P2 操作说明](archive/legacy-runtime/core/README.md)与[旧版本说明](archive/legacy-runtime/core/VERSIONING.md) | 对应历史实现与当前 CI 回归 |
| 新能力开发者从这里开始 | [现行能力接入边界](designs/current-architecture-baseline.md#capability-onboarding) | 旧 P2 可复现接口仅作历史样例；明镜接线和正式业务 API 尚待建设，AC-17 在 G 实际验收 |
| P1 验证与可复现环境 | [P1 说明](archive/legacy-runtime/p1-walking-skeleton/README.md)、[P1 历史报告](archive/legacy-runtime/p1-walking-skeleton/P1_REPORT.md) | 历史记录以原 SHA 和 CI 为准 |
| 通用 Codex 工程规范 | [通用规范包](../engineering-standard/README.md) | 含执行脚本、Skills、模板，不是明镜业务交付包 |
| 明镜如何采用工程规范 | [项目接入说明](engineering-standard.md)、[执行性审查](engineering-standard-execution.md) | 通用层与项目例外分开 |
| 开发与任务接续 | [开发流程](development.md)、[长任务计划](PLANS.md)、[设置及环境边界](configuration.md) | 任务具体状态以所属任务记录和实际 Git 状态核对 |
| 需求与验收 | [D01–D13 生效修订](requirements/current-engineering-requirements.md)、[76 项映射](requirements/final-architecture-mapping.csv)、[工程流程需求](requirements/engineering-standard.md) | 原始编号保留，按现行判据逐阶段签收 |
| 当前产品架构与选型 | [DeerFlow 架构](designs/current-architecture-baseline.md)、[架构图与契约](designs/architecture-final/contracts.md)、[技术清单](designs/architecture-final/technology.csv)、[实施门禁](designs/architecture-final/gates-and-risks.md) | 主体已定，H 核实际制品，W0/G 及业务待验 |
| 历史架构与原需求证据 | [PR #14 独立终裁](archive/route-b/designs/whole-product-decision.md)、[原 76 项历史填证](archive/route-b/requirements/whole-product-acceptance-results.md) | 保留原需求、证据范围和失败；不作为新组合的通过证明 |
| 首期设计历史原件 | [九份原件、文件指纹与 W0 设计回执](tasks/reviewed-deliverables.md) | 用于追溯早期业务范围、组件计划和验收设计；现行建设按上列最终架构执行 |
| 技术决定 | [ADR 目录](adr/) | 记录拟议、接受、替代与撤回，状态必须与当前事实一致 |

历史工程材料可从[P1/P2 回归与原始证据](archive/legacy-runtime/README.md)和[历史路线 B 裁决](archive/route-b/designs/whole-product-decision.md)进入。

## 当前架构与历史的区别

- [v1 历史工程交付包](archive/engineering-v1/README.md)已迁至归档目录。根 AGENTS 继续要求读取[原工程规则](archive/engineering-v1/AGENTS.md)，按[根规则](../AGENTS.md)保留安全、阶段及停止条件，冲突判据按 R3 修订。新任务按现行架构与实施门禁接续。
- [v2 路线 B 开发包候选 PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 已关闭，保留为**未合并的历史候选交付**，当前 main 不含该目录；不按该技术栈继续新建设。可复用契约和验证资产须按新组合复核。
- [早期架构评审 PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 已合并，曾要求修订；[后续完整产品独立终裁 PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) **已合并，曾确认调整后的路线 B 为当时开发基线**。两次评审对应历史阶段；保留原证据，不再将 B 视作新开发指令。
- [独立 Reviewer 机制 PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 已合并，属于工程流程，不替代产品架构终裁。
- [A/B 隔离实验 PR #5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) 保存两路实际实验材料；它不是合并到 main 的产品实现。

当前主体选择见 [ADR 0003](adr/0003-deerflow-architecture-transition.md)，各阶段从[基线任务](tasks/architecture-baseline-transition.md)接续。[Mastra 历史导航](archive/mastra-20261126/README.md)保留旧选型、H1/H2 正反例及固定版本；[ADR 0002](adr/0002-mastra-architecture-transition.md)记录当时的取舍。

## 目录治理及资料规则

参见[目录职责、迁移映射和验收](repository-layout.md)及[16 件原件与校验记录](tasks/directory-governance.md)。正式设计保存在 `docs/designs/`；Git 保存正式工程记录。后续迁移按目录治理规则逐项审查。
## W0、MVP 和后续开发如何持续维护

- **已有开发分支**不能假定自动继承本规范；启动 W0/MVP 或接续旧 PR 时要与最新 `main` 比较，安全同步适用规则及文档入口，再以该候选复验。不得为同步而覆盖未提交的他人改动。
- **每次阶段交付之前**，实施者根据实际代码、受控需求与验收结果核对本索引、根 README、受影响的架构设计/ADR、任务记录、运行说明和相关引用；完成状态必须给出具体 PR、提交及运行证据，不能只凭 CI 绿灯宣布用户目标完成。
- **W0 通过时**，标明最短端到端技术链路实测范围和剩余风险，不写成 G、MVP 或生产已完成；**G 通过后**才可开始首个正式业务 M，按实际公共基座验收补证（含独立 AC-17）；**MVP 通过时**，单独补用户任务、业务权限、目标环境与业务验收。后续功能/架构/目录变化同样执行“检查影响→更新相关文档或说明不适用→审查→CI→合并”的流程。
- 新的正式技术决定覆盖旧版时更新此入口；旧版方案保留版本和来源，但明确标注为历史。规范详情见[目录治理规则](repository-layout.md)，自动链接检查由 [make check](../Makefile) 执行，语义正确性由实施者和 Reviewer 核对。
