# v0.4.1 完整产品验收表 · 本轮证据与选型判定

本页沿用 PR #7 已冻结主表，对每个需求编号单列本轮判定，并按原 23 组比较各候选。原有“观察什么、验收方法、分阶段应取得什么证据”三列仍以[冻结主表](https://github.com/zhuquanwei111/mingjing---agent/blob/52208b482fab9c74b3193a9789a0ff0abf2f5d99/docs/requirements/route-b-w0-acceptance.md)为准。[R4 当时的填证稿](https://github.com/zhuquanwei111/mingjing---agent/blob/9d61564347dbea5ada09678c1aa8b9d16f36a2df/docs/requirements/route-b-w0-acceptance.md) · [每组失败会改变哪个组件](../designs/whole-product-review.md) · [选型裁决和独立评审](../designs/whole-product-decision.md)

需求原件 SHA-256 为 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`。41 项 FR、11 项 NFR、7 项 TS 和 17 项 AC 保持原分组，各编号一次。按第 7 章的阶段二裁决架构，阶段三在真实宿主贯通，阶段四面向运营加固，稳定后再进行能力扩展。逐项说明适用阶段，使后续验证有责任、时限和失败处置。凡已有反例必须先修正或封闭有问题的路径；线上准入仍取决于目标环境实证。

**如何读证据等级。** “机制实测”表示本轮有直接运行样本证明该项的架构机制；“局部实测”表示只验证其中若干要求；“文档核实”用于技术选择与职责分析；“未实测”指尚无能判定该项指定场景的完整运行；“条件项”在该功能实际启用前验。局部实测中可能包含已知失败，逐项说明。每一行同时给出余项，列的历史 PR 只支持随附所述事实。计数是检索索引，不设总分或完成率。**安全、授权、结果正确、未知操作处理、扩展与可行性均独立裁决，一项硬失败不能靠其他行抵消。**

## 路线对照 · 采用相同 23 组

下表列各路线能直接指出的样本或文档。标为未测、未比较或缺目标宿主的格子保持未知。A 的历史范围来自 #5，P2 的同库测试只用于所述旧资产；#6 独立质量库、#10/11 共性机制须重新接入目标宿主，不能算任一完整平台已通过整组。B 和 A 旧实验覆盖较多的部分不能转化为后来候选的失败，五条新证据也不能反推所有分项通过。

| 原组 | A/P2 改造 · 历史 | 路线 B | Windmill CE | DBOS + Pydantic AI | Mastra | Agno AgentOS |
| --- | --- | --- | --- | --- | --- | --- |
| G01 产品边界和事实权威 | P2 产品对象/业务账 | 自有宿主+产品账/引擎 | 应用作业+外账 | PG 产品/引擎分库 | PG 运行快照+外账 | 队列/运行+产品账 |
| G02 选型和复用 | 改造原执行核，#5 对照 | 组件组合与新公共适配 | 完整应用+治理出口 | 嵌入引擎+PG | Node 原生运行器+PG | 完整宿主+外部执行 |
| G03 受理、目标与结果可读 | 合成任务 | 合成任务、无真实用户闭环 | 作业 API，未验业务受理 | 执行 ID，未验需求理解 | run ID，未验业务受理 | HTTP 受理，未验需求理解 |
| G04 按需推理与真实循环 | LangGraph 动态循环 | 受控 0/1/2 工具，真实任务 0/2 条件 | 动态一工具、两轮 | 原生延迟工具一回合 | 原生 durable Agent 一回合 | 暂停、原号回填一回合 |
| G05 依赖、异步与协作 | #5 子任务与取消切片 | #5 子工作流，#12 等待 | 原生流程/子作业树 | 待核与取消本地工作流 | 两层挂起快照 | 持久暂停+原生取消 |
| G06 运行边界与共享预算 | #5 并发父额度 | #5 父额度；#10 迟到 | 单操作预留；模型断连对照 | 单操作预留/核销 | 单操作预留/核销 | 单操作预留/核销 |
| G07 异构能力和扩展 | 既有契约内扩展 | 同步样本三入口；异步一入口 | 两个脚本+一个 Flow | 一种外部工具适配 | 一种外部工具适配 | 同一异步能力三入口正例 |
| G08 发现、发布与调用门禁 | 角色/发布负例 | #5 部分门禁，命令提供候选 | 公开脚本登记，未测发现 | 未比较目录发现 | 未比较目录发现 | 已知工具，未测发现 |
| G09 模型可换、降级可查 | SDK/模型协议切片 | #5/#10 SDK；完整降级未测 | 流式代理与断回执，未测降级 | 同一 SDK，未测降级 | 单模型协议，未测降级 | 固定 OpenAIChat 映射，未测降级 |
| G10 上下文、会话及可选长期记忆 | 未测上下文压缩 | 受限正文外置，模型/历史取样 | 默认/受控映射实查 | 产品检查点、引用 | 默认/受控快照实查 | 默认/引用各四个落点 |
| G11 业务事实、资料及生命周期 | 未测资料撤回链 | 未测资料撤回链 | 未测资料撤回链 | 未测资料撤回链 | 未测资料撤回链 | 未测资料撤回链 |
| G12 产物、质量与事后评测 | #5 正负交付 | #5 正负交付；#6 为独立库 | 按回执交付，未验 AC-15 | 同左，未验 AC-15 | 同左，未验 AC-15 | 同左，未验 AC-15 |
| G13 任务、运行与用户状态 | 历史与状态切片 | 账、运行、尝试/待核 | 作业树与产品状态 | 工作流状态与产品账 | 外嵌两层状态与产品账 | session/run/票据与产品账 |
| G14 持久执行与恢复 | 原机制故障恢复 | 真实 Worker 重入、回合检查点 | 工具脚本重入/原作业 | 嵌入执行器及双进程接管 | 原生租约转移/快照 | 已持久暂停后重启续接 |
| G15 取消、未知及跨组件对账 | #5 取消/未知切片 | #10/#12 迟到/错配/未知 | 默认/治理模型及工具出口 | 裸步骤重复/治理对照 | 裸步骤重复/治理对照 | 未知、重复继续和产品状态 |
| G16 身份、隔离与运行中撤权 | 受控域；P2 旧同库终核 | #5/#11 单域，实际业务方未接 | 合成取消与代理；无真实 IAM | 有权/取消，不作全面撤权证据 | 产品取消，未测并发撤权 | 暂停后撤权、网关拒绝 |
| G17 不可信内容与执行环境 | 越权工具拒绝；无第三方沙盒结论 | 同一类拒绝；恢复后真实沙盒未验 | 未评不可信脚本隔离 | 未评第三方执行器 | 未评第三方执行器 | 未评第三方执行器 |
| G18 审计与评测计量关联 | 测试轨迹与收端 | 历史载荷/操作关联 | 公共表与协议两端 | 引擎与外部步骤原始账 | PG 快照/独立收端 | 队列/运行/HTTP 与产品/模型阳性 |
| G19 在途版本与发布回退 | 既有版本/回归资产 | 应用编解码跨版，SDK 未跨版 | 应用旧版隔离，非 SDK 升级 | 读旧/隔离，非 SDK 升级 | 格式不兼容挂起，非 SDK 升级 | 数据版本不兼容，非 SDK 升级 |
| G20 资源和主体隔离 | #5 配额样本 | #5 配额，无混合负载 | 未测混合负载 | 双执行器接管，非资源争用 | 未测混合负载 | 未测混合负载 |
| G21 可测试性 | 固定依赖、#5 可重放 | 固定依赖、正负故障可重放 | 固定 CI、失败及治理对照 | 全锁、裸/治理/误报 | 全锁、裸/治理/错配 | 全锁、默认/受控/错配 |
| G22 部署、回退与灾备 | 隔离部署，无目标灾备 | 真实 PG/引擎/Worker，无目标灾备 | server、worker、PG，无目标灾备 | PG、应用执行器，接管有额外责任 | PG、Node，无目标灾备 | PG、AgentOS，无目标灾备 |
| G23 按任务类型测性能 | 无目标压测 | 无目标压测 | 无目标压测 | 无目标压测 | 无目标压测 | 无目标压测 |

[B 原始记录](https://github.com/zhuquanwei111/mingjing---agent/tree/554367bf8528a9500a88bac4033ad15a5983b4de/lab/product-review/evidence/45190768318) · [Windmill 报告](https://github.com/zhuquanwei111/mingjing---agent/blob/c847da6c10608f33ba0d88277d20400885afc04d/lab/windmill-native/REPORT.md) · [DBOS 报告及失败记录](https://github.com/zhuquanwei111/mingjing---agent/blob/75d6fccf821c5ebcd70cd837f8fa52a3e78cf936/lab/dbos/RESULT.md) · [Mastra 报告与完整锁](https://github.com/zhuquanwei111/mingjing---agent/blob/a9b6570419f6f6877e824a4abcb889e3867e6517/lab/mastra/RESULT.md) · [Agno 报告与原始事件](https://github.com/zhuquanwei111/mingjing---agent/blob/60dc1965c4cea6d4e976ed40875f82403dbb386f/lab/agno-agentos/REPORT.md) · [A/B 的原始同题报告](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md)

## 原编号逐项填证

### G01　产品边界和事实权威

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| TS-06 架构职责与部署解耦 | 文档核实 | 任务/费用/业务事实和引擎运行分别归属；四类职责可在同一部署单元实现。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) | W0a 各落点按同一操作号对账，双权威须重划。 |
| TS-07 技术示例无优先权 | 文档核实 | 候选不限 P2 或组件组合；近期扩查并额外实测 DBOS、Mastra、Agno、Windmill。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#14](https://github.com/zhuquanwei111/mingjing---agent/pull/14) | 必须出口或部署约束有变化时按原表重开对应组件。 |

### G02　选型和复用

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| TS-01 按实际效果与综合代价选型 | 文档核实 | 按可靠、安全、扩展及真实工程责任比较，已核定向实测。总成本、长期维护及真实性能均保留未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 选型时公开未知，新增环境约束或数据改变选择即重审。 |
| TS-02 覆盖四种来源路线 | 文档核实 | 完整应用、轻适配、组件组合和必要自研四条路径均进入评估，两个完整应用有真实对照。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 确定宿主和发行模式时复核适配及许可。 |
| TS-03 不同路线同一门槛 | 文档核实 | 多方案同一需求、治理/默认分列和独立收端；没有以框架数量、功能表或历史行数排名。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 裁决时按硬性门槛及已知工程代价决定。 |
| TS-04 核查成熟工程与许可 | 文档核实 | 查上游版本、许可、维护、公开应用、接口与部署，项目实测和厂商案例分列。公开案例未核真实内部成本。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 锁定正式制品和使用方式前复查版本、许可、维护及替代。 |
| TS-05 实证覆盖、缺口及投入 | 文档核实 | 每个实测工程列直接复用、产品适配、服务与未知，覆盖本次代表性链路。真实长期运维待环境测量。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 对齐目标宿主，部署与采购前确认约束。 |

### G03　受理、目标与结果可读

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-01 多入口任务受理 | 局部实测 | 实验按任务键追溯请求，尚缺目标 App 的身份绑定和缺身份拒绝。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0a 受理并以相同主体读回。 |
| FR-02 任务目标与约束识别 | 未实测 | 质量库可报缺项，尚无多要求、歧义输入生成正确任务结构的实测。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | W0a 接口澄清缺输入；对应 MVP 验真实多目标。 |
| FR-38 用户可理解的过程与结果 | 未实测 | 实验记录能看出失败和未知，尚缺用户可读的进度、部分结果、等待原因和继续入口。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | W0a 用用户身份查询同一任务，首个业务 MVP 验可理解性。 |
| AC-01 完成一次真实端到端任务 | 未实测 | 一次真实模型任务有 2 次请求、1 个工具，两个必需业务条件确认 0 项。无目标 App 受理至正式交付的真实闭环。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | W0 串通受控端到端；对应 MVP 验真实业务结果。 |

### G04　按需推理与真实循环

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-03 合理选用执行方式 | 机制实测 | 受控动态决策有不同路径，确定性入口可零模型执行；Agno 的直接与工作流各实收一次。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 固定同宿主入口和路由的正负例。 |
| FR-04 受控推理与规划 | 局部实测 | 受控模型会选不同工具，越权工具被拒。真实需求的规划及无效参数纠正全链未验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0b 验约束和实际执行端；MVP 验任务效果。 |
| FR-06 Agent 执行循环 | 机制实测 | 2 工具、1 工具和停步有收端记录；#12 已知工具结果可接续。活跃待核唤醒另见两窗口裁决。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0b 验完整宿主、多个中断点和终止；MVP 验真实业务。 |
| AC-04 接入一种 Agent Loop 能力 | 机制实测 | 受控循环有零、一、连续两个不同工具的路径及终止，部分故障下原调用配对。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0b 目标宿主和受控出口；真实业务达成另验。 |

### G05　依赖、异步与协作

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-05 多种协作模式 | 局部实测 | 并发子任务有实收和父账。多要求依赖、生成与评审、部分聚合尚未在目标宿主完整执行。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0 核先后关系；相应协作类型启用前补验。 |
| FR-07 工作流编排 | 局部实测 | 真实工作流承载活动、子流程和等待；全套依赖负例及目标宿主的错误传播未验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0a/b 验未满足的依赖零下游。 |
| FR-08 子任务与协作管理 | 局部实测 | 父子争用及取消后零交付有证；向真实可取消外部服务传播、部分汇总未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) | W0 验状态传播；有外部作业的能力启用前确认其取消协议。 |
| AC-03 接入一种异步工作流能力 | 局部实测 | 真实异步受理、等待、终局和部分取消有证，目标宿主依赖与外部取消传播待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a/b 用一个异步能力贯通。 |
| AC-05 构造多要求与依赖任务 | 未实测 | 已测子任务并行；完整多要求、前置依赖、部分成功及聚合的指定场景尚未跑通。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | 首个有该类依赖的 W0/MVP 能力正式采用前。 |

### G06　运行边界与共享预算

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-09 执行边界 | 局部实测 | 有步数/共享限额和拒绝样本；深度、无进展及运行时间未覆盖，总次数也不能证明同轮去重。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0b 验无进展、限额、到限有界停止。 |
| FR-37 资源计量与预算 | 局部实测 | 并发父预算和未知后核销有证；按责任主体归集计算、存储、网络及真实商账未测。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0 核预算共账；各实际资源启用前验计量，接商用前对账。 |
| NFR-10 成本可控 | 局部实测 | 模拟工具/模型费用与资源占额有实收，真实成本、各资源分摊和价格未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) | W0 验共账；实际供应商启用及放量前对账。 |
| AC-16 多个并发子任务同时使用共享预算 | 机制实测 | 父额度 5 下三子任务竞争与拒绝有收端证据；单笔模拟费不验证并发共享预算。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) | W0 跨实际入口核父账；真实费用在供应商启用前。 |

### G07　异构能力和扩展

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-10 异构能力接入 | 局部实测 | 普通同步与外部异步各有接法。Agno 一个已知工具经三入口使用；其他执行器没有通用通过结论。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 验宿主契约；新执行类型启用之前验其专有语义。 |
| FR-11 能力契约 | 局部实测 | 已记录同步描述及异步受理、回执/错配和版本语义。未证明接入者只靠契约即可集成任意类型。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 给出可调用契约和失败示例；稳定后盲接。 |
| FR-15 能力组合 | 机制实测 | 同一同步能力在直接、工作流、Agent 三入口各有实收；Agno 的一个异步能力亦验证三入口正例。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 验各入口在失权/错误时保持一致规则。 |
| FR-41 开发接入体验 | 局部实测 | 有受控接入示例、锁与契约。同一已知 schema 的手写转换不能证明开发者可独立接入任意能力。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 验模板/错误契约；基础稳定后由未参与设计者盲接。 |
| NFR-07 可扩展性 | 局部实测 | 记录过冻结公共文件后接入同步样本和新异步适配；尚无无限类型零侵入的依据。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 每次新增执行类型记录核心差异，稳定后盲接。 |
| AC-02 接入一种普通程序能力 | 局部实测 | 普通程序经直接调用和其他入口产生实际结果；新宿主目录、拒绝、实际受理及结果管理待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a 走目标宿主的完整程序入口。 |
| AC-17 基础链路稳定后接入事先未专门适配的中立新能力 | 未实测 | 已有固定核心后的动态字段样本和预先定义的异步工具，未完成目标基础链路稳定后的真正未知能力盲接。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | 基础链路稳定后冻结核心，由独立接入者选中立能力，核差异与原因。 |

### G08　发现、发布与调用门禁

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-12 注册、发布与授权分离 | 局部实测 | 合成目录中，未发布、禁用和无权调用的拒绝可复查。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0 在真实目录逐查登记、发布、按主体授权三种状态。 |
| FR-13 能力发现与选择 | 未实测 | 实验有由命令提供的候选。尚无按目标、版本、输入输出与当前授权过滤生产目录的证明。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0 首批目录，扩大工具集前验证无关、无权工具不被列为可执行候选。 |
| FR-14 工具执行网关 | 局部实测 | 已验部分参数/权限门禁和同域发送，真实业务端对上游已放行请求的独立拒绝仍待证。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) | W0a 接目标业务服务，记录拒绝原因及零效果。 |
| AC-06 构造权限不足或权限不可确认 | 局部实测 | 部分未知/失权拒绝有零效果证据。实际资源服务对上游已放行请求的终核待证。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) | W0a 接目标服务，在实际收端核拒绝及原因。 |

### G09　模型可换、降级可查

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-16 模型调用抽象 | 局部实测 | 同一 SDK 走受控与一次真实模型任务；记录过 SDK 配置，尚无成套供应商切换证明。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) | W0b 强制单一受控模型入口，备用接入前验可换性。 |
| FR-17 模型兼容性与降级 | 未实测 | 模型能力不足、上下文超限和结构化输出降级尚无完整对照。配对错误不能替代备用模型不兼容用例。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | W0b 测工具故障；启用备用前逐项确认不能错误降级。 |
| AC-07 构造模型不兼容和工具故障 | 未实测 | 故意错配调用可被拒绝，尚缺模型不兼容与工具故障并含错误降级/结构化输出的完整场景。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0b 验基础错误，备用模型启用前验兼容。 |

### G10　上下文、会话及可选长期记忆

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-18 上下文构建 | 局部实测 | 受限正文/引用在部分引擎及模型输入有正负探针。尚未验证无关用户历史默认不入上下文。 [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 追踪选择来源，注入无关历史并在模型端检查。 |
| FR-19 会话与任务状态分离 | 局部实测 | 会话、消息、操作与独立业务收据可区分，尚未实测摘要压缩后的权威回查。 [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 压缩后重新读取进度和业务事实。 |
| FR-20 长期记忆治理 | 条件项 | 长期记忆可选。来源冲突、过期、更新和清理尚无项目实测。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | 启用长期记忆前由数据负责人验收。 |

### G11　业务事实、资料及生命周期

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-21 权威数据访问 | 局部实测 | 独立业务收端可核效果与终局。过期资料与实时业务数字相冲突时两路选择尚未测。 [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | 首个真实数据/知识能力启用前分别查来源与版本。 |
| FR-22 知识检索与治理 | 未实测 | 无受控知识索引、缓存、撤回后检索及交付的运行证据。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | 首个知识检索能力启用前测失权、未发布、撤回。 |
| FR-23 数据生命周期 | 未实测 | 资料受理、处理、质检、发布四步属架构职责；尚未对真实资料流水线作读回。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | 知识发布启用前，未质检或已撤回材料须无法正式检索。 |
| AC-09 使用过期、未发布或撤回资料 | 未实测 | 没有过期、未发布、已撤回资料在实际索引、缓存、检索及交付上联动的记录。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | 首个知识能力接入真实资料前。 |

### G12　产物、质量与事后评测

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-24 产物与结果管理 | 局部实测 | 三个质量负例零提交、零交付，正例一份；独立质量库 15 项。新宿主非文本引用、版本、读回仍待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) | W0a 贯通判定和正式出口；首个非文本类型启用前验交付读回。 |
| FR-36 通用与可扩展评测 | 局部实测 | 前置确定性质量规则可阻止错误交付；模型/提示词升级后可比数据集及主观业务质量校准仍缺。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) | W0a 接判定器；业务 MVP 制作独立评测与回归。 |
| AC-15 工具或产物返回成功但任务契约校验失败 | 机制实测 | 确定条件不满足时实际零提交/交付，合格对照成功；15 项质量库与收端样本来自不同实现。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) | W0a 在同一新宿主贯通判定和真实出口。 |

### G13　任务、运行与用户状态

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-25 统一任务与运行标识 | 局部实测 | 产品键、引擎 run、重试和业务收据可分别追溯。目标 API 区分多次重新运行待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0a 让用户按目标读回各次运行。 |
| FR-26 执行生命周期 | 局部实测 | 已观察待核、结算、取消和部分引擎挂起。真实 UI/接口的部分完成和非法状态转换未验。 [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a 核各适用状态与外部事实一致。 |
| FR-27 适配不同执行时长 | 局部实测 | 工具回合跨进程持久化有证；客户端长期离开再连接、低延迟任务与长任务并存未知。 [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a 验脱离客户端运行并读回；资源隔离上线前压测。 |
| NFR-08 可观测性 | 局部实测 | 按同一操作可跨运行、尝试、计费与交付核查。目标宿主所有节点、版本与角色视图待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0 受理到交付全链追踪及脱敏。 |

### G14　持久执行与恢复

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-28 持久化与恢复 | 机制实测 | 各有已生效、回执未记录时的真实中断/查单；五种路径的暂停点与重入方法有差异。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 核目标宿主其余必要中断点、旧版本及交付已发未回执。 |
| NFR-01 可靠性 | 机制实测 | 固定窗口真杀进程，区分安全结束、继续和持有待核，不同接管拓扑分别记账。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a/b 核目标宿主所有必需窗口，上线前验灾备。 |
| AC-08 人为断开服务、重复提交 | 机制实测 | 固定窗口真实中断、重试、查单。模型首轮及活跃回执的两项另按专项记录判定。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a/b 目标宿主受理/交付/跨部署故障。 |

### G15　取消、未知及跨组件对账

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-29 幂等与未知结果处理 | 局部实测 | 预留、查单、防重与迟到核销有实收及负对照；模型已收单和活跃未知见两窗口裁决。 [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a 验路由/启动的原子边界；实际供方启用前核权威查单能力。 |
| FR-30 暂停、取消与授权恢复 | 局部实测 | 取消后迟到不交付有证，Agno 的已暂停撤权有实际拒绝。真实宿主的数据时效及外部取消传播未验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a/b 在相应授权权威和可取消服务处验。 |
| FR-31 跨组件一致性 | 局部实测 | 产品账、外部效果、未知回执和取消各留痕。上游已提交、下游明确失败的补偿及真实启动唯一绑定未闭环。 [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0a 竞争受理、下游失败和交付补偿。 |
| NFR-03 一致性 | 局部实测 | 已核复发、终局、待核与迟到，独立收端能证实效果。目标宿主启动及部分提交、失败交付未测。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0a 竞争启动、上游成功下游失败及对账。 |
| AC-14 父任务取消，外部提交超时，随后收到迟到结果 | 局部实测 | 取消后迟到仅核销，已知实验零后续交付。真实外部作业可否中止及父子取消传播尚待验证。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0a/b 核真实取消语义和迟到记录。 |

### G16　身份、隔离与运行中撤权

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-32 身份与授权 | 局部实测 | 合成单域验读取后撤权、两种时序与首次交接。跨权威业务出口的实际最终拒绝待证。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) | W0a/b 按真实身份逐出口验，失权后实际收端零新增。 |
| FR-33 租户与数据隔离 | 局部实测 | 存在合成身份及跨范围拒绝。跨租户检索、缓存、外部处理和交付全链未验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) | W0 首个多租户宿主，真实各路径启用前逐口复测。 |
| NFR-02 安全性 | 局部实测 | 业务动作核权和失权屏障有合成样本。真正业务端服务权限、防不可信输入与凭据隔离均未全验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 验首个真实出口；不可信执行器及每条生产路径启用前。 |
| AC-13 暂停及持续运行中撤权 | 局部实测 | 合成暂停/持续两类撤权及五屏障，首次交接同一健康域。真实跨服务、缓存及四类实际出口待验。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) | W0a/b 首个实际受限出口，其他出口启用前逐个验。 |

### G17　不可信内容与执行环境

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-34 不可信输入与执行环境 | 局部实测 | 有越权工具拒绝；尚无不可信资料、工具输出、凭据与网络隔离在恢复后的完整验证。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0b 受控工具验拒绝；启用第三方执行器前验真实隔离。 |

### G18　审计与评测计量关联

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-35 运行可观测性 | 局部实测 | 操作、收端及部分引擎历史/快照可关联；真实角色视图、全部日志/搜索属性脱敏未知。 [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 逐落点查合成标记并从访问方验权限。 |
| AC-12 运行评测、追踪和计量 | 局部实测 | 轨迹与操作/费用可关联，质量判定库有测试；未打通带数据集、提示词和规则版本的业务评测全链。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0 先核全链关联，MVP 做版本化评测回归。 |

### G19　在途版本与发布回退

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| FR-39 版本兼容 | 局部实测 | 应用格式兼容/不兼容有运行样本，未实际滚动升级两套 SDK 或完整部署。 [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 带在途任务做版本并存；实际发版前复测。 |
| FR-40 发布和回退 | 局部实测 | 拒绝禁用能力及不兼容格式隔离有切片；停接、排空、回退和审计整条发布过程未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | W0b 演练在途任务，面向正式流量发版前验目标部署。 |
| NFR-06 可维护性 | 局部实测 | 固定代码、旧格式读取和失败记录可复查；完整运维回滚、长期维护人天未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 带在途演练；发版前验实际制品。 |
| AC-11 升级或停用执行能力 | 局部实测 | 有旧数据兼容或保留待核；实际升级/停接/回退整条演练仍待执行。 [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0b 在途发版；实际制品上线前复验。 |

### G20　资源和主体隔离

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| NFR-05 隔离性 | 局部实测 | 合成主体、父配额有例。未证跨租户数据和长短任务争用情况下的全链隔离。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | W0 验身份及资源边界；目标负载下验证。 |
| AC-10 运行不同类别任务的并发负载 | 未实测 | 共享预算争用与混合流量测试条件不同。真实路由、并发隔离与性能未知。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) | 部署压测阶段分交互、后台、模型和执行器；放量前。 |

### G21　可测试性

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| NFR-09 可测试性 | 机制实测 | 有固定依赖、合同/故障用例和可复算逐笔证据，支持重复运行。正式业务回归集尚未建立。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) [#10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) [#11](https://github.com/zhuquanwei111/mingjing---agent/pull/11) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 固定宿主合同入口；对应 MVP 固定业务集及模型评测。 |

### G22　部署、回退与灾备

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| NFR-11 可部署与可恢复 | 局部实测 | 五条隔离环境可启动并接受故障；目标环境备份、恢复时间/点与发布回退未测。 [#5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | W0 验停接和核查，确定部署后、真实流量前验灾备。 |

### G23　按任务类型测性能

| 原编号与要求 | 本轮证据等级 | 已观察事实与证据范围 | 余项与最迟验证时间 |
| --- | --- | --- | --- |
| NFR-04 性能 | 未实测 | 无真实负载模型、吞吐及时延分布，约 300 名用户不能推出并发。 [#7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) | 部署设计拟定分类型指标，放量前在目标环境压测。 |
