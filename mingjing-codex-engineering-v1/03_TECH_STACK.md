# 03 技术栈、版本与引入门槛

以下版本来自 2026-11-19 调研，是只读核验锚点，不是经过联调的生产锁定。

## 核心候选
- Temporal Server OSS v1.32.2（MIT）：https://github.com/temporalio/temporal
- Temporal Python SDK 1.36.1：https://github.com/temporalio/sdk-python
- LangGraph Python 1.2.22（MIT）：https://github.com/langchain-ai/langgraph
- temporalio-langgraph 1.0.0（官方插件候选）：https://github.com/temporalio/ai-integrations
- Python 3.12（验证候选环境；核对全部包实际兼容范围）
- PostgreSQL：优先使用已有受支持版本；未确认前不锁定具体生产版本。

## 首期优先复用
- OpenTelemetry Python SDK：跨服务观测。
- Promptfoo CLI：隔离样本自动回归；按许可、依赖和数据出口核验。
- PostgreSQL 事务、唯一约束和行锁：幂等收据与预算预留。
- 对象存储：先查可取得性、维护状态、S3 兼容性及已有基础设施，暂不锁定厂商。

## 条件候选，不预装
- SpiceDB：复杂对象关系授权；先比较现有身份和权限需求，核验授权 Schema。
- OpenFeature / Unleash：发布灰度需要独立规则服务时。
- LiteLLM Proxy：跨模型/跨服务统一路由和密钥治理需要时，独立进程部署并核实许可。
- Langfuse：现有 OTel/观测方案不足以支持 AI 实验与追踪时。
- OpenMeter：多资源统计与商业计费复杂度达到阈值时。
- Docling + pgvector：出现实际文档检索需求并通过授权与出处验证时。
- SeaweedFS / RustFS：无合适现成对象存储时再比较。
- gVisor / E2B：确需执行不可信代码且部署环境支持时。

## 明确避免
- 不同时引入 Temporal 与 Dapr Workflow 作顶层任务引擎。
- 不把 LangGraph 官方 Agent Server 许可等同于 MIT 库许可。
- 不将 Dify 的商业限制或 Enterprise 能力混同为社区版能力。
- 不把 Temporal 自动重试等同于业务幂等。
- 不按调研中的未经验证的代码行数估算立项。
- 不因为新版本号更高就直接替换测试基线。

## 版本锁定流程
读取固定 Tag 的依赖声明、许可证、官方示例和安全公告；记录镜像摘要；生成锁文件；实际执行官方集成样例、恢复、序列化、取消、升级和重放测试；通过后形成 DEPENDENCY_LOCK.md。
