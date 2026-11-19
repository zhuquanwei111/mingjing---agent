# 明镜风险登记

截至 2026-11-19。以下状态来自 P0 静态核验。所有 AT 现在均为待验证。风险关闭需要测试证据、适用环境和明确的边界。

| ID / 状态 | 风险与现有证据 | 控制与关闭证据 |
| --- | --- | --- |
| R01 · 高 · 待实测 | 旧插件的缓存命中历史可在 1.0.0 重放失败，反向回滚也可能失败。1.36.1 默认关闭特定 Workflow 激活批处理行为，已有对应标记的历史保留旧行为。 [插件发行说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0) · [SDK 发行说明](https://github.com/temporalio/sdk-python/releases/tag/1.36.1) | AT09/10 涵盖旧历史同版本重放、预期不兼容的历史与前滚/回滚。旧运行固定在旧 Worker，或测试并证明旧任务已排空。 |
| R02 · 高 · 待实测 | 中断后的函数重入、重复中断、缓存审批答案、消息 ID 不稳定与跨 Run 状态丢失会造成卡住或跨步骤误用。 [插件固定版本文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md) | AT02/04/09 验证一个待审批请求、确定性 ID、显式状态与 ID 去重。仅在无未决审批且 handler 已完成时续跑，恢复后读当前策略和授权。 |
| R03 · 高 · 待实测 | Activity 提交后回执丢失会触发重试，跨系统超时结果未知。同库凭幂等键、唯一约束和事务才能确认单次业务写入。 [Temporal Activities](https://docs.temporal.io/activities) | AT03/05 将 Worker 杀在提交与返回之间并观察两次执行尝试、一次业务提交、一条成功收据。外部模拟不可查且不支持幂等时记录 UNKNOWN、停止重试并进入人工核对。 |
| R04 · 高 · 待实测 | 客户端声明、历史审批或 Agent 工具参数可能绕开实时授权。撤权后旧产物引用也构成风险。 | AT04/06/08 使用合成主体，审批回调鉴权，执行边界核对当前身份、租户、资源、版本、动作和委派。数据库内测试用锁序列化撤权和写入，拒绝路径要有收据或审计证据。 |
| R05 · 高 · 待实测 | 取消、Activity 失败和供应商未知回执会改变账目与动作状态。插件不会代发 Activity heartbeat。 [插件发行说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0) | AT05/06/07 对可中断动作验证显式 heartbeat、取消后禁止新尝试、两个 Worker 争夺末额与门禁故障时拒绝。未知费用保留预留，既有收据可查。 |
| R06 · 高 · 待实测 | Pydantic、dataclass、消息 ID 或限定类名变更可能改变类型，历史与整图状态可能膨胀。LangGraph 曾发布 checkpoint 反序列化公告。 [插件固定版本文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md) · [LangGraph 安全公告](https://github.com/langchain-ai/langgraph/security/advisories) | AT08/09/10 以固定 DTO 和转换器做冷恢复与重放，校验类型和字节计数，使用受信输入与严格 checkpoint 配置。大对象走受控引用，History 中保留小型字段。 |
| R07 · 中 · 待实测 | 流式 API 为实验功能。已发送的数据块可能因 Activity 重试而重复，跨 Run 游标需要显式管理。 [插件固定版本文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md#streaming) | AT09 模拟断线、重试和续跑，记录原始事件与客户端去重结果。带稳定 ID 的合成进度可去重，最终业务状态由持久结果查询反馈。若无法满足，仅保留轮询进度方案并重新评审需求。 |
| R08 · 高 · 待实测 | Python 可解依赖，固定 Server/PG 镜像尚未启动。本机未确认容器运行权限。第三方镜像和本地制品尚无实测供应链结果。 | AT12 在隔离 Linux 环境核验镜像架构、签名或可取得的来源证明、SBOM、扫描结果、建库、备份恢复和重建。Mac CLI 冒烟可先独立完成。 |
| R09 · 中 · 待审 | 四核心 MIT，Python 传递依赖、Psycopg 二进制、容器层与商业部署形态可能有不同许可或外部通信。 [Psycopg 元数据](https://pypi.org/project/psycopg/3.3.9/) · [LangSmith 部署说明](https://docs.langchain.com/langsmith/data-plane) | 最终提供组件和通知清单，复核 LGPL 与包含原生库的分发方式。P1 断开外部遥测与模型出口。许可证或可取得性出现阻断时停止并提交替代客户端/制品选项。 |
| R10 · 中 · 待确认 | 团队运维能力、实际长任务需求、现有身份、对象存储、数据驻留与负载未知。 | AT08/12 验证本地适配与可重建性。P2 设计前确认环境资产与工作负载，并用验证证据决定是否引入生产对象存储或其他条件候选。 |
| R11 · 高 · 待实测 | 任务状态、History、图状态、收据和 OTel 若相互替代，会造成故障后状态结论不一致。 | AT01/03/11 在应用重启、重复回调或 exporter 失败后，核对产品映射、业务收据和审计仍可关联且完整。记录各状态权威和恢复证据。 |

## 门禁与替代路径

- R01、R02、R06 若出现关键重放或恢复失败，先验证固定旧 Worker、显式状态续跑和收据隔离。仍失败时提交最小重现与不可满足的语义，评估 Temporal 原生 Activity 编排或 Temporal + Pydantic AI。
- R03、R04、R05、R11 若出现重复效果、撤权后写入、未经授权的调用、预算逃逸或关键审计丢失，立即停止该实验路线。复查明镜执行边界、锁序、收据与门禁，再用原失败用例复验。
- R08、R09 的运行权限、依赖可取得性或许可无法达成时，记录具体制品、限制和隔离环境选项，由用户决定路线。容器或自托管环境不适合时按 [09 待核验事项](09_OPEN_QUESTIONS.md) 重新比较顶层调度器。
- P1 技术证据按 [AT01–AT12](08_ACCEPTANCE_TESTS.md) 和 [P1 执行计划](P1_EXECUTION_PLAN.md) 留存。P1 通过后再请用户确认 P2。
