# 项目目录职责与安全迁移规则

**状态：持续适用的项目目录与文档治理规则。** 真正移动已有交付包须另经审查与验证。 该文件定义职责和可核对迁移步骤，不单凭本文授权修改业务行为、删除旧代码或认定新技术路线已经批准。

## 目录职责

| 目录 / 文件 | 适合放什么 | 不应该放什么 |
| --- | --- | --- |
| 根 `AGENTS.md` / `README.md` | 简短规则导航、当前项目入口 | 完整旧开发包、第二套任务事实 |
| `.agents/`、`.codex/`、`.github/` | 可发现技能、Codex 配置、服务器 CI 定义 | 项目业务设计正文 |
| `engineering-standard/` | 跨项目复用的规范、模板、技能、执行脚本与可选适配 | 明镜专用技术选型或历史方案 |
| `docs/archive/legacy-runtime/` | P1/P2 历史源码、回归脚本、迁移与原始证据。CI 从这里运行两套隔离测试 | 不断增加与代码脱钩的正式项目方案 |
| `app/`（候选） | 按[现行架构与实施门禁](designs/current-architecture-baseline.md)，获单独授权后开发的正式源码与测试 | 未经过 W0/MVP 对应准入时擅自宣称完成 |
| `scripts/`、`Makefile` | 确定性检测、回归入口及辅助程序 | 只有口头承诺的自动检查 |
| `docs/requirements/` | 受控需求摘要及获准可公开的需求文档 | 未授权公开的原始材料、秘密 |
| `docs/architecture/`（目标） | 当前经确认的架构说明、C4/Mermaid 源和边界 | 尚未被批准的设计冒充当前事实 |
| `docs/designs/`（现有） | 已评审的设计、[现行架构](designs/current-architecture-baseline.md)、最终技术清单及契约 | 业务运行代码 |
| `docs/adr/` | 关键技术取舍、理由、方案和状态（拟议/接受/替代/撤回） | 没有版本与批准记录的临时口头决定 |
| `docs/tasks/` | 具体任务计划、进展、审查反馈及验收位置 | 与同一任务并存的第二套真相 |
| `docs/runbooks/`、`docs/reports/`（目标） | 有实际运行职责的操作手册和正式报告 | 自动复制敏感日志及秘密 |
| `docs/archive/` | 不再作为现行入口的历史方案，保留原 SHA、日期和与现行方案的关系 | 有效的执行规则未经抽取就直接弃用 |

实际项目可以保持更简单的布局；以上“目标”类目录无需提前创建为空目录。现有工程规范的 [文档和权限约定](../engineering-standard/operations.md)继续适用。

## 文件迁移与保留位置

| 来源 | 目标 / 处理方式 | 校验与适用范围 |
| --- | --- | --- |
| `mingjing-codex-engineering-v1/`（原址） | [v1 历史包](archive/engineering-v1/README.md)已按原名整体迁入 `docs/archive/engineering-v1/` | 根 AGENTS 显式加载[迁入的原规则](archive/engineering-v1/AGENTS.md)；[迁移任务](tasks/directory-governance.md)记录完整树及引用核对 |
| PR #6 的 `mingjing-codex-engineering-v2/` | 历史候选材料；受审后按维护者认可的历史设计目录归档，选择性复用契约和证据 | PR #6 已关闭且未合并，不是现行实施基线；先核[现行架构](designs/current-architecture-baseline.md)及该 PR 实际状态，不得凭空从主分支搬迁不存在的文件 |
| 已有 `docs/PLANS.md`、`docs/configuration.md`、`docs/development.md` | 原路径先保持，作为工作流程和配置事实入口 | 不为了目录整齐迁移活跃脚本引用的路径 |
| `core/P2_REPORT.md`、`p1-walking-skeleton/P1_REPORT.md` | [历史运行目录](archive/legacy-runtime/README.md)内保留与源码对应的报告 | 根 Makefile 接续原回归入口；证据按固定版本核验 |
| `engineering-standard/` | 保留仓库根，作为可独立复制的通用规范包 | 不误放进 `docs/` 造成执行脚本和技能路径变化 |

## 迁移的实际执行门禁

1. **准备和冻结对象。** 先读取 [文档索引](index.md)、根 [AGENTS](../AGENTS.md)、现行 PR、最终独立架构评审报告及其具体版本。核对任务工作区与其它分支。以[现行架构与实施门禁](designs/current-architecture-baseline.md)核对新旧权威；PR #14 为历史裁决，PR #6 是已关闭的历史候选；状态不因目录迁移而升级。
2. **独立评审迁移方案。** 让不参与本次目录设计的 Reviewer 检查历史业务规则保留、Git 路径引用、Codex 技能发现、文档权威与被其他 PR 引用的风险；记录并处理阻断。
3. **仅在隔离分支迁移。** 用 Git 识别重命名，保留原内容，不混入业务重构。以全库文本查找旧路径，更新真实引用；不能只更新 README 里的链接。涉及有效规则的路径变更，重新验证 Codex 在新目录确实读到。
4. **完整检查。** 运行 `make check`、文档引用和技能入口检查；人工核对 GitHub 相对路径、历史证据链接、重要 README 及架构图源。校验无失联或越界链接，必要时运行既有 CI。通过检查不自动证明业务架构已批准。
5. **交付与回滚。** 通过 Draft PR 展示迁移映射、`git diff --summary`、旧新目录一一对应、被变动的引用、独立审查和 CI 证据。由用户人工合并。回退只撤销本 PR 的目录及引用变更，不删除业务数据，不自动合并其他 PR。

## 本次治理与正式架构关系

[早期架构评审 PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 已合并，随后 [完整产品终裁 PR #14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) 也已合并：当时确认调整后的路线 B。后续以[当前架构与实施门禁](designs/current-architecture-baseline.md)为最终架构入口，详细设计、SVG 和选型矩阵归 designs/architecture-final，76 项映射归 requirements，受控证据校验入口归 tasks；旧终裁保留历史，PR #6 的旧版 v2 包仍未合并，不自动转入新开发。正式实施、G、MVP 与真实流量仍必须分别获准和验收。旧 v1 的有效规则及历史证据继续保留。

## 贯穿 W0、MVP 和长期开发的维护动作

1. **任务启动和范围变更。** Codex 必须先从[项目文档索引](index.md)定位已批准架构、代码、任务记录及实际 Git 状态；不要依赖旧包的技术选择。涉及新系统、数据库、能力契约、身份、执行恢复、部署或目录变更时先审查设计和文档影响。
2. **每次阶段性交付。** W0 的最短贯通验收、MVP 的真实用户路径验收、后续阶段完成，以及改变当前架构或运行入口的 PR，都需同步检查根 README、`docs/index.md`、受影响架构/ADR、任务/验收、操作手册和引用。仅更新受影响的文件；不适用时在 PR 说明原因。
3. **可执行验证。** [项目根规则](../AGENTS.md)持续要求文档同步；CI 的 `make check` 固定校验索引和目录治理文件存在及相对链接。实际目录迁移还必须核对运行脚本、Skills、规则发现、其他分支引用及适用验收，不能以文档链接检查代替业务安全验收。
4. **审查和回滚。** Review 时检查代码与当前文档**语义一致性**和历史资料状态（自动检查只能查形式）；报告实际目录重命名、依据提交、任务完成范围、未验证项和回滚路径，由维护者合并。正常小改动如果文档无需变化，可简短声明不适用，不能强制新增无意义文件。

未来其他项目复用的是这些职责和持续更新机制，不必复刻明镜的目录名或 ARM64 合并门禁。
