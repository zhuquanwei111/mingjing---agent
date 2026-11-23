# Codex 通用工程开发规范与验证体系

**版本 1.0.0-rc.1。** 这套规范用于把需求、技术决策、实现、验证和人工交付串在一个可接续的任务里。版本与来源提交一起固定。[版本变更](CHANGELOG.md)记录升级影响，[采用依据](sources.md)区分公开实务、规范性建议和本体系的设计。

| 层次 | 内容 | 维护方式 |
| --- | --- | --- |
| 通用标准 | [工作流](workflow.md)、[代码质量与交付](quality.md)、[权限、文档与运维](operations.md)、模板和[任务接续技能](skills/engineering-handoff/SKILL.md) | 当跨任务反复出现同类问题时更新，以真实任务复验 |
| 技术适配 | [Python、Make 与 GitHub Actions](adapters/python-github.md)、[原生子代理模板](agents/solution-reviewer.toml)、[CLI 备用方案关卡](adapters/codex-cli/README.md) | 依据项目已有技术栈采用，记录命令、支持平台和实现证据 |
| 项目实例 | 根 `AGENTS.md`、项目文档、真实命令与行为验收 | 由采用仓库维护，业务约束、环境和实验证据留在该仓库的项目层 |

## 接入已有项目

1. 先核对真实分支、未完成工作、现行规则、运行入口与所需权限。把本目录按来源 Git 提交复制到目标仓库的 `engineering-standard/`，记录版本和提交。采用者先阅读、评审，再在目标仓库提交接入。
2. 从 [AGENTS 模板](templates/agents.md)选用必要条款，合并进目标项目的现有入口。先接入已有命令和文档。已有清晰的计划、ADR、PR 或配置格式可以沿用。
3. 明确项目采用的测试入口、合并规则、目标平台、敏感操作边界及证据位置。需要这些载体时使用[任务记录](templates/task.md)、[ADR](templates/adr.md)、[独立评审](templates/review.md)、[PR](templates/pull-request.md)和[项目授权默认值示例](templates/codex-config.toml)。
4. 需复用接续方式时，在支持符号链接的 checkout 安装仓库技能。以下命令从目标 Git 根目录执行，先检查同名入口，由已有入口迁移时保留其内容和历史。

   ```sh
   mkdir -p .agents/skills
   ln -s ../../engineering-standard/skills/engineering-handoff .agents/skills/engineering-handoff
   ```

   也可把技能目录按同一版本复制到 `.agents/skills/engineering-handoff/`。每次升级一起更新；同一项目只保留一个可发现的定义。由实际 Codex 客户端确认发现并运行一次冷恢复。
5. 需要方案评审时，将 [原生子代理角色](agents/solution-reviewer.toml)安装到 `.codex/agents/solution-reviewer.toml`，并由主 Agent 按[评审模板](templates/review.md)显式发起。**安装角色文件不会自动触发评审。** 子代理不可用时沿用现有 CLI 关卡或人工新会话。
6. 用一个已有的真实任务验证需求、命令、独立审查回流和交付。检查本地文档导航与复制后的完整性。记录遗漏、失败和不适用情形，以及项目实例层应调整的内容。

从桌面主会话发起任务后，由 Agent 执行已授权的步骤并回报证据。终端可用于独立审查、可重复检查和人工复核。升级时比较来源版本及目标项目的本地规则，修改接入链接和受影响检查，用一个真实任务验证。需要回退时，在任务分支撤销接入的 Git 变更，重新核对现行门禁。
