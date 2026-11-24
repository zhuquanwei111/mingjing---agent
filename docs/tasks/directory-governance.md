# 工程目录治理与开发交付包迁移

**状态：第一阶段已建立文档索引与长期治理规则；实际 v1/v2 迁移仍待独立审查。PR #14 已确认调整后的路线 B 为开发基线，W0/MVP 尚未完成。**
本任务依据用户在独立架构评审结束后启动目录整理的授权，处理文档/旧包位置和文档权威问题，**不代表用户授权合并、发布或恢复新开发**。

## 冻结对象与当前事实

- 初始基线为 `main` `3b5b9d2c285de011c523174d794792eb7cafbd97`；PR #14 合并后主分支为 `ef8bb05c79d02004d66e48e5ee8dc55c5491c723`，当前目录治理分支为 `docs/directory-governance-20261123`。
- 明镜根规则、通用规范 `engineering-standard/`、旧 v1 包 `mingjing-codex-engineering-v1/`、代码 `core/` 和 `p1-walking-skeleton/` 已存在。
- 路线 B v2 开发包仍在 [PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 未合并；[PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 和 [PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 均已合并，[PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 为最新的完整产品架构终裁。各 PR 实际状态须在任务运行时复核。
- **当前独立终裁：**[PR #14 完整产品终裁](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 已把调整后的 B 作为开发基线，[终裁正文](../designs/whole-product-decision.md)明确模型出口与 Agent 工具回合恢复两个调整。PR #7 先前的“需修订后复审”属于**历史阶段**；W0/MVP 开发和上线仍要单独授权/验收。

## 本次已完成的安全准备

1. 新建 [文档索引](../index.md)，以当前代码和工程规范为权威入口，并准确标识 v1 为历史资料、v2 为未合并候选、A/B 为独立实验。
2. 新建 [目录职责与迁移映射](../repository-layout.md)并纳入 W0/MVP 后续阶段治理规则；在根 `AGENTS.md` 中增加执行要求，用 CI 对索引/规则入口持续检查。
3. 暂不移动历史交付包或修改运行命令。所有正式开发保持暂停，不对进行中的 PR 进行推送、强制更新、合并或归档。

## 后续必须完成

- [x] 已核对早期 PR #7 与后续 PR #14 的不同结论，将 PR #14 最新裁决和 W0/MVP 未完成边界接入索引。
- [ ] PR #6 v2 开发包迁移前核对是否体现 PR #14 的两项设计调整和完整产品验收边界；同步其他在途 PR 的路径差异。
- [ ] 给出逐文件迁移清单，并让独立 Reviewer 审查其对根规则、CI、Skills、历史引用、并行 PR 的影响。
- [ ] 在独立迁移分支进行 v1 历史包移动，并在允许后根据实际采纳的架构方案处理 v2。处理所有源文件与 Markdown 的实际引用，禁止丢失仍有效规则。
- [ ] 运行 `make check`、相对文档链接/技能检测、适用测试与 GitHub 当前 head 的 CI；对不可验证的路径和本地环境如实记录。
- [ ] 提交目录迁移独立 Draft PR，提供 rename 摘要、对照清单、审查问题处理和完整验证结果，由用户决定是否合并。

## 长期维护与完成条件

W0 最短贯通、正式 MVP 及之后的重要功能/架构/目录变更在每个 PR 中重复执行：从 `docs/index.md` 核对现行状态，评估 README、架构/ADR、任务、运行手册和验收的影响；同步改动或说明不适用。`make check` 在 CI 检查必需入口及本地链接；审查者须检查内容和实际实现一致。迁移 v1/v2 仍是未完成的独立任务，不因本次索引合并而自动判为完成。

## 原则与恢复

本次工作只属于**工程治理**，不是新功能研发；继续使用仓库 [开发流程](../development.md) 和 [通用工程规范](../../engineering-standard/workflow.md)。后续从本任务、最新 Git 状态和用户提供的评审结论恢复，不依赖原聊天历史，不让旧交付包悄悄成为新权威。
## v1 实际迁移的评审稿（2026-11-24）

冻结基线 [e759892a](https://github.com/zhuquanwei111/mingjing---agent/commit/e759892afdfae7fe08c51e90b5fed977b053e905)。本节提交迁移方案供独立评审。收到回执并处理阻断后，在同一 PR 移动目录、修订引用、提交实际验证记录。

### 文件映射与原件验证

以下每个文件均从 `mingjing-codex-engineering-v1/` 原名移至 `docs/archive/engineering-v1/`。16 份原件的 Git 树为 `8c8d45fe6fd733e409858db1a31f450b7787cbf3`。基线的包内 Markdown 相对链接已逐条检查，均能在原包内解析。实际移动后，以新目录的完整 Git 树与该值相等验收文件名、模式和字节。

| 内容 | 文件 |
| --- | --- |
| 产品与架构 | `01_PROJECT_BRIEF.md`、`02_ARCHITECTURE.md`、`03_TECH_STACK.md`、`04_CAPABILITY_CONTRACT.md` |
| 安全、数据与计划 | `05_SECURITY_AND_RELIABILITY.md`、`06_DATA_AND_ARTIFACTS.md`、`07_IMPLEMENTATION_PLAN.md`、`08_ACCEPTANCE_TESTS.md`、`09_OPEN_QUESTIONS.md` |
| 规则与入口 | `AGENTS.md`、`README.md`、`CODEX_START_PROMPT.md` |
| 版本与历史证据 | `DEPENDENCY_LOCK.md`、`P0_REPORT.md`、`P1_EXECUTION_PLAN.md`、`RISK_REGISTER.md` |

### 实际迁移时要改的入口

- **仍生效的规则。** 根 `AGENTS.md` 继续明确要求从仓库根读取有效工程规则。把旧规则中的业务与授权边界、P0–P3 门禁、修改及停止条件接入当前工程规范，逐条对照存档原文。由独立读者从根入口复述这些约束，并说明与 #14 现行裁决的关系。
- **现行文档与证据。** 更新根 README、工程索引、开发流程、项目工程规范、完整产品裁决的契约链接，以及 P2 报告、P1 README、Instabox 证据 README 和工程规范任务中的有效链接。目录治理文件保留原路径作为迁移映射，历史记录中提到的本地未跟踪文件保留原叙述。用 Git 的文件清单分辨当前入口、历史事实和固定 SHA 引用。
- **已审原件。** [交付物归档 PR #21](https://github.com/zhuquanwei111/mingjing---agent/pull/21) 的三份 MVP 文件有已审指纹。其中组件表正文含一个指向旧包技术栈的相对链接。执行前先吸收 #21 的正式归档提交，保留该文件的原字节及可从仓库取回的固定版本。当前阅读版只改这个链接，记录原版与导航修订版的两个指纹和可核对差异；其余原件照原指纹验收。为保证克隆后仍能核对全部七个原件，将这一份原稿逐字节保存在 `docs/archive/MVP-SCOPE-COMP-01/whole-product-component-selection.md.txt`，校验原 SHA-256，以索引区分原始文本与可导航的阅读版。
- **并行分支。** #20 更改 README 和索引，合入后需保留两套导航。#6 更改旧包的 README 与启动词，后续提取其候选资产时逐文件对照迁移映射，避免恢复根目录旧包。本次只处理 v1。
- **运行入口。** 保持根工程规范包、现有 Skill 发现路径、工作流和运行命令。执行前后核对根规则、Skill 实际解析位置与 CI 路径，并验证新检出能从入口读取现行规则和历史版本。

### 评审者判据与实施回执

对照上述清单核实原件可找回、有效规则可发现、当前链接可用、并行 PR 有明确处理方式。记录固定评审提交、审查意见、整改及结论。实施后附 Git 重命名摘要、16 文件树相等结果、全仓库旧路径剩余引用分类、新旧规则对应关系、`make check` 及对应 CI。由维护者复核后合并，回退使用本迁移 PR 对应提交。当前归档路径与运行状态仍以实际 Git 树为准。
