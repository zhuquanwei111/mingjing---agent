# 02 架构与组件职责

## 当前优先验证组合
Temporal OSS：持久 Workflow/Activity、定时器、重试、Signal/Update、历史与恢复。
LangGraph OSS：Agent 内部动态决策与状态图。
temporalio-langgraph：官方集成候选；逐节点明确 workflow/activity 执行位置，兼容性须实测。
明镜产品服务：统一 API、任务映射、能力目录、权限与预算入口、产物引用和业务审计。
PostgreSQL：产品任务元数据、契约、幂等收据、预算、产物元数据。Temporal 的数据库应逻辑隔离。
OTel：可移植遥测；不得充当业务审计权威。

## 核心数据流
App/API/事件
  -> 明镜可信入口（身份、能力版本、授权、预算）
  -> 简单确定性能力：直接进入可信业务执行边界
  -> 需等待/编排的能力：Temporal Workflow
      -> 普通 Activity
      -> 固定子 Workflow
      -> LangGraph Agent 节点/任务
  -> 真实 I/O 前重新鉴权与预算控制
  -> 业务收据、用量、产物引用
  -> 明镜 Task/Run 状态映射与结果交付

## 状态权威
- Temporal History：执行历史与恢复权威。
- LangGraph 插件模式：图内状态依官方要求使用 InMemorySaver；不再叠加独立持久 checkpointer，除非测试证据证明必要。
- 明镜 Task/Run：产品状态、业务身份、任务与执行映射。
- 业务收据：副作用是否已发生、实际结果、未知状态和补偿进度。
- 产物元数据：产物版本、归属、权限和生命周期。
- Trace：诊断数据，不是上述任何权威记录。

## 跨组件约束
1. 不能在 Temporal Workflow 的确定性代码里直接做外部网络 I/O。
2. Agent 工具必须经过可信执行适配器，不能绕过权限与预算。
3. 所有外部写操作必须有稳定 operation_id 和明确的重试语义。
4. Signal/Update 的审批消息不能代替审批人身份校验；恢复后执行前再核权。
5. 取消与预算耗尽必须传递到子执行，但已发生的动作按事实报告。
6. Agent 图、能力、Workflow、模型和知识版本需要可追溯。
7. 外部黑盒 Agent 若无法控制其工具调用和副作用，不得直接承担敏感写入。

## 备选条件
官方插件无法满足恢复、授权或维护要求时，优先研究 Temporal + Pydantic AI 的同职责替代；如果 Temporal 运维不适合，再重新比较 Dapr + Dapr Agents。不能仅因业务幂等实现错误就更换引擎。
