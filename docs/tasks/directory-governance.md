# 工程目录治理与开发交付包迁移

**前期归档记录：v1 的 16 件文件已按独立评审方案归档，v2 仍保留在已关闭的 #6 历史候选中。** [DeerFlow 架构与实施门禁](../designs/current-architecture-baseline.md)及[基线任务](architecture-baseline-transition.md)继续适用，公共基座建设须另获批准。

历史状态（第一阶段记录）：当时 PR #14 确认调整后的路线 B 为开发基线，W0/MVP 尚未完成。保留以下历史记录及证据；不据旧方案恢复开发。
最初授权限于目录准备。本轮维护者明确要求先审并合并 #21，再按审过的方案执行 #22，最终复审及 CI 通过后合并。

## 全仓旧路线清理

本次逐项核对 395a7ed 上的 261 个跟踪文件。项目原有 42 个 Python 文件，34 个位于旧 P1/P2 内，另有 3 个专属检查文件。根目录只保留通用工程和现行项目入口。[历史实现与证据](../archive/legacy-runtime/README.md)给出源树、证据校验和升级时旧状态的处理方法。

| 原职责 | 核查结果与处置 |
| --- | --- |
| 产品实现 | P1 的 138 个文件、P2 的 35 个文件完整移入历史运行目录。旧 Python API、Worker、模型循环、授权与恢复逻辑仅用于复现。归档时 #27 的 Mastra 宿主尚未建设；后续主体按 [ADR 0003](../adr/0003-deerflow-architecture-transition.md)执行。 |
| 工程检查 | P2 静态导入检查和对应测试、P1 重建清理测试随归档运行。仓库脚本继续负责文档、评审流程、项目角色和技能入口。 |
| 工程包和隐藏目录 | 通用规范包、技能链接、Codex 配置与评审角色、PR 模板、分支保护配置和 GitHub Actions 有独立使用方。根 Makefile 与 CI 仍驱动历史回归。 |
| 文档与证据 | 路线 B 和 PR #14 的 7 份设计、3 份判据或历史填证、2 份任务记录归入 [route-b](../archive/route-b/)。现行决定、技术清单、原编号 76 项最终映射、H1/H2 记录、旧版仍生效的原规则、九件原件及工程流程保留各自入口。 |
| 本地与未合并历史 | Git 工作区、被忽略的凭据和缓存留在原持有位置；其他历史分支和未合并实验按固定提交追溯。此次候选只交付主分支已跟踪内容的整理。 |

独立方案评审 LAYOUT-395a7ed-D1 确认目录方案，要求保留旧卷选择和凭据忽略边界、已迁任务文档检查与同版三项 CI。回退可反向应用本次迁移提交，旧运行身份与卷分别核对，不随 Git 回退。实施复审、最终候选与逐项运行结果见本次迁移 PR。

## 冻结对象与当时事实（2026-11-23 历史记录）

- 初始基线为 `main` `3b5b9d2c285de011c523174d794792eb7cafbd97`；PR #14 合并后主分支为 `ef8bb05c79d02004d66e48e5ee8dc55c5491c723`，当前目录治理分支为 `docs/directory-governance-20261123`。
- 明镜根规则、通用规范 `engineering-standard/`、旧 v1 包 `mingjing-codex-engineering-v1/`、代码 `core/` 和 `p1-walking-skeleton/` 已存在。
- 路线 B v2 开发包仍在 [PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 未合并；[PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 和 [PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 均已合并，[PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 为当时最新的完整产品架构终裁。各 PR 实际状态及现行裁决须在任务运行时复核。
- **当时独立终裁（历史）：**[PR #14 完整产品终裁](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 已把调整后的 B 作为开发基线，[终裁正文](../archive/route-b/designs/whole-product-decision.md)明确模型出口与 Agent 工具回合恢复两个调整。PR #7 先前的“需修订后复审”属于**历史阶段**；W0/MVP 开发和上线仍要单独授权/验收。

## 第一阶段准备（历史记录）

1. 新建 [文档索引](../index.md)，以当前代码和工程规范为权威入口，并准确标识 v1 为历史资料、v2 为未合并候选、A/B 为独立实验。
2. 新建 [目录职责与迁移映射](../repository-layout.md)并纳入 W0/MVP 后续阶段治理规则；在根 `AGENTS.md` 中增加执行要求，用 CI 对索引/规则入口持续检查。
3. 当时暂不移动历史交付包或修改运行命令。所有正式开发保持暂停，不对进行中的 PR 进行推送、强制更新、合并或归档。

## v1 实施记录

- **顺序与基准。** [#21 独立审阅通过](https://github.com/zhuquanwei111/mingjing---agent/pull/21#issuecomment-7183644979)，先合并为 `743799f08f13a3392e3b2e774daf65b481370ec2`。#22 同步该基线及 #26 工程规则。迁移方案的[独立评审回执](https://github.com/zhuquanwei111/mingjing---agent/pull/22#issuecomment-7183653192)对应 `e100020ad2dc80f413c89a980b9fa88d84606e48`，列出树、入口、技能和 CI 的验收条件。
- **原件。** 按下表整体移动 16 件。实施前后 Git 目录树均为 `8c8d45fe6fd733e409858db1a31f450b7787cbf3`，16 项均为 R100，文件名和模式一致。#21 的[九件归档](reviewed-deliverables.md)独立保存，压缩包、原件指纹及固定提交阅读链接均保留。
- **入口。** 修正根规则、README、开发与工程规范、文档索引、两份架构文档、工程规范任务及 P1/P2 文档中原有的 13 处相对链接。包内相对链接保持原字节。旧路径只用于历史位置和迁移映射，其中包括早先工作区的未跟踪图片记录；未将图片纳入归档。技能仍由项目级符号链接加载通用规范原件。
- **验证与回退。** 从候选根规则读取归档规则，核对阶段失败停办、撤权终核和未知结果禁止盲重试，打开 #27 阶段衔接锚点。以 Python 3.12 运行 `make check`，另外逐个检查迁移链接、旧包内部链接、技能目标与 CI 工作流指纹。实施提交的独立复审结果与同版 CI 链接见 [PR #22](https://github.com/zhuquanwei111/mingjing---agent/pull/22)。需要回退时，仅反向应用实际移动和引用变更；保留 #21 归档与 #26/#27 的工程及架构决定。

## 长期维护与完成条件

W0 最短贯通、G 公共基座验收（G 通过并获准后才进入 M）、正式 MVP 及之后的重要功能/架构/目录变更在每个 PR 中重复执行：从 `docs/index.md` 核对现行状态，评估 README、架构/ADR、任务、运行手册和验收的影响；同步改动或说明不适用。`make check` 在 CI 检查必需入口及本地链接；审查者须检查内容和实际实现一致。v2 候选保留其历史提交；后续如需搬迁，另行确定范围和授权。

## 原则与恢复

本次工作只属于**工程治理**，不是新功能研发；继续使用仓库 [开发流程](../development.md) 和 [通用工程规范](../../engineering-standard/workflow.md)。后续从本任务、最新 Git 状态和用户提供的评审结论恢复，不依赖原聊天历史，不让旧交付包悄悄成为新权威。

## v1 目录迁移方案 · 2026-11-26

本轮处理 [PR #22](https://github.com/zhuquanwei111/mingjing---agent/pull/22)。对象已按 [#27 合并后的主分支](https://github.com/zhuquanwei111/mingjing---agent/commit/3828592f51044bcdd99c1b4f8b984412c42a8677)复核。本节保留获审方案，实施与验收见上方记录。

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
- 从根 README、文档索引、目录规范、开发流程、项目工程规范、当前与历史架构文档、工程任务记录、P1/P2 报告和隔离验收 README 逐个查找指向旧路径的链接。更新有效的相对链接，保留描述当时文件位置的文字和固定版本历史链接。当时的现行入口以 #27 为准。
- #21 的九件原件在固定提交中可以按原相对路径阅读和核验，另有原字节归档。#22 更新现行引用；归档原件维持各自指纹。#6 和 #20 均已关闭，其固定版本可继续用于历史追溯。
- `.agents/skills/engineering-handoff`、通用工程规范、CI 工作流和可执行目录保留各自位置。验证从根规则能打开原规则与现行架构，并核对 Skill 的真实目标、CI 引用和原包内 Markdown 链接。

### 评审、交付与回退

方案要求独立评审核对 16 件原件、可执行规则、历史与现行入口、#21 原件和开发工具发现路径。按[目录规范](../repository-layout.md)记录意见和整改后才移动文件。迁移后的同一 PR 应列出源树与新树、分类后的剩余旧路径、检查结果、独立审查和 CI。回退只撤销迁移和引用修改，九份设计归档与现行架构决定有各自的记录。
