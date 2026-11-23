# 交给 Codex 的第一条指令

> 此启动词仅用于复现旧 P0 阶段。当前开发从[仓库根规则](../AGENTS.md)和[新开发包](../mingjing-codex-engineering-v2/README.md)进入。以下为历史原文。

你正在一个全新的 Mingjing 仓库中工作。请首先完整阅读 AGENTS.md 和 README.md，再阅读 01—09 的工程文档。

本次只执行 P0，并准备 P1 的隔离验证计划；不要直接建设完整平台。

具体任务：

1. 检查当前仓库与可用工具，确认没有旧业务代码。
2. 核实 Temporal Server OSS、Temporal Python SDK、LangGraph OSS、temporalio-langgraph 的固定版本、许可证、官方示例、依赖兼容范围和安全公告。
3. 列出最小可运行依赖及运行方式，区分开发环境与生产部署。
4. 提出 P1 Walking Skeleton 的目录结构、测试命令、故障注入方法和所需环境变量。
5. 明确哪些能力是现成复用、哪些是适配、哪些必须写明镜代码；不得照搬调研中的不安全示例。
6. 生成 P0_REPORT.md、DEPENDENCY_LOCK.md（候选版）、RISK_REGISTER.md、P1_EXECUTION_PLAN.md。
7. 遇到版本、许可或关键恢复语义冲突，提供证据与可选方案，停止自动进入 P1。

完成 P0 后报告结果并等待我确认。未经批准不要执行付费模型请求、生产部署、真实数据迁移或 P2/P3 开发。

