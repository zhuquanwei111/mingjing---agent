# 完整产品候选路径与入围依据

> 历史评审资料。当前建设依据见[现行架构与实施门禁](../../../designs/current-architecture-baseline.md)。

本轮扩大到不同语言、完整应用、集成运行时、可嵌入调度和已有业务宿主。判断以 v0.4.1 的可扩展执行、动作级权限、恢复与对账、共享预算、交付正确性及长期维护责任为准。验证同一外部效果的窗口，分别数物理发送、效果、模拟收费、模型实收与交付；产品任务状态单独读回。既有 A/B 比较的两个对手不能代表全部市场。外部产品的文档和上游用例单列证据级别。

## 直接进入隔离对照的不同起点

| 路径 | 有证据的起点及为何会改变选型 | 需要现场回答的差异 |
| --- | --- | --- |
| B · Python、Temporal、PostgreSQL、Pydantic AI | 自有宿主可将受限正文和权威回执留在产品存储，调度只接收引用。#5 及 #12 验证了至少一类动态循环、异步工具和换进程续跑。 | 长期维护外部异步契约、意图、模型出口、对账、预算和版本；已有四个组件均可按具体失效替换。[B 实验](https://github.com/zhuquanwei111/mingjing---agent/pull/12) |
| Windmill CE · 完整自托管应用 | 原生 Agent、脚本/Flow、作业树、审批、可配置模型端和持久检查点。能复用现成 API、Worker、目录和控制台。这条具体轻适配路径在完整产品复审中首次入围。 | 原生重试/取消、审批等待点与任意工具已生效窗口的差异；受限正文与别名留在哪个域。自有网关、业务账和许可按用途计入。[上游检查点](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/windmill-worker/src/ai/pause.rs#L282-L329) · [许可](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/LICENSE) · [同题实验](https://github.com/zhuquanwei111/mingjing---agent/pull/13) |
| Agno AgentOS · 可嵌入的完整运行时 | 有 REST API、Agent、Team、Workflow、持久会话。原生 external_execution 把工具执行移到受控业务端，允许按原 session、run 和 requirement 回填。足以改变要自建多少宿主这一判断。 | 已完成的 run 再续、并发/错配回填、账务及模型出口仍须对账。运行时提供的身份机制与真实业务 ACL 各有职责。[AgentOS 公开接口](https://docs.agno.com/agent-os/overview) · [外部执行/续跑示例](https://docs.agno.com/examples/agent-os/human-in-the-loop/external-execution) · [v3.2.0 恢复源码](https://github.com/agno-agi/agno/blob/v3.2.0/libs/agno/agno/agent/_run.py) |
| Mastra · TypeScript Agent、Workflow、PG | 可完全离开路线 B 的 Agent 和调度组件。原生 durable agent、运行快照、租约、工具调用 ID 和恢复入口，既可嵌入既有后端又能自托管。 | 官方说明工具结果尚未保存时能再次执行，失去租约也可能出现重叠；需独立操作账、脱敏快照、验证代理治理和跨重启回执。核心与企业功能的许可分别核定。[持久 Agent 与运行边界](https://mastra.ai/docs/harness/durable-agents) |
| DBOS + PostgreSQL · 嵌入式调度 | 能在已有业务数据库一类服务上保存工作流/step 的状态。可直接减少一项独立工作流服务的部署，是对 Temporal 有决定意义的挑战者。Pydantic AI 可组合，也可替换。 | step 在回写前中断仍可再次执行；事务函数与外部副作用须分开。单机重启和多执行器失联接管方式不同，有无 Conductor 的运维责任须计入。[恢复及接管](https://docs.dbos.dev/production/workflow-recovery) · [持久 Agent 接口](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/) |

## 查看过但未据此判优的替代

| 路径 | 可复用的具体优势 | 当前未改变决定之处、重新入围条件 |
| --- | --- | --- |
| 现有宿主＋普通程序/业务事务；P2 或 P2＋LangGraph | 直接执行确定任务，可由业务方在同事务终核权限、幂等和提交；P2 旧测试、契约和真实收据可复用。#5 路线 A 验证过 LangGraph 与 Temporal 的组合。 | #5 旧 P2 的固定选择器由新动态循环替代；单用已有事务或裸队列仍要自行实现跨步骤恢复、长等待、动态工具配对。若现有宿主已具备这些经过实证的能力，可直接返回此方案。[A/B 运行与代价](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md) |
| Dify 1.20.0 · 完整应用 | 可复用知识、插件、模型租户策略、系统模型额度和人工暂停恢复。 | 已识别的接口仍缺 Agent 进程在工具已生效时恢复原操作的具体入口，额外多 workspace 使用有许可条件。若出现按稳定操作号恢复在途工具和阻止失权后交付的有限适配，即须同题测。[源码与 G02 处置](whole-product-review.md) |
| Langflow v1.13.2、Flowise Agentflow V2、n8n | 可视化编排、工具/连接器、暂停与人工审批有真实复用价值；不同项目的自托管权限、部署及许可不相同。 | Langflow 的冻结分支设计文档仍标草案，需证明持久化的批准/顶点映射到未回写的外部操作；Flowise 官方已宣布终止维护，长期基线需要明确维护方；n8n 固定版区分 Sustainable Use 与企业功能，且审批前等待不能证明效果后的恢复。出现可验证运行/产权边界时按同题评估。[Langflow 固定版说明](https://github.com/langflow-ai/langflow/blob/v1.13.2/docs/features/durable-execution-hitl.md) · [Flowise 官方公告](https://flowiseai.com/sunset) · [n8n 固定版许可](https://github.com/n8n-io/n8n/blob/n8n%402.47.4/LICENSE.md) |
| Restate、Dapr Agents | Restate 有日志重放、服务处理器及原生 Agent 适配；Dapr Agents 将耐久工作流、服务调用和状态放在应用/sidecar 体系，可支持异构服务。 | Restate 也明确中断在日志回写前的副作用步骤会重入，需治理账本与自托管服务器。Dapr 增 sidecar 与状态组件，未测得明镜部署中抵消其代价的跨语言需求。若 DBOS 或 Temporal 的特定恢复/部署要求失效，或宿主本来就在 Dapr 上，实测对应替代。[Restate 持久化接口](https://pydantic.dev/docs/ai/capabilities/durable_execution/restate/) · [Dapr 工作流](https://dapr.io/workflow/) |
| LangGraph 独立＋检查点、Google ADK、OpenAI Agents SDK、Microsoft Agent Framework | 可替换 Agent 或工作流层。ADK 从已记事件恢复，未返回的工具可再次执行；OpenAI RunState 能续审批与部分会话写回，需要独占相应会话；Microsoft 自托管 Worker 通过 Durable Task 后端提供持久运行。LangGraph 有图、检查点与按步骤持久执行。 | 每个单独 SDK 都须落实明镜的业务授权、共享预算和外部收据；不能将框架恢复推导为付费外部调用仅一次。若已选 Agent 无法安全接续或目标栈已有相应运行时，优先按相同失败窗口比较合适的那一项。未给这组候选打运行分。[LangGraph](https://docs.langchain.com/oss/python/langgraph/persistence) · [ADK](https://adk.dev/runtime/resume/) · [OpenAI RunState](https://openai.github.io/openai-agents-python/ref/run_state/) · [Microsoft Durable Extension](https://learn.microsoft.com/en-us/agent-framework/hosting/durable-extension) |
| SpiceDB、OpenFGA · 可单独替换权限判定服务 | SpiceDB 提供一致性令牌与指定新鲜度，OpenFGA 可选择更高一致性，适合组织/资源关系复杂时比较。 | 单独一次最新的权限查询不能与另一个系统的后续网络写入自动成为一个原子动作。真实业务服务同事务可终核时优先沿用；若实际身份权威缺少可追溯顺序，拿对应产品做 W0a 双向终核和不可撤回点试验。无需现在默认部署第二套身份系统。[SpiceDB](https://authzed.com/docs/spicedb/concepts/consistency) · [OpenFGA](https://openfga.dev/blog/query-consistency-options-announcement) |

对产品样本的优先顺序由能改变决定的问题驱动。完整应用改变宿主自研范围，不同语言的集成运行时改变 Agent 和编排能否共用一个开发底座，DBOS 改变独立服务数。模型供应商和检索实现各自留在可替换边界。本次使用受控模型与合成数据，商业运行条件在真实用途明确后复核。

## 同题判定及工程代价口径

只有满足当前阶段适用的硬要求才比较原生复用、自研和运维。用同一合成业务事件核验「已受理未生效 → 效果及一笔模拟费用已提交 → 原回执尚未记录 → 原进程被终止 → 新进程重入」。分别列实际工具外发／业务效果／按物理到达的模拟费用／模型接收／正式交付。域内代理尝试与域外实际接收分开；若受限正文已交给未获授权的处理方，不能因最后模型未收费而通过。计费的观测点、一次共享故障与样本数、已知有权必须继续、未知保留预留、取消迟到只能核销，在所有方案上一致。

#12 的合成标记和原始工具调用号是检查引擎载荷的探针。应报告何者为受限正文、何者是可替换的普通关联号、引擎的读取权归谁；仅见普通随机运行 ID 不自动推导泄露客户数据。真实产品判据来自 FR-32/33/35 和 NFR-02，试验约定及未测的真实治理分别记录。一个引擎在有授权的受治理网关加入一次性操作账后通过，须明示依赖该改造；所有候选适用相同口径。

相同模型/业务测试夹具及实验控制器不计作某个候选的生产自研。分别列上游直接提供的可运行职责、必需的业务和公共适配、是否修改上游核心、部署服务和特殊拓扑要求。物理行数只描述对应试件，不能跨不同统计范围换算工期，也不把研究阶段已有代码投入当作采纳加分。有合格候选而数据尚不足以区分关键选择时，逐个列关闭条件，允许暂缓整体采纳；不为等真实商业账单或全年流量永久悬置已足够的职责选择。

## 已完成的验证

实测复用、产品自研、部署差异、样本计数及限制按同一口径列在[完整产品决策的跨路线实测表](whole-product-decision.md#跨路线实测结果)。可按如下入口查看原始记录、依赖和失败过程。

[B 原始记录](https://github.com/zhuquanwei111/mingjing---agent/tree/554367bf8528a9500a88bac4033ad15a5983b4de/lab/product-review/evidence/45190768318) · [Windmill 报告](https://github.com/zhuquanwei111/mingjing---agent/blob/c847da6c10608f33ba0d88277d20400885afc04d/lab/windmill-native/REPORT.md) · [DBOS 报告及失败记录](https://github.com/zhuquanwei111/mingjing---agent/blob/75d6fccf821c5ebcd70cd837f8fa52a3e78cf936/lab/dbos/RESULT.md) · [Mastra 报告与完整锁](https://github.com/zhuquanwei111/mingjing---agent/blob/a9b6570419f6f6877e824a4abcb889e3867e6517/lab/mastra/RESULT.md) · [Agno 报告与原始事件](https://github.com/zhuquanwei111/mingjing---agent/blob/60dc1965c4cea6d4e976ed40875f82403dbb386f/lab/agno-agentos/REPORT.md)
