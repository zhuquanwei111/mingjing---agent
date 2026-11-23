# Mastra 原生持久 Agent 对照 · 事前协议

起点为 #5 bb55c843；#12 f5b4df8f 的 lab/product-review/PLAN.md 为对照。独立评审优先核对崩溃窗口、外发计数和原文落点。此草稿只作技术选型判别。固定 @mastra/core 1.85.0、@mastra/pg 1.37.0，均由同一发布标签的 package.json 确认，后者要求 core >=1.84 <2 且 Node >=22.13。公开 Agent、createDurableAgent、stream、recover、createTool、PostgresStore。固定版源码根许可 Apache-2.0，ee/ 及第三方另有许可。普通 Agent 与原生 PostgreSQL 工作流持久化，不引入第二个调度器。

1. 用独立 Node 进程归属同一 Mastra run，真正 PostgreSQL。独立 HTTP 收端记录每次模型请求、随机生成的调用 ID、每个工具派发及逐次模拟计费；异步任务受理时尚无效果，完成后提交业务效果和独有回执。稳定产品 operation 在首轮前确定，不依赖工具调用 ID。进程死亡前取 DB 的运行中快照和产品操作未终结、收端效果/费用已生效的证据，验证未含回执，再 SIGKILL 旧 PID。等原生 claim 到期，用新进程对相同 runId 调用公开 recover。上传快照、独立事件、计数、请求正文、PID/信号及原始失败。
2. 原生重放对照禁用产品查单保护，切实观测重复工具或模型请求、重复收费。对照的不安全边界只限这个隔离合成收端。受控适配器持久记录首发资格和原预留，重入只读原单。已知有权要工具发 1、效果 1、工具费 1、模型请求及每请求费用 2、独立交付 1。最后一个模型请求须以原工具调用 ID 携带真实回执或由受权模型适配器解析其引用。工具/模型收费各自独立，业务效果按稳定键合并不会合并费用。
3. 不可查重入时须保留 held=3、spent=0，模型只收到首轮、工具仅收一次、零正式交付。后取消并收到同一迟到回执两次，只结算一次 held=0、spent=1，工具/模型/交付的收端计数零增量。真实未知与无权限不得用“成功待核”工具消息返回模型。重入如何隔离后续推理、产品终局和框架状态分别记录。
4. 独有合成正文仅在产品输入和收端结果产生。对照原生快照的解码 JSON、产品库和模型请求；观测恢复时与完成时的正文与调用 ID。受控引用路径如有需要在框架外保存正文并仅在受权模型端解析；分别披露框架新增适配、产品账、调度进程数及可运营性未知。必须保留正文命中阳性对照。关键反例可排除某种直接接法；安装、环境、探针错误先修复。只对确证边界给结论，不推断全部 TypeScript 底座、生产 IAM、商业账单、容量、费用、跨版或 W0。

上游固定包与许可见 [core](https://github.com/mastra-ai/mastra/blob/%40mastra%2Fcore%401.85.0/packages/core/package.json)、[PG](https://github.com/mastra-ai/mastra/blob/%40mastra%2Fcore%401.85.0/stores/pg/package.json)、[许可](https://github.com/mastra-ai/mastra/blob/%40mastra%2Fcore%401.85.0/LICENSE.md)、[恢复契约](https://mastra.ai/docs/harness/durable-agents)。
