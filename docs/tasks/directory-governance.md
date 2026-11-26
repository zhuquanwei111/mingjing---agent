# 工程目录治理与开发交付包迁移

**现行状态：第一阶段已建立文档索引与长期治理规则；实际 v1/v2 迁移仍待独立审查。** 本任务仍是目录治理接续入口；2026-11-23 的 PR #14 路线 B 裁决已转为历史依据，不是新开发基线。当前以[最终架构与实施门禁](../designs/current-architecture-baseline.md)及[基线任务](architecture-baseline-transition.md)为准：Mastra 主体及 H2 的 B04 限定方案已确认，正式实施暂停，G 验收先于 M。

历史状态（第一阶段记录）：当时 PR #14 确认调整后的路线 B 为开发基线，W0/MVP 尚未完成。保留以下历史记录及证据；不据旧方案恢复开发。
本任务依据用户在独立架构评审结束后启动目录整理的授权，处理文档/旧包位置和文档权威问题，**不代表用户授权合并、发布或恢复新开发**。

## 冻结对象与当时事实（2026-11-23 历史记录）

- 初始基线为 `main` `3b5b9d2c285de011c523174d794792eb7cafbd97`；PR #14 合并后主分支为 `ef8bb05c79d02004d66e48e5ee8dc55c5491c723`，当前目录治理分支为 `docs/directory-governance-20261123`。
- 明镜根规则、通用规范 `engineering-standard/`、旧 v1 包 `mingjing-codex-engineering-v1/`、代码 `core/` 和 `p1-walking-skeleton/` 已存在。
- 路线 B v2 开发包仍在 [PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 未合并；[PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 和 [PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 均已合并，[PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 为当时最新的完整产品架构终裁。各 PR 实际状态及现行裁决须在任务运行时复核。
- **当时独立终裁（历史）：**[PR #14 完整产品终裁](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 已把调整后的 B 作为开发基线，[终裁正文](../designs/whole-product-decision.md)明确模型出口与 Agent 工具回合恢复两个调整。PR #7 先前的“需修订后复审”属于**历史阶段**；W0/MVP 开发和上线仍要单独授权/验收。

## 本次已完成的安全准备

1. 新建 [文档索引](../index.md)，以当前代码和工程规范为权威入口，并准确标识 v1 为历史资料、v2 为未合并候选、A/B 为独立实验。
2. 新建 [目录职责与迁移映射](../repository-layout.md)并纳入 W0/MVP 后续阶段治理规则；在根 `AGENTS.md` 中增加执行要求，用 CI 对索引/规则入口持续检查。
3. 暂不移动历史交付包或修改运行命令。所有正式开发保持暂停，不对进行中的 PR 进行推送、强制更新、合并或归档。

## 后续必须完成

- [x] 已核对早期 PR #7 与后续 PR #14 的不同结论，将 PR #14 当时的裁决和 W0/MVP 未完成边界接入索引。该历史动作已完成，现行导航已由本次架构过渡更新。
- [ ] PR #6 v2 开发包仅按历史候选处理；保留 PR #14 两项历史设计调整及验收证据，核对现行架构的可复用资产与完整产品验收边界，迁移/处置另行授权，不按旧栈实施。同步其他在途 PR 的路径差异。
- [ ] [PR #22](https://github.com/zhuquanwei111/mingjing---agent/pull/22) 是独立的 v1 迁移清单任务，与本页有共享改动；待 PR #27 进入目标基线，核对实际 main 和 PR #22 head，安全同步本页的现行入口、历史标记、旧门禁与新阶段衔接。保留已审原件、#22 独有迁移清单及独立评审要求，处理语义/文本冲突后复验，禁止恢复旧路线。
- [ ] 给出逐文件迁移清单，并让独立 Reviewer 审查其对根规则、CI、Skills、历史引用、并行 PR 的影响。
- [ ] 在独立迁移分支进行 v1 历史包移动，并在允许后根据实际采纳的架构方案处理 v2。处理所有源文件与 Markdown 的实际引用，禁止丢失仍有效规则。
- [ ] 运行 `make check`、相对文档链接/技能检测、适用测试与 GitHub 当前 head 的 CI；对不可验证的路径和本地环境如实记录。
- [ ] 提交目录迁移独立 Draft PR，提供 rename 摘要、对照清单、审查问题处理和完整验证结果，由用户决定是否合并。

## 长期维护与完成条件

W0 最短贯通、G 公共基座验收（G 通过并获准后才进入 M）、正式 MVP 及之后的重要功能/架构/目录变更在每个 PR 中重复执行：从 `docs/index.md` 核对现行状态，评估 README、架构/ADR、任务、运行手册和验收的影响；同步改动或说明不适用。`make check` 在 CI 检查必需入口及本地链接；审查者须检查内容和实际实现一致。迁移 v1/v2 仍是未完成的独立任务，不因本次索引合并而自动判为完成。

## 原则与恢复

本次工作只属于**工程治理**，不是新功能研发；继续使用仓库 [开发流程](../development.md) 和 [通用工程规范](../../engineering-standard/workflow.md)。后续从本任务、最新 Git 状态和用户提供的评审结论恢复，不依赖原聊天历史，不让旧交付包悄悄成为新权威。

## v1 目录迁移方案 · 2026-11-26 待独立评审

本轮处理 [PR #22](https://github.com/zhuquanwei111/mingjing---agent/pull/22)。对象已按 [#27 合并后的主分支](https://github.com/zhuquanwei111/mingjing---agent/commit/3828592f51044bcdd99c1b4f8b984412c42a8677)复核。先确认 [#21 的历史归档](https://github.com/zhuquanwei111/mingjing---agent/pull/21)进入主分支，再在本分支移动旧包。此版仅提交迁移清单，接受独立评审后执行。

### 逐文件映射

以下 16 个文件从 `mingjing-codex-engineering-v1/` 原名移至 `docs/archive/engineering-v1/`。当前源树为 `8c8d45fe6fd733e409858db1a31f450b7787cbf3`。执行前核对最新源树，执行后比对完整 Git 树和重命名清单，以验证名称、模式、内容及包内链接。

| 内容 | 文件 |
| --- | --- |
| 产品与架构 | `01_PROJECT_BRIEF.md`、`02_ARCHITECTURE.md`、`03_TECH_STACK.md`、`04_CAPABILITY_CONTRACT.md` |
| 安全、数据与计划 | `05_SECURITY_AND_RELIABILITY.md`、`06_DATA_AND_ARTIFACTS.md`、`07_IMPLEMENTATION_PLAN.md`、`08_ACCEPTANCE_TESTS.md`、`09_OPEN_QUESTIONS.md` |
| 规则与入口 | `AGENTS.md`、`README.md`、`CODEX_START_PROMPT.md` |
| 版本与历史证据 | `DEPENDENCY_LOCK.md`、`P0_REPORT.md`、`P1_EXECUTION_PLAN.md`、`RISK_REGISTER.md` |

### 仍在使用的入口

- 根 `AGENTS.md` 继续明示读取归档内的原规则；原规则的业务、安全、编码、P0–P3 门禁及停止条件原样保留。现行建设依最终架构的 H/W0a/W0b/G/M/T/P；按[阶段对应表](../designs/current-architecture-baseline.md#stage-gate-crosswalk)核对 W0、G 与首个业务的放行条件。归档目录本身不承担技术选型。
- 从根 README、文档索引、目录规范、开发流程、项目工程规范、当前与历史架构文档、工程任务记录、P1/P2 报告和隔离验收 README 逐个查找指向旧路径的链接。更新有效的相对链接，保留描述当时文件位置的文字和固定版本历史链接。现行入口以 #27 为准。
- #21 的九件原件在固定提交中可以按原相对路径阅读和核验，另有原字节归档。#22 更新现行引用；归档原件维持各自指纹。#6 和 #20 均已关闭，其固定版本可继续用于历史追溯。
- `.agents/skills/engineering-handoff`、通用工程规范、CI 工作流和可执行目录保留各自位置。验证从根规则能打开原规则与现行架构，并核对 Skill 的真实目标、CI 引用和原包内 Markdown 链接。

### 评审、交付与回退

请独立评审核对 16 件原件、可执行规则、历史与现行入口、#21 原件和开发工具发现路径。按[目录规范](../repository-layout.md)记录意见和整改后才移动文件。迁移后的同一 PR 应列出源树与新树、分类后的剩余旧路径、检查结果、独立审查和 CI。回退只撤销迁移和引用修改，九份设计归档与现行架构决定有各自的记录。
