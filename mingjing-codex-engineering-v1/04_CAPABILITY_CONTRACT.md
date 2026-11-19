# 04 能力契约与生命周期

## 目标
普通程序、确定性工作流、Agent Loop 和远程服务对外暴露稳定的能力契约。契约统一外部语义，不规定内部技术。

## 建议字段
capability_id、version、display_name、description、input_schema、output_schema、execution_kind、endpoint/adapter_ref、side_effect_class、required_permissions、resource_scope、timeout_policy、retry_policy、idempotency_policy、approval_policy、budget_units、result_schema、artifact_types、validation_ref、lifecycle_status。

## 执行形态
- direct_program：普通程序或业务服务；允许同步或异步。
- durable_workflow：可等待、恢复和取消的确定性编排。
- agent_loop：动态工具决策，受步数、预算、授权范围和深度约束。
- external_service：通过受控适配器接入外部系统。
execution_kind 不是固定业务分类，也不等于每种形态必须对应一个微服务。

## 生命周期
Draft -> Registered -> Validated -> Published -> Deprecated -> Disabled。
注册只代表系统知道能力；发布控制版本和环境；授权控制主体对能力与资源的实际访问。Disabled 不自动撤销已发生的副作用。正在运行的任务需要显式版本与撤权策略。

## 发现
先根据租户、当前主体、可用版本和环境进行硬过滤，再按语义或标签检索。最终执行前必须重新核权。向模型只提供被允许且与任务相关的候选工具，不把全量目录放进提示词。

## 输入输出
输入、输出与错误采用可版本化 JSON Schema。长任务返回 task/run 引用；大文件返回受权限保护的 artifact_id，不把二进制内容塞入模型上下文或 Workflow History。

## SDK
提供统一的 CapabilityContext 和执行入口，业务实现不必知道 Temporal/LangGraph 细节。SDK 至少包含类型验证、权限上下文、幂等键、预算调用、追踪关联和错误映射。禁止将仅有用户/租户 ID 的未签名数据当作授权凭据。

## 兼容策略
契约变更必须说明向后兼容性；长任务固定能力版本；旧任务迁移或旧 Worker 保留策略须可验证。开发者模板包含三种不同实现形态和契约测试。
