# Mastra 原生运行与外部操作边界

目标是验证同一个 Node Agent 运行器与 PostgreSQL 能否接管一次中断的模型/工具循环。独立实验起点 #5 bb55c843，判据与 #12 f5b4df8f 的同窗实验一致。这里的输入、业务执行、回执、模型和单位费用全为合成。模型为独立 HTTP 协议收端，按到达请求分别记账。

## 裁决与收端原始计数

**保留 Mastra + PostgreSQL + 受控操作/模型适配器，排除工具直接重复提交的接法。** 此固定实现确实把被测 Agent 回合和接管放在同一运行器，在此路径上省去单独 Temporal 服务。已保留的自有操作账、敏感正文引用与交付治理仍决定能否用于全产品。跨产品编排、运维、人力和成本没有对等量测，本实验不能宣布整个平台胜出。

| 固定窗口的用例 | 工具 HTTP | 业务效果 | 工具费 | 模型 HTTP | 模型费 | 交付 | 产品/运行状态 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 直接调用，重放未确认步骤 | 2 | 1 | 2 | 2 | 2 | 1 | 相同操作被重复收费 |
| 已知且原调用可配对 | 1 | 1 | 1 | 2 | 2 | 1 | 恢复结束，正式出口收到原回执 |
| 不可查→产品取消→迟到两次 | 1 | 1 | 1 | 1 | 1 | 0 | 两层挂起，先 held=3/spent=0；产品取消后两次核销影响 [1,0] 行，最终 0/1 |
| 以不同产品记录版本读取 | 1 | 1 | 1 | 1 | 1 | 0 | 两层挂起，保留 v1，已知回执仅核费 |
| 回执中的调用号被调换 | 1 | 1 | 1 | 1 | 1 | 0 | 两层挂起，产品 held=3/spent=0，错误配对未到模型 |

实跑代码 d6056739c9f4a1965fbcb771cedae1d93a1ca161。已知用例 PID 2983→3120，外层 runId 76cc2d33-bcd5-4f4f-ac4b-481e0c8f2f6f，两处检查点已解码，并看到 PG owner 更换及 generation 增加。外部收端验证原 assistant tool call、第二轮 tool 消息以及完整原回执一致。原生直接模式首个活跃快照含提示原文、第二个含提示与回执；受控已知两次的两种正文均未命中，原工具调用 ID 均命中。[原始计数](evidence/45193324986/results.json) · [68 份原始文件](evidence/45193324986/raw.zip) · [各文件 SHA256](evidence/45193324986/SHA256SUMS) · [实跑日志](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193324986)

初跑 ae39a6c 与增强见证的 7a319c4 都记录了默认 recover reader 在挂起后继续等待读取，三次 Node exit 13。固定版公开配置 closeOnSuspend:true 让 reader 随框架挂起结束；该修正不改变任何验收阈值。独立方案评审要求双时点快照和两个负例，独立代码评审要求按原始到达包计费、严格核对回执及缩窄取消主张。修正后评审者独立解压核验关键证据 SHA、PID、原请求、挂起与迟到两次核销。[初跑日志节录](evidence/45192503460/job-excerpt.log.gz) · [第二次失败原始记录](evidence/45193060608/raw.zip) · [附件与退出状态](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193060608)

## 实测的界线

同一模型先生成随机工具调用号。工具在可重入区提交稳定产品操作号，独立异步收端返回受理，随后效果及费用提交。控制器从 PostgreSQL 和独立 SQLite 分别核对运行中快照、已生效和未入账的工具结果，再向旧 Node PID 发 SIGKILL。等待 16 秒后，新进程调用 recover(runId)；未强抢。第二轮到达后先扣住响应，再读取 PostgreSQL，以覆盖会在终局被清理的中间状态。另有两次向收端提交同一业务操作却出现两笔费用的阳性对照。

直接调用已出现重复工具请求、重复费用和中间快照正文。运行器接管、复用原模型工具调用 ID 和生成下一轮请求均可复用。产品须负责稳定操作与首发资格、预留、查单、迟到结算、不可推进时挂起、模型入口引用解析以及正式交付。示例只有一种异步能力；业务服务对实际写入/接收的授权、网络与事务的提交边界、重复正式交付等仍需真实宿主另验。

只看选定两类正文标记，受控模式把提示与回执原文移出框架输入/工具返回，在访问受控模型前按产品记录解析。运行器仍持久化工具调用号与产品引用。随机关联 ID 的可关联性应按部署的数据分类与访问权限评估。这个有限扫描覆盖原生 workflow 表与载荷映射，未覆盖日志、全链路追踪、缓存、真实供应商保留政策及受限正文外发的并发撤权。

## 复用与自有责任

| 责任 | 这次实际采用的机制 | 尚需真实环境回答 |
| --- | --- | --- |
| Agent 回合和持久运行 | Mastra Agent、createDurableAgent、公开 recover、PG run claim、外层和嵌套执行快照与工具 suspend | 多副本恢复和队列公平性、升级与积压、长等待/定时调度、部分失联、历史增长/清理、备份恢复、目标并发容量 |
| 工具、费用与交付 | PostgreSQL 产品操作的首发状态、稳定外部操作号、按原号查单、预留与条件结算，应用检查消息绑定后交付 | 多租户资源授权、真正消费方的上限和幂等/查单、取消与 I/O 竞争、正式交付收据与多次恢复 |
| 外发与隐私 | 产品引用、受控模型 HTTP transport、错误配对时挂起、独立接收日志 | 日志与备份的敏感信息、模型响应正文与任意参数的通用保护、生产 IAM、敏感调用号映射 |
| 操作与维护 | 实测候选不需 Temporal 服务，一个主动 Mastra Node worker 与一个 PostgreSQL 实例即能跑这条路径。测试另启 controller 与独立见证进程用于观测 | 自动发现与重启策略、多机观察流所需共享 pub/sub 和 replay cache、告警对账、滚动升级、真实运维成本。生产部署数和节省人日未测 |

## 版本与许可

@mastra/core 1.85.0、@mastra/pg 1.37.0 取自同一 release aa82a4a7858c637f654be24391ff306dcb568c00；适配器要求 core >=1.84 且 <2，Node >=22.13。本实验直接调用的 Mastra API 在上游普通 Apache-2.0 范围；ee/ 有单独许可，第三方保留各自许可。@ai-sdk/openai 2.0.0 为 Apache-2.0，pg 8.23.1 与 zod 4.6.7 为 MIT。分发和生产制品的依赖与 EE 边界另审。

[Mastra 许可](https://github.com/mastra-ai/mastra/blob/aa82a4a7858c637f654be24391ff306dcb568c00/LICENSE.md) · [固定版恢复与租约](https://github.com/mastra-ai/mastra/blob/aa82a4a7858c637f654be24391ff306dcb568c00/packages/core/src/agent/durable/durable-agent.ts) · [PG 适配器](https://github.com/mastra-ai/mastra/blob/aa82a4a7858c637f654be24391ff306dcb568c00/stores/pg/package.json) · [AI SDK 许可](https://github.com/vercel/ai/blob/%40ai-sdk%2Fopenai%402.0.0/packages/openai/package.json) · [pg](https://github.com/brianc/node-postgres/blob/pg%408.23.1/packages/pg/package.json) · [Zod](https://github.com/colinhacks/zod/blob/v4.6.7/packages/zod/package.json)


## 复验

在一次性空 PostgreSQL 上设置 DB_URL，LAB_OUT 指向新证据目录，从 lab/mastra 运行 npm ci --ignore-scripts 后执行 node driver.mjs。驱动会建表并启动本地见证、两个先后接管的独立 Node worker。CI 入口使用指定 Node 24.22.3、基础 PostgreSQL 镜像摘要和 npm v3 锁，锁中 166 个非根条目，SHA256 207d3cb243d4a2129e061d24b2302cd4efa65dc86e1d53e88c57c021fda6ee5b。本次工具与模型共用一台独立 HTTP 见证进程，以不同端点及独立逐笔事件/费用类型记录；业务效果按操作去重，费用按请求去重。SQLite 仅用于测试收端独立见证。归档中的文件可解压后用 SHA256SUMS 逐文件核对，CI 附件另保留 SQLite 原库及 WAL。没有部署生产、调用付费模型或开启 W0。
