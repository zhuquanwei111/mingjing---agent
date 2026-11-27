# 明镜业务智能体工程

本仓库维护明镜现行架构、工程规范和历史回归资产。

## 当前项目状态

**项目方已采纳 R3 最终裁决，选定 DeerFlow 作为明镜智能体主体。** DeerFlow 是唯一主体应用工程底座，优先承载 Agent、工作流、异步任务与调度。普通程序可直接查询开播时间；直播表现分析由 Agent 处理。架构、正式需求及实施边界见[现行架构](docs/designs/current-architecture-baseline.md)、[需求修订](docs/requirements/current-engineering-requirements.md)、[架构图与契约](docs/designs/architecture-final/contracts.md)及 [ADR 0003](docs/adr/0003-deerflow-architecture-transition.md)。v2.2.0 是研究参考版；实际制品在 H 确认。W0 另行批准。全部必要公共能力和独立 AC-17 在 G 签收后，才可另批首个正式业务 M。

早期 P1 隔离验证与 P2 公共层已归入[历史代码与证据](docs/archive/legacy-runtime/README.md)。两套实现仍供 CI 复跑；正式公共宿主的建设状态以[基线任务](docs/tasks/architecture-baseline-transition.md)为准。

## 用 Codex 开发

在 Codex 图形界面选择仓库根目录，从 [AGENTS.md](AGENTS.md) 进入。
用户通过对话交代目标和查看结果；以下命令由 Agent 执行，用户仍可自愿用终端复核。
项目级权限默认使用 `workspace-write` 和 `on-request`；需信任项目后加载，
不替换个人模型、供应商和认证配置。

[开发流程](docs/development.md)包含验证、审查和 Git 交付；
[计划与接续](docs/PLANS.md)说明完成信号、换会话和恢复方法。
[Codex 通用规范与明镜接入](docs/engineering-standard.md)提供独立评审、复用、文档治理和验证入口。
Agent 可用 `python3 scripts/check_development_docs.py --status --task docs/tasks/codex-development-configuration.md`
读取实际 Git 状态、定位本次任务并检查开发入口引用。它不连接服务或修改工作区。

```bash
make check       # 实际检查范围见 Makefile，包含开发入口引用检查
make smoke       # 已准备好的 macOS ARM64 环境冒烟
make acceptance  # 专用 Linux ARM64/x86_64 Docker 环境：全量 P1 + 恢复与重建
make p2-acceptance  # 专用 Linux ARM64/x86_64 Docker 环境：P2 公共层
```

`P1 acceptance` 保留已有必需检查名称，正式 ARM64 作业执行 P1 和 P2 验收；
x86_64 作业只提供辅助反馈。是否已经通过，须查看候选提交的实际运行，不能由
工作流配置推定。服务器合并保护以[当前生效规则](https://github.com/zhuquanwei111/mingjing---agent/rules/27699996)
为准；[仓库规则 JSON](.github/rulesets/main.json)用于复现配置，提交文件本身不启用保护。
保留人工合并，不要求单人项目再找另一位审批人。

优先复用现有 Instabox 做服务联调与故障复现，Daytona 做隔离开发和实验；
Daytona 跑完整验收前需确认其当前 Docker/Compose 能力。
[环境分工](docs/development.md#现有环境怎么使用)与本地、CI 使用同一套命令。

## 项目资料

- [统一文档索引（现行架构、W0/MVP 和历史资料）](docs/index.md)
- [目录结构与持续文档治理规则](docs/repository-layout.md)
- [当前架构与实施门禁](docs/designs/current-architecture-baseline.md) · [历史 PR #14 终裁](docs/archive/route-b/designs/whole-product-decision.md)

- [历史 v1 开发包（有效的工程规则仍需保留）](docs/archive/engineering-v1/README.md)
- [P1 运行与复现说明](docs/archive/legacy-runtime/p1-walking-skeleton/README.md)
- [P2 接口与操作手册](docs/archive/legacy-runtime/core/README.md)
- [开发流程的来源与适配说明](docs/development.md#采用依据与核验版本)
