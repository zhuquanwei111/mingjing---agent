# 明镜智能体架构与技术选型决策

2026 年 11 月 23 日 · v0.4.1 · 隔离工程验证

**主推荐为路线 B。明镜采用 Python、PostgreSQL、Temporal 和 Pydantic AI。** 一个能力注册一次，经授权后可由直接 API、确定性工作流或 Agent 调用。Temporal 负责调度、取消、重试和恢复。PostgreSQL 保存明镜自己的任务状态、授权、业务回执和预算账本。Pydantic AI 只负责需要模型决定下一步的那段执行。正式操作和交付各自经过授权及完成条件校验。

**选择依据。** A 和 B 的同场实测结果见下表。决定取舍的是谁拥有 Agent 循环，以及下一种能力需要改哪里。A 可以有效复用 P2 的发布、资源授权、事务任务和回执，但为通过动态 Agent 测试，实验另写了 LangGraph 的模型节点、工具分派、结果配对和终止条件，绕开了原 P2 的固定选择器。B 直接使用 Pydantic AI 的原生循环和工具接口，项目只在模型出站和工具执行处实现授权。两边都必须自己实现正式交付校验、未知回执治理和父子预算。这些实测责任决定了 B 有更清楚的长期维护边界。两路使用同一持久化引擎，实验支持这两种组合之间的选择。Dapr 与完整应用的相对可靠性仍未知。

## 同场结果

指定 P2 基线为 `fdf04240eba747a9a681a1dad627da22d4b89cdd`。统一标准先于两条路线的执行代码冻结，SHA-256 为 `22b7e3bdd7094e47f6977c7e03653aff79408efe799a4ceba94174e0104ef450`。最终运行的实验分支提交为 `bb55c843b8dd2e9ad646e982a38cda350b3df952`，Runner 实际检出 `7d618721f3e9f7a7a54dd09bc6f13035289401c2`。A 先结束，B 在独立的 Ubuntu AMD64 主机启动。两路的服务、卷、网络、命名空间、身份、推理容器、业务账本和外部接收账本分别新建。对端真实只读测试身份和本端错误口令都须被数据库拒绝，本端身份须能读回标记。A 导入指定 P2 副本。B 的运行容器只挂载 B 目录和中立协议、测试夹具，没有 P2 或 A 执行代码。预检命令复用了 P2 测试镜像中的 PostgreSQL 客户端与 Temporal SDK。

| 统一门槛 | A | B | 支撑判定的运行事实 |
|---|---|---|---|
| V01 · 多轮 Agent | 通过 | 通过 | 受控模型先读清单，拿到随机键后才查状态，两种工具、三次模型请求、逐轮回传。另有交换工具顺序与立即停止的输入。真实模型接收的任务只要求核验，不指定工具名或调用顺序。两路都用同一权重的真实模型完成工具往返。完整、缺失、证据引用按实际工具返回值计算。 |
| V02 · 新能力 | 通过 | 通过 | 最终提交冻结后，按同一检出版本生成新名称和字段，安装外部校验算法，HTTP、确定性工作流、Agent 三种入口得到同一回执。前两者的模型请求合计 0。负例覆盖输入非法、未发布、撤权和跨租户身份。两边运行核心在安装前后的逐文件哈希一致。 |
| V03 · 运行中撤权 | 通过 | 通过 | 在读取、送模型、送工具、正式写入和受限交付前，分别提交撤权后放行屏障。覆盖持续执行、Temporal 持久暂停/信号恢复、Agent 缓存已有资料、外部供应商发送。按收端记录核对受阻动作及后续动作均为 0。 |
| V04 · 幂等与恢复 | 通过 | 通过 | 独立供应商库先提交，再丢回执并强杀 Worker。换进程后，可查时一次结算；不可查时保留 3 单位预留。父任务取消后两次迟到通知只按可信供应商查询结果结算，供应商写入一次，下游发送为 0。 |
| V05 · 交付质量 | 通过 | 通过 | 实际工具成功后，缺一项、证据版本错误、校验服务不可用三种情形均进入待核，分别保存原因，正式提交与交付数为 0。完整正例两端各一次。 |
| V06 · 父子预算 | 通过 | 通过 | 同一父任务总额 5，三个真实子工作流各申请 3。首轮只有一个获准，其余两个已在持有者暂停时被拒。实耗 2 后再利用余额，两笔合计 4；重复计量不重扣。预留后崩溃保留 3，收费后崩溃据查单结算 2，取消后新子任务被拦截。 |

**真实模型的实际表现。** A 发出 2 次模型请求，实际执行 1 次工具调用，业务校验确认 0 项，仍缺 2 项，B 发出 2 次模型请求，实际执行 1 次工具调用，业务校验确认 0 项，仍缺 2 项。模型选择和工具回传均可在接收端逐条复查。此前的同权重运行中，两边都曾得到 invalid-key，对应项目被保存为缺失；这直接支持把业务完成校验放在正式交付边界。[带证据引用的运行](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45130185846)

最终两路分别保留 30、30 个独立场景的接收端记录和 42、42 段顶层工作流历史摘要。统计文件汇总各用例的账本状态和接收计数。完整作业日志保留原始关联键、工具请求/回传、故障注入顺序、进程号、顶层工作流事件（含子任务启动与取消）和实际安装版本。[最终同场作业](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45131052175) · [机器可读摘要](evidence/summary.json) · [完整作业日志归档](evidence/run-logs.zip) · [各日志 SHA-256](evidence/log-manifest.json)

## 哪些技术承担哪些责任

| 边界 | 选型与责任 |
|---|---|
| 宿主 API 与能力注册 | 保留版本化输入、输出和资源范围。读操作、确定性业务和已知流程可直接调用。发布、发现与实际执行授权分开。实验 HTTP 服务是黑盒测试入口，Web 框架没有参加评选。 |
| 长任务与父子任务 | Temporal 是一个顶层持久化调度器。工作流控制顺序、并发、暂停、取消；调用具有稳定业务操作号的 Activity。产品任务结论和外部副作用从业务账本或供应商查单确认。 |
| Agent | Pydantic AI Slim 与工具注册接口。模型和工具可替换；受限输入进入模型、工具或正式操作前，在实际 I/O 边界重核身份、资源和动作。敏感内容通过受控引用交给工作进程。 |
| 业务正确性 | PostgreSQL 持久化权限、操作键、回执、取消、预算预留与计量。发出请求前先持久登记；结果未知时查单并保留预留。业务完成条件由明镜校验，通过后才允许提交和交付。 |
| 模型 | 实验使用本地 Ollama 及 Qwen2.5 1.5B，纯合成数据。该模型只用于验证协议。业务模型、检索系统和生产模型网关未参加本次选型。 |

## 复用、自研和未来修改面

| 项目 | 路线 A | 路线 B |
|---|---|---|
| 直接运行的现成代码 | P2 Catalog、两级数据库角色、Service 提交/执行/有权取回收据、契约指纹、原迁移；LangGraph StateGraph、Temporal Python SDK | Pydantic AI 的 Agent、Tool.from_schema、OpenAIChatModel、OpenAIProvider 和请求上限；Temporal Python SDK；Pydantic 严格输入输出 |
| 自行补充的主要部分 | 动态图和模型/工具授权出口；P2 原来没有的父级预留账本、质量判定、父子业务恢复。实验另外实现了供应商处理，原 P2 供应商核心不能计作本轮 V04 的直接复用。 | 发布/授权与租户身份、证据引用、产品状态、幂等收据、质量判定与父子额度均需独立实现。模型和工具各有一个治理适配点。 |
| 源码改动实测 | 路线专用运行/工作流两个 Python 文件共新增 341 行。指定 P2 的 core/ 内变更 0 行；通过替换入口完成改造，原 Agent 执行机制已退出测试路径。 | 两个对应文件共新增 295 行，另有独立镜像定义、直接依赖声明与 32 项 AMD64 哈希锁。没有导入 P2。 |
| 框架侵入与服务 | 两路对 Temporal、LangGraph、Pydantic AI 等上游源码的修改均为 0。A 显式维护模型消息配对和图边。 | 通过公开模型请求方法设置授权，工具描述转换成原生 Tool。两套框架 API 升级后，上述接口需回归。 |
| 运维责任 | API/Worker、PostgreSQL、Temporal 和模型端。P2 还带原迁移、合同指纹、双数据库角色等现成治理。 | 同类运行服务，没有因采用 B 省掉数据库、工作流服务或模型。独立供应商、见证库和故障注入器是实验夹具。 |
| 下一种能力的修改面 | 在本轮可表达的外部工具协议中，只增加实现并注册。新增长回调或流式执行类型时，需核对原 Capability.kind、恢复和交付边界。 | 在同一工具契约范围只注册能力。新增流式工具、有副作用且无法查单的服务或不同价格模型时，执行适配、可信回执和预算模型需要重新验证。 |

行数由同一基线的 git diff --numstat 得出，包含实验用代码与格式，不计共同测试代码、锁文件和框架自带代码。它只说明本次落在哪里；未测人天、开发成本、300 人负载以及长期运维费用。初次接入与解封后的修改分别归档。[A 的实现](a/runtime.py) · [B 的实现](b/runtime.py) · [文件级差异和接入记录](evidence/changes.txt) · [两路关键代码补丁](evidence/runtimes.patch)

**P2 取舍。** 退出通用执行核心、固定 append_note 选择器和只为其服务的图。保留可独立复用的契约样例、授权/发布负例、回执与查单故障用例、迁移测试和隔离基础设施作为回归资产。A 已证明部分 Catalog/Service 机制能工作；将来即使借鉴它们，进入 B 也要走独立适配和同场回归。原 P2 以租户为单位的预算池不能直接承担父任务额度。跨租户权限生命周期、产品审计、多环境发布也是 B 需要继续承担的产品责任。

## 候选范围与调查校正

三份调研和 v0.4.1 的原文摘要哈希见附录。基线同提交 P2 CI 为 32 项通过，原图 choose_note_tool 固定选择 append_note，Service.start_execution 又对该名字做判断；以两工具多轮动态决策为验收时，既有 P2 通过数不能代替同场结果。Temporal 官方 LangGraph 插件确有发布版本，Pydantic AI 也提供 TemporalDurability 与 PydanticAIPlugin。两路实验都将模型循环放在受控 Activity 内，本轮没有验证逐模型轮次崩溃后的原位恢复，也未把 Pydantic 原生持久化插件的恢复粒度计入 B 的收益。[基线 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/44683410513/job/136111930837) · [P2 固定图](https://github.com/zhuquanwei111/mingjing---agent/blob/fdf04240eba747a9a681a1dad627da22d4b89cdd/core/src/mingjing/temporal_adapter.py) · [Pydantic AI 固定版](https://github.com/pydantic/pydantic-ai/tree/v2.71.0/pydantic_ai_slim/pydantic_ai/durable_exec/temporal) · [LangGraph 官方集成](https://github.com/temporalio/ai-integrations/tree/python/langgraph/v1.0.0/python/langgraph)

| 未进入本次双路线运行 | 实际起点与选择取舍 |
|---|---|
| Dapr + Dapr Agents | v1.1.1 的 DurableAgent、call_agent、工作流与 sidecar 有现成代码，适合需要多语言服务调用和状态组件的系统。换调度器还需要验证工作流状态存储、部署控制组件、取消与账本语义。本次固定引擎，未作跨引擎优劣结论。[官方样例](https://github.com/dapr/dapr-agents/tree/v1.1.1/quickstarts) |
| Windmill | 可直接复用脚本、Job API、Worker 与运维界面。需验证脚本出站能否统一受控、任务状态能否与业务回执和预算对应；实际部署和许可条件未做实测。[固定版本](https://github.com/windmill-labs/windmill/tree/v1.882.0) |
| Dify | 有完整 Web、知识与 Agent 工作流，直接复用产品功能的机会较多。自托管需持续维护 API、Worker、数据库、Redis、插件等；同场权限、幂等、质量和预算均为未知。[仓库及许可](https://github.com/langgenius/dify) |

## 复跑、失败与边界

使用两台可丢弃 Linux AMD64 runner。Docker/Compose、外部只读镜像下载、持久卷和内部网络须可用。Python 3.12.16、PostgreSQL 17.12、Temporal Server 1.32.2、Temporal SDK 1.36.1；A 使用 LangGraph 1.2.22，B 使用 Pydantic AI Slim 2.71.0。[基础镜像摘要](../../core/infra/compose.yaml) · [A 的 52 项锁](../../core/requirements/linux-x86_64.lock) · [B 的 32 项锁](b/linux-amd64.lock) · [推理镜像和权重摘要](model.sh)

最简单的复核是打开最终云端作业，两个独立 job 已在相同检出版本依次执行了以下命令。自行复跑时，从同一实验提交创建两个独立检出，分别运行对应的一行。需提供相同的 GITHUB_SHA 与数字 GITHUB_RUN_ID，以及各自可写的 RUNNER_TEMP，固定同一次复核的挑战和只读探针身份。A/B 实际应用凭据独立随机生成。

```bash
bash lab/architecture/run.sh a
bash lab/architecture/run.sh b
```

- 第一轮两路的数据库/引擎数据均可在容器替换后读回，但在数据库自身回环地址进行的错密码测试意外成功。日志保留失败，后续通过独立客户端、SCRAM 和两路交叉身份重新检查。[最初失败](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45126744264) · [预检复测](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45127044505)
- 首轮功能作业均为绿色，复查发现未知回执保留额度等子断言覆盖不足，仅作初次实验记录。加强版使用真正的父子取消、原生 Agent 出站撤权、外部能力实现、质量服务不可用与账本变化记录。中间提交另有源文件尾空行导致仓库 make check 失败；该处修复后，原仓库三项回归均通过。随后把未知能力的模型说明从“返回规范 JSON”更正为“返回回执标识”，并用只描述业务目标的提示词复测两路。[初次功能作业](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45128217583) · [加强复测](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45129036196) · [中间仓库检查失败](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45129036180) · [跨租户及证据引用复测](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45130185846) · [对应仓库回归](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45130185871) · [最终仓库回归](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45131052141)
- 所有故障针对合成系统指定的注入点。未验证任意指令位置的 exactly-once、生产容量、高可用、计费、供应商不可逆操作、不同外部协议以及完整 v0.4.1 的全部非功能条款。数据库事务中的外部 I/O 会延长持锁时间；并发容量与撤权延迟须在目标负载测量。实验中的 B 部署和单一测试租户集合也未覆盖 P2 的全部产品治理。本次未取得独立代码评审签字。

最终 `make check` 核对了 49 个 Python 文件。P2 AMD64 为 32 项通过，P1 的 ARM64 验收和 AMD64 辅助回归各为 16 项加 2 项通过。完整日志随实验账本归档。

全部改动位于公开实验分支。草稿 PR 的目标是固定基线的另一个实验分支。本轮实验没有写入或合并 main，也没有调用生产环境。交付时本地 main 仍指向指定基线，远端跟踪引用已包含独立的配置 PR #3（fcc5e47）。实验按原 SHA 完成对照。[隔离实验 PR](https://github.com/zhuquanwei111/mingjing---agent/pull/5) · [输入文件指纹](evidence/inputs.json)

