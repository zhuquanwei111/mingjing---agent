# 明镜 Mingjing — Codex 工程交付包 v1.0

> 历史交付包。下列“当前决策”记录 v1 当时的候选。新开发使用[路线 B 开发包](../mingjing-codex-engineering-v2/README.md)，旧资产的维护方式见[处置表](../mingjing-codex-engineering-v2/legacy.md)。

日期：2026-11-19
工程类型：全新仓库，代码优先，分阶段验证。

## 目标
构建业务无关、可持续扩展的智能体平台。新的能力可由普通程序、确定性工作流、Agent Loop 或外部服务实现，通过统一契约被 App/API、工作流与 Agent 调用。执行授权由可信代码控制，不能由提示词代替。

## 当前决策
首要验证组合：Temporal OSS + LangGraph OSS + 官方 temporalio-langgraph 集成。此组合尚未通过本项目实测，不等于最终生产定版。
复用 PostgreSQL 承担必要产品元数据、幂等收据和预算事务；使用 OpenTelemetry 观测，Promptfoo 作为候选 CI 评测工具。对象存储选择前须核实实际部署环境。SpiceDB、LiteLLM Proxy、Langfuse、OpenMeter、Docling/pgvector、gVisor 等均为条件候选，不预装全部。

## 文件阅读顺序
1. AGENTS.md — Codex 必须遵守的工程规则
2. 01_PROJECT_BRIEF.md — 目标与边界
3. 02_ARCHITECTURE.md — 组件职责与数据流
4. 03_TECH_STACK.md — 版本与组件决策
5. 04_CAPABILITY_CONTRACT.md — 能力协议
6. 05_SECURITY_AND_RELIABILITY.md — 安全与可靠性
7. 06_DATA_AND_ARTIFACTS.md — 数据和产物
8. 07_IMPLEMENTATION_PLAN.md — 实施阶段
9. 08_ACCEPTANCE_TESTS.md — 验收与故障注入
10. 09_OPEN_QUESTIONS.md — 风险与待核验
11. CODEX_START_PROMPT.md — 可直接提交给 Codex 的第一条指令

## 工程交付纪律
先研究仓库与依赖，再建立可丢弃验证工程，验证通过后才建设最小公共层。未经批准不得部署生产、购买服务、导入真实敏感数据或宣布生产就绪。
