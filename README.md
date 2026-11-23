# 明镜业务智能体工程

明镜是 App 内面向组织授权用户的智能体应用。新开发采用 Python、PostgreSQL、Temporal 和 Pydantic AI。

## 当前项目状态

新任务从[路线 B 开发包](mingjing-codex-engineering-v2/README.md)进入。[选型 ADR](docs/adr/0002-route-b-foundation.md)记录技术决定，[切换任务账](docs/tasks/route-b-foundation.md)记录当前开发与验收状态。旧包和已交付代码按[旧资产表](mingjing-codex-engineering-v2/legacy.md)维护。

历史 P2 最小公共层已由 [PR #2](https://github.com/zhuquanwei111/mingjing---agent/pull/2)
合并交付，其兼容维护与操作入口在 [core/README.md](core/README.md)。
后续新阶段交付时同步更新本入口。新任务先核对实际分支、HEAD 和该提交的检查结果，
不要把这里的阶段记录或旧日志当作当前候选已经通过的证明。

- [P1 验收报告](p1-walking-skeleton/P1_REPORT.md)保留隔离验证和未放行事项。
- [P2 早期验收记录](core/P2_REPORT.md)明确对应历史提交 `7d4df4f`，其中 11 项测试不是当前版本的验收结论。
- 当前改动的验证以同一候选提交的 PR、CI 作业和完整日志为准；生产制品等未放行事项继续适用。
- 正在推进的[完整 Codex 配置任务](docs/tasks/codex-development-configuration.md)记录 C01–C09，阶段交付不等于全部完成。

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

- [新开发包](mingjing-codex-engineering-v2/README.md) · [旧工程包](mingjing-codex-engineering-v1/README.md)
- [P1 运行与复现说明](p1-walking-skeleton/README.md)
- [P2 接口与操作手册](core/README.md)
- [开发流程的来源与适配说明](docs/development.md#采用依据与核验版本)
