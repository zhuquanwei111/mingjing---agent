# Codex 开发与交付流程

以下命令从仓库根目录执行。先读根目录 `AGENTS.md`；原有[工程原则、阶段门禁与安全要求](archive/engineering-v1/AGENTS.md)继续生效。本页把已有项目检查、Codex 独立审查和 GitHub 交付串起来，不增加自研调度器或 review-loop 脚本。

通用生命周期、独立方案评审与接入证据见[明镜工程规范](engineering-standard.md)。

## 一个任务做到哪里才结束

1. **确定范围。** 查看 `git status -sb`，从 [当前项目状态](../README.md#当前项目状态)定位实现和历史证据，再读取相关代码、测试和项目文档。保留用户和其他 Agent 的未提交改动。沿用本任务已经给出的授权，不把每次测试、修复、提交或已授权的 push/PR 重新变成确认问题。
2. **实现并验证。** 对运行行为、API、配置或持久状态的修改，先在现有记录中用简短说明写清必需行为、兼容边界、不支持范围及现有替代路径。先复现问题，再做范围清楚的修改，运行下表中适用的检查。行为改变同步更新文档；失败先修复，环境阻断则记录准确原因，不写“已通过”。
3. **独立审查并处理结果。** 按下一节启动独立 reviewer。原执行 Agent 读取结果、核实发现、修复成立的问题并重新验证；不能用自己的总结代替 reviewer 的完成结果。修复改变了候选代码后，对新候选再次审查；拒绝不成立的发现时写明依据。
4. **提交自己的修改。** 按明确文件路径暂存，检查暂存 diff，再做范围单一的 commit。不要 `git add .` 或混入其他任务。提交/PR 说明原因、行为变化、实际验证、未验证项及回滚方法。
5. **完成已授权的交付。** 用户已授权 push/PR 时，继续推送任务分支、创建或更新 PR、读取对应 head 的 CI 结果与评审意见并修复，直到可交付或遇到真实阻断。没有这项授权时停在本地交付结果。**不自动 merge、不直接向受保护的 `main` 推送。**

### 任务结束、阶段结束与会话接续

同一连贯目标继续在主会话推进。任务目标、适用检查和已授权交付完成后，Agent 明确说明“本任务完成”，给出结果与证据，并区分不属于本次范围的后续工作；复杂总任务的一个阶段完成时，仍须继续其已授权的剩余事项。真实阻断则说明缺少的决定或条件、已完成工作及恢复动作。

新的独立目标适合新会话；当前目标尚未完成而需要切换环境或会话时，先按 [docs/PLANS.md](PLANS.md) 更新已有任务记录，给出一段可直接使用的接续说明。压缩、固定 token 比例或连续两次失败本身不是换会话条件。发现重复走已排除路线时，先对照代码和记录纠偏，再判断是否需要换会话。

新会话读取根规则和指定任务记录，核对当前分支、HEAD、未提交修改及验证归属，再继续已有授权。记录中的旧基线不能覆盖当前工作区事实。本次完整配置沿用 [已有总账](tasks/codex-development-configuration.md)，不新建第二份总计划。这里没有自动创建或唤醒会话的后台服务，恢复是否成功需用真实接续结果验证。

### 开发入口与记录检查

`python3 scripts/check_development_docs.py` 检查开发入口和任务记录中的常规行内相对文件链接；缺失入口或目标会返回失败。`--status --task docs/tasks/<task>.md` 另外显示只读 Git 状态及任务入口，供 Agent 开始或恢复任务时使用。它不检查网页可用性、Markdown 锚点或引用式链接、文字真实性、授权或会话理解，也不会把文件存在等同于任务完成。修改行为、目录或验收入口时，同步核对指向它们的开发文档。


## 共用的验证入口

| 命令 | 实际验证范围 | 前置条件 |
| --- | --- | --- |
| `make check` | Python/Shell 语法、代码空白、核心静态依赖边界及其用例、开发入口和任务记录的行内相对文件链接；不等于类型、业务或完整安全验收 | Python 3.10+、Git、sh/bash；服务运行仍用锁定的 Python 3.12 |
| `make smoke` | 现有 macOS Temporal CLI 冒烟脚本 | 按 [P1 README](../p1-walking-skeleton/README.md)准备 `p1-walking-skeleton/.venv` 和已校验的 `.p1/bin/temporal` |
| `make acceptance` | 既有全验收、备份恢复、Temporal 重启、独立重建；失败即停 | 隔离的 Linux ARM64 或 x86_64 环境与 Docker Compose |
| `make p2-acceptance` | P2 迁移和公共层测试，包含真实 PostgreSQL、Temporal 及 LangGraph | 独立 Linux ARM64/x86_64 checkout 与 Docker Compose |

GitHub CI 的 **`P1 acceptance`** 保留既有 required check 名称，在官方 Linux ARM64 runner 上执行 P1 全验收及 P2 公共层验收。任一步失败都不能把该必需检查报为通过。服务器规则需实际启用，不能仅由仓库 JSON 推定；结果以当前候选提交的实际运行与生效规则为准。

x86_64 的 P1 与 P2 检查独立提供辅助反馈，不设为合并必需项，也不代替 ARM64 结果。两个架构分别使用各自的依赖锁，复用对应层的验收入口；P2 测试在独立 Compose project 中执行并清理本次合成卷及凭据。新增当前代码层或改变正式目标时，同步核对工作流、测试范围和服务器 required check，不能让旧层通过代替新层验收。

验收与重建包含其原有 smoke 测试，但这不等于验证了 Darwin CLI。只改文档时不为凑本地流程启动整套服务；必需 CI 仍运行，避免缺少检查结果而无法合并。修改运行时、基础设施、依赖或验收逻辑时，按影响运行相应验证。历史 `evidence/` 不能作为新提交已通过的证明；保留本次日志、测试结果及对应 commit。PR 明确贴出本次 head 对应的 CI run 链接，并能打开 ARM64 job 的完整日志；独立代码审查和截图不能替代这份运行证据。上传证据只选本次 `.p1/results/` 和验证摘要，不打包含运行凭据、数据库备份的整个 `.p1/`。

## 现有环境怎么使用

| 环境 | 本项目的用途 | 执行方式与已知边界 |
| --- | --- | --- |
| Mac mini | Codex 主会话、查看修改和本地冒烟 | 使用项目配置；`make check`，已准备环境时 `make smoke`。不要求把 PostgreSQL/Temporal 常驻在 Mac 上 |
| 已有 Instabox | 服务联调、辅助 P1 回归和失败复现 | 历史 `mj-agent` 为 Linux x86_64、4 vCPU/8 GiB、Docker/Compose，已有 16 项用例记录；在专用 checkout 运行 `make acceptance`，新提交须重新验证；不代替 ARM64 合并门禁 |
| 已有 Daytona 沙盒 | 隔离开发、试验性修改、独立复现 | 先核实当前沙盒；`make check` 不需要 Docker。完整验收还需可用的 Docker daemon、Compose、兼容架构及拉取固定镜像/锁定依赖的网络 |
| GitHub Actions | 每个 PR 的统一合并前检查 | 正式 ARM64 `P1 acceptance` 覆盖 P1 与 P2，x86_64 独立辅助；以实际启用规则和候选提交结果约束合并 |

Instabox 的既有证据及平台限制见 [Instabox 验收记录](../p1-walking-skeleton/evidence/instabox/README.md)。`requirements/linux-x86_64.lock` 原样复用该次 amd64 锁；Docker 构建按目标架构选择它或原有的 `linux-aarch64.lock`，无需临时改 Dockerfile。两个锁保持原先各平台的精确版本和 wheel 哈希。

首次在云端 checkout 运行前，先作只读能力确认：

```bash
git status -sb
uname -srm
python3 --version
sudo -n docker info --format '{{.OSType}}/{{.Architecture}}'
docker compose version
make check
```

当前验收脚本含 `sudo docker cp/rm`，因此还需 `sudo` 可用并允许非交互执行相应 Docker 操作。上述能力检查失败时保留真实报错，不能据此宣称该沙盒已具备完整验收条件。

Daytona 官方提供沙盒内运行 Docker 的方案，但镜像需包含 Docker Engine，且 daemon 已就绪；只有 Docker CLI 不够。见 [v2 Docker 文档](https://www.daytona.com/docs/docker) 与 [v0 snapshots 文档](https://www.daytona.io/docs/en/snapshots/#run-docker-in-a-sandbox)。不能由“已有 Daytona 沙盒”推定当前实例已具备这些能力。两版的持久化默认值也不同，必须核实用户当前版本、沙盒类型和生命周期设置；见 [v2 持久化](https://www.daytona.com/docs/persistence) 与 [v0 持久化](https://www.daytona.io/docs/en/persistence/)。源码和任务进度仍同步到 Git，不以沙盒存活替代交付。

每个并行任务使用独立 checkout；`make acceptance` 为本次运行创建独立 Compose project，并在成功或失败后清理该 project。不要在另一个任务已有 `.p1/runtime.env` 的目录中接管运行，也不要使用全局 `docker prune`。先复用现有机器和沙盒，不新增常驻服务器、供应商密钥或编排平台。这里的能力要求和历史证据不表示已连接、已配置或已在用户当前两台环境上运行本次提交。

## 独立审查：现成工具，结果回到原 Agent

### 立即可用：原生 Codex review

先查看 `codex --version`、`codex review --help`。从下面选择与当前候选一致的一条，由实施任务的 Agent 调用并等待完整结果：

```bash
# 未提交的候选改动
codex review --uncommitted

# 单个已提交的候选
codex review --commit HEAD

# 整个任务分支相对已同步基准的改动
codex review --base origin/main
```

这三项与自定义 `PROMPT` 互斥；不要写成 `codex review --uncommitted "检查……"`，也不要同时传多个目标。基准必须是本任务实际使用且已经同步的基准；不要拿陈旧的 `origin/main` 作为最新结果。独立命令的输出直接进入原 Agent 的工具结果，无需用户搬运。命令结束不等于没有发现，必须读完审查结论。

### 可选：Peter 正在使用的 autoreview

已有安装先复用。首次安装时，将固定源码保留在本项目之外，**只安装 autoreview 这一个 skill**：

```bash
mkdir -p "$HOME/.local/share"
git clone https://github.com/openclaw/agent-skills.git "$HOME/.local/share/mingjing-agent-skills"
git -C "$HOME/.local/share/mingjing-agent-skills" checkout --detach 0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341
python3 "$HOME/.local/share/mingjing-agent-skills/scripts/install-skills" autoreview
```

目标或源码目录已存在时先检查并复用，不用 `--force` 覆盖。安装器默认创建 `~/.agents/skills/autoreview` 软链接；不安装 OpenClaw、不复制 Peter 的根 `AGENTS.MD`、不注册 Git hook。不要省略最后的 `autoreview`，否则安装器会选择全部 skills。

安装后先读已安装的 `SKILL.md`。保持当前目录为本项目，再做兼容性预检和审查：

```bash
python3 "$HOME/.agents/skills/autoreview/scripts/autoreview" --help
python3 "$HOME/.agents/skills/autoreview/scripts/autoreview" \
  --mode local --engine codex --max-priority P2 --dry-run
python3 "$HOME/.agents/skills/autoreview/scripts/autoreview" \
  --mode local --engine codex --max-priority P2
```

用户已有 Codex `0.167` 时，先检查实际兼容性，不无条件升级或改全局配置。上游有 CLI `0.169.0` 的验证记录，**不是声明最低版本为 0.169.0**。`--dry-run` 只检查准备与本地启动条件，不证明账号模型权限或真实审查成功。当前 CLI 不兼容或工具未安装时，使用上面的原生 review；原生也不可用则报告审查阻断，不把失败改称通过。

本项目明确选 `--engine codex`：helper 会启动隔离、临时的 Codex reviewer，收集结构化报告并返回原 Agent；不需要 OpenClaw 运行时，也不加载 OpenClaw 项目业务规则。默认用现有 ChatGPT 订阅认证；不为此购买 API 或另加密钥。审查需要未修改文件的上下文时，按原版 skill 提供 `--prompt-file`/`--dataset` 等证据，不解除隔离。`P2` 扩大到一般开发缺陷；原版默认只有 P0。

| autoreview 结果 | 原执行 Agent 的动作 |
| --- | --- |
| `scoped-clean` | 仅说明选定范围与优先级无可行动发现，继续适用的交付检查 |
| `findings` / `incorrect` | 核实并修复成立的问题，验证新候选后复审 |
| `filtered` | 阅读被过滤的发现，不能称为完整正确性证明 |
| `incomplete` / `reviewer_unavailable` / 无有效报告 | 报告未完成及阻断，不能提交“已通过审查”的结论 |

退出码 `0` 也可能是 `filtered`；`1` 可能是发现问题或执行失败；`2` 表示不完整。始终同时读报告状态。helper 只做审查，不替实施 Agent 修复、commit 或 push。等待中的一次审查要等其结果，不能反复启动新审查刷出更好结论。

## 哪些能强制执行

`make`/CI 能以非零退出码报告其覆盖检查的失败。**GitHub 只有实际启用并验证了保护规则，将相应 CI 设为 required check，才会阻止不符合条件的合并或直接推送。**工作流 YAML、PR 模板和本页文字本身不会开启服务器保护；以 GitHub 当前生效规则和精确 head 的检查结果为准。

自动维护进度、选择独立 reviewer、处理发现、按范围 commit 和授权后继续 push/PR，仍是 Agent 的行为约定。原版 autoreview 安装器没有把“每次 commit 必须先审查”变成不可绕过的 hook；不能把 Agent 自述、CI 通过或合并保护说成完整独立评审的替代品。CI 绿灯不解除 P1 报告中的剩余安全放行事项或 P2 阶段门禁；生产发布仍需对应授权。

## 采用依据与核验版本

- **OpenAI Agents SDK 团队：**Kazuhiro Sera，2026-03-09，[团队实际如何使用 skills](https://developers.openai.com/blog/skills-agents-sdk)。核验 `openai/openai-agents-python` 的固定提交 [`91fb508a8931016efa793b033147d08cd20308cf`](https://github.com/openai/openai-agents-python/tree/91fb508a8931016efa793b033147d08cd20308cf)：[`AGENTS.md`](https://github.com/openai/openai-agents-python/blob/91fb508a8931016efa793b033147d08cd20308cf/AGENTS.md)、[`code-change-verification`](https://github.com/openai/openai-agents-python/blob/91fb508a8931016efa793b033147d08cd20308cf/.agents/skills/code-change-verification/SKILL.md)、其 [`run.sh`](https://github.com/openai/openai-agents-python/blob/91fb508a8931016efa793b033147d08cd20308cf/.agents/skills/code-change-verification/scripts/run.sh)、[`Makefile`](https://github.com/openai/openai-agents-python/blob/91fb508a8931016efa793b033147d08cd20308cf/Makefile) 和 [`tests.yml`](https://github.com/openai/openai-agents-python/blob/91fb508a8931016efa793b033147d08cd20308cf/.github/workflows/tests.yml)。本项目采用“可发现的规则、共用检查入口、CI 运行同一检查”的机制，没有复制 SDK 专用检查，也不声称本项目经过 OpenAI 验证。
- **Peter Steinberger 的实际审查流程：**个人 [`AGENTS.MD`](https://github.com/steipete/agent-scripts/blob/2f82700ba9f3e7e93d3583e1990992584561eadc/AGENTS.MD) 固定提交 `2f82700ba9f3e7e93d3583e1990992584561eadc`；本人 [PR #44](https://github.com/steipete/agent-scripts/pull/44)（2026-09-22）记录独立 P2 autoreview；本人 [PR #392](https://github.com/openclaw/agent-skills/pull/392)（2026-11-14）记录检查与 P0–P2 审查，并使用 Codex CLI 0.169.0。这是作者运行记录，不是本项目已运行结果。
- **原版 autoreview：**固定提交 [`0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341`](https://github.com/openclaw/agent-skills/tree/0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341)，对应 [`SKILL.md`](https://github.com/openclaw/agent-skills/blob/0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341/skills/autoreview/SKILL.md)、[`helper`](https://github.com/openclaw/agent-skills/blob/0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341/skills/autoreview/scripts/autoreview)、[`安装器`](https://github.com/openclaw/agent-skills/blob/0a5ba4b3c79ed4643c2b5f0b62af17d3cb4c8341/scripts/install-skills)。本仓库不复制、修改或另写 review-loop 实现。
- **原生命令：**[Codex CLI 官方参考](https://developers.openai.com/codex/cli/reference/)，使用目标机器的 `codex review --help` 核对具体版本参数。
