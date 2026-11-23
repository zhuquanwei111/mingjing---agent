# ADR 0002　采用路线 B，保留可独立验证的旧资产

状态为用户已采纳。日期为 2026-11-23。治理方式继续按 [ADR 0001](0001-versioned-engineering-standard.md) 和[项目工程规范](../engineering-standard.md)执行。

## 决定与证据

明镜 App 的后续智能体代码以 Python、PostgreSQL、Temporal、Pydantic AI 为基础。实验 A 直接利用 P2 的发布、授权和收据，形成动态 Agent 时另行实现图节点、配对和终止逻辑。B 的原生 Agent 完成相同的工具循环，两路均经三种入口调用同一个未知能力。B 的项目责任集中在授权、外部操作核实、共享预算和结果校验。既有投入未计入比较收益。[固定选型报告](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md)

## 后果与改判条件

新代码采用独立目录。P2 v1 对现有调用方的行为、历史操作与旧 Worker 继续由原实现负责。逐项处置详见[旧资产表](../../mingjing-codex-engineering-v2/legacy.md)。首项选择完成条件校验，因为真实模型已经出现工具返回 `invalid-key` 后停止的情况，它可在引入任何外部服务前独立验收。跨组件事务、逐轮恢复、生产负载和真实身份接入需后续实测。若正式链路出现失权后外传、重复提交或关键恢复粒度不足，记录对应版本、失败和修复/替换证据，更新 ADR。首项交付按[开发包](../../mingjing-codex-engineering-v2/README.md)及[本任务](../tasks/route-b-foundation.md)推进。
