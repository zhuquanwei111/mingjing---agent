# 06 数据模型与产物管理

## 数据权威
- 产品 Task/Run：明镜数据库。
- 持久执行历史：Temporal。
- Agent 图内快照：按官方插件模式处理，不能代替执行历史。
- 业务事实：原业务系统。
- 业务副作用收据：业务写入的权威记录。
- 知识索引：可重建的派生数据。
- 产物：对象存储字节与明镜元数据表共同管理。
- 遥测：诊断数据，不能替代业务事实和收据。

## 建议最小实体
Task：task_id、tenant_id、initiator、capability_id/version、business_status、created_at。
Run：run_id、task_id、workflow_id、temporal_run_id、started_at、ended_at、outcome。
OperationReceipt：tenant_id、operation_id、payload_hash、state、result_ref、external_ref、recovery_point、updated_at。
BudgetReservation：reservation_id、task_id、resource_kind、reserved_amount、settled_amount、state。
UsageAttempt：attempt_id、operation_id、provider_request_id、usage_units、price_version、actual_or_estimated。
Artifact：artifact_id、task_id、tenant_id、storage_ref、content_hash、media_type、version、visibility、retention_policy。
Approval：approval_id、task_id、resource_ref、action、params_hash、decision、approver、expires_at。
CapabilityVersion：capability_id、version、contract、status、implementation_ref。

这些是设计候选，Codex 须在 P1 验证后提交迁移设计，不应照抄为未经审查的最终数据库表。

## 产物
- 对外返回 artifact_id 与受控访问接口，内部存储 URI 不等于公开下载权限。
- 大文件不进入 Temporal History 或模型上下文。
- 每次访问按当前身份和对象权限核验；预签名 URL 的有效期与撤权语义需明确。
- 重试写入不能静默覆盖另一版本的产物。
- GC、保留、撤回、审计按产物类型和业务规则实施。

## 知识与检索
- 实时事实走权威业务 API；知识索引用于获准资料检索。
- 资料记录来源、版本、页码/媒体时段、访问范围、撤回状态。
- 先授权过滤，再交给模型；最终引用打开时再次核权。
- pgvector 和 Docling 是按需候选，不是默认业务数据库或万能内容引擎。
- 记忆不得自动升级为业务事实。

## 数据迁移
支持能力版本、任务与产物的可追溯导出；执行历史的兼容与迁移按 Temporal 官方机制验证，不能假设可任意修改历史。
