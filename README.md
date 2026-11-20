# 明镜业务智能体工程

本仓库保存工程方案、P1 隔离验证和 P2 最小公共层。阶段结论和待放行事项见
[P1 验收报告](p1-walking-skeleton/P1_REPORT.md)与 [P2 验收记录](p2-core/P2_REPORT.md)。

## 用 Codex 开发

在仓库根目录打开 Codex，从 [AGENTS.md](AGENTS.md) 进入。
项目级权限默认使用 `workspace-write` 和 `on-request`；需信任项目后加载，
不替换个人模型、供应商和认证配置。

[开发流程](docs/development.md) 包含验证命令、独立审查、Git 交付和任务接续。

```bash
make check       # Python / Shell 语法及代码空白检查
make smoke       # 已准备好的 macOS ARM64 环境冒烟
make acceptance  # 专用 Linux ARM64/x86_64 Docker 环境：全量 P1 + 恢复与重建
make p2-acceptance  # 专用 Linux x86_64 Docker 环境：P2 公共层
```

`P1 acceptance` 是 GitHub Actions 上的正式 ARM64 检查；x86_64 单独提供辅助
回归反馈，不是合并必需项。服务端合并保护需由仓库管理员
导入并启用 [.github/rulesets/main.json](.github/rulesets/main.json)；提交此 JSON
本身不会启用保护。规则要求 PR 和检查通过，保留人工合并，不要求单人项目
再找另一位审批人。启用状态以 GitHub Settings → Rules → Rulesets 为准。

优先复用现有 Instabox 做服务联调与故障复现，Daytona 做隔离开发和实验；
Daytona 跑完整验收前需确认其当前 Docker/Compose 能力。
[环境分工](docs/development.md#现有环境怎么使用)与本地、CI 使用同一套命令。

## 项目资料

- [方案入口](mingjing-codex-engineering-v1/README.md)
- [P1 运行与复现说明](p1-walking-skeleton/README.md)
- [P2 接口与操作手册](p2-core/README.md)
- [开发流程的来源与适配说明](docs/development.md#采用依据与核验版本)
