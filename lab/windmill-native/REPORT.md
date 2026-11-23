# Windmill CE 原生 Agent 同题对照

此堆叠草稿基于 #5 的固定提交 bb55c843，与 #12 使用同一组可观测条件。[事前协议](PROTOCOL.md)先于代码提交。本文只记录完整应用在这一条跨进程异步能力上的证据，完整产品选型由独立复审决定。

## 实际边界和成本

|层|本次使用及新增工作|
|---|---|
|Windmill CE 原生|真实 PostgreSQL、Server、独立 Worker，公开 API 部署 2 个版本化 Bun 脚本和 1 个 Flow。通过路径运行，不用 preview。原生 aiagent 动态发起工具调用，requires_approval 在执行前保存调用号、消息和动作；公开批准端点恢复同一 Agent job。重拉由原生 zombie monitor 完成。原生工作流安排后续交付步骤。|
|产品出站|单个合成可信域的 HTTP 代理在实际模型发送前查取消、版本、操作和调用关系。为一次有副作用模型请求预先持久认领，再次检查后在同一域的锁内交给外端。在未知声明上拒绝后续发送。流式协议桥将供应商一次调用的真实 ID 与引擎可保存的随机引用双向映射。真实跨域 IAM、协议格式多样性另需验证。|
|能力与交付|工具脚本接收固定操作引用，产品账原子认领后才向独立提供方发送。重复脚本进入按原操作查单。独立后台进程在控制器释放后完成受理任务并提交唯一回执与一笔模拟费。正式出口要求原终局结果绑定本次回执、版本可读且产品未取消。|
|可复核规模|以最终代码的 wc -l 计，工具脚本 17 行、交付脚本 5 行、受控模型接口 113 行。services.py 的 233 行同时含 HTTP/SQLite、产品账、协议模型、假提供方和异步完成进程，product_action 位于 180–210 行；最终含取消独立挑战的故障控制与断言 375 行、启动 25 行、CI 23 行。测试代码和产品适配职责混在同一实验装置，不能将合计当成长期自研行数，也不能同 #5 的 295 行直接比。|
|接入与未验成本|原生 Agent 循环及调度均未改源码，登记依赖两个公开脚本保存接口和一个 flow 保存接口。业务适配器、稳定 operation、确认/保留额度与取消后对账、模型代理、维护审批协调仍由产品承担。本次未冻结通用注册核心后再盲接第二个未知能力，未验证 AC-17；没有开发人日或生产成本比较。|

## 运行条件

- 固定源码/OCI revision 均为 28985a122cc303200bb36c5c67037f5f2157299c。运行时公开版本接口返回 CE v1.882.0，镜像索引为 ghcr.io/windmill-labs/windmill@sha256:c5d60c73d12ed2839a8598edfcbe29f13eb1062b8e2e7e8112b985b0fb24ebc8。PG 采用项目已锁定的 sha256:526f86d93c6ea08fd3f1fe5605650cacc781b2c6013169a0ad8f42c7d3d84f32。自管实验仅调用部署 API 与非付费本地协议服务。[镜像/版本预检](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45190305078)
- 固定源码分别标明无 enterprise 编译的二进制与预构建 CE 镜像的授权。后者含非公开代码，明示内部使用/API 按原样使用的条件，并对商业嵌入、包装、转售等另列条款。本实验按原样运行 CE 和 API。正式发行形态仍需根据实际用途核对。[固定版 LICENSE](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/LICENSE)
- 独立 Linux runner 从仓库执行 bash lab/windmill-native/run.sh 即重建。工具和模型侧信号、产品账各在不同进程，且与 Windmill PostgreSQL 分开。控制器用只读 PG 定位待批 job，调用公开 resume API；操作账或原生服务未通过测试 SQL 代为推进。真实前端从公开查询自行发现待批记录、真实用户授权流程均尚未串联。[上游公开批准测试](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/tests/ai_agent_approval.rs)
- 未改写的匿名开关可用 WMN_ALIAS_CALL_ID=0 复跑当前对照。历史无代理直连以 f246ea90 或 ba8d24cb 各自原始代码重跑。各版本实验间可以弃用独立分支；没有更改 main、生产或启动 W0/MVP。

## 原生直连、批准与后台模式

两个真实直连实验均复现同一差异。原生已知恢复让同一 Agent job 经新 Worker 从 checkpoint 读入原调用，允许为本次调用再开工具子 job，同时老子 job 自己也可能重拉；单次外部发送来自产品账原子认领。取消时原生父/子均能结束为 canceled。原生 Agent 仍可能将“工具已取消”作为原 call ID 上的工具错误交给模型。两轮各见模型 2 次、交付 0。需要在产品最终模型出口核验取消状态。[直连原始计数](direct-observations.json) · [首轮完整日志](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45190773511/job/137748198935) · [严格配对复验](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45191055874/job/137749191595)

公开后台工具的原生行为与本实验的前台脚本不同。background=true 先把启动 job_id 作为与工具 ID 对应的消息回复，真实结果可在后续 user 消息中抵达，该设计可能在真实结果之前再调用模型。此处以源码为据，未将后台变体算作运行通过。本次选原生批准前 checkpoint，审批协调是实际接入成本。[原生工具](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/windmill-worker/src/ai/tools.rs#L370-L525) · [恢复逻辑](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/windmill-worker/src/ai_executor.rs#L1955-L1971)


## 受控模型代理的实际结果

代码 9cc96af7 使用独立异步完成进程。产品、接收端和提供方后台 worker 的 PID 均已记入原始观测。下表“模型”只数受控最终边界后的模拟供应商原始 HTTP 入站，网关入站另计；工具/模型两种模拟费分表记录。[逐事件与全部作业谱系](guarded-observations.json) · [最终主样本原始 SQLite、模型与 Worker 日志](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45192349465/artifacts/14826008810) · [完整 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45192349465/job/137753692529)

|工况|工具 POST / 效果 / 工具费|模型 / 交付|持久证据|
|---|---|---|---|
|无中断|1 / 1 / 1|2 / 1|两轮和可信回执配对，root success。|
|效果、费用已落后强杀，有权可查|1 / 1 / 1|2 / 1|工具脚本共进 3 次，原生 Agent 同 job、重排计数 1。进入产品网关的 assistant/tool ID 均为匿名 A；最终供应商实际接收的两字段均为其首轮生成的 C。|
|真实重入时结果暂不可查|1 / 1 / 1|1 / 0|持有 3、核销 0，替换 Worker 上再次查单未知。|
|真实取消和两次迟到确认|1 / 1 / 1|1 / 0|原生 root canceled、持有 0、核销 1。9cc96af7 这一次网关共见 1 个入站，额外拒绝数为 0。两次无代理样本均收到了第二次出站，单次阴性不能推断原生每次都会停。|
|不兼容 reader|1 / 1 / 1|1 / 0|可信回执仍核费，reader=2 / 旧版本=1 的任务隔离。原生 checkpoint 和重启前逐字段相等，保留任务与工具调用关系。|
|已知完成后注入错误调用 ID|1 / 1 / 1|2 / 1|在此前已交付的一次样本上回送不匹配 ID，网关新增一次拒绝，正式交付、工具和供应商模型均零新增。|

在全部相关工况中的多个时间点扫描 Windmill 的 192 张 public 表。两个私有正文标记及上游原 ID 零命中；随机匿名引用在活跃 checkpoint、resume_job、v2_job_status、终局作业结果中可见。对照提交 c93fbbf4 未启用 ID 转换，原始 ID 确实进入相同引擎记录。该提交后续错误输入已获得 403，但夹具打印异常状态时抛 AttributeError，修正为标准库 get_method 后单独复跑，不能把该次错误当全部用例通过。[原 ID 入引擎的对照](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45191743737/job/137751582802) · [匿名引用完整首个复验](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45192050612/job/137752660293)

|模型收费故障|网关尝试 / 拒绝|模型提供方 HTTP / 模拟费|覆盖范围|
|---|---|---|---|
|已经计费再 503，允许隐式重试|4 / 0|4 / 4|原生最多重试 3 次，各尝试独立计费。|
|已经计费再 503，下游明确禁止重试|1 / 0|1 / 1|提供方实际给 x-should-retry:false，代理透传。|
|已计费即断 TCP，无派发声明|4 / 0|4 / 4|仍经过转发进程，故障前没有返回头。|
|已计费即断 TCP，产品先认领本轮|2 / 1|1 / 1|第二次 Windmill 请求到达代理，已有持久 unknown，本轮没有再次发到提供方，后续交付为 0。|

[原生重试源码](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/windmill-ai/src/retry.rs) · [TCP 对照独立复验](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45192181467)

以上结果确认 Windmill 是这道代表性产品题上可复用的完整应用候选。默认行为没有满足全部约束；实测适配的主要责任已列于上表。没有足够跨业务、真实宿主与长期成本证据在两个全产品方案间确定赢家。真实 IAM、受理/启动一致性、业务终核与交付方互信、发行方式和部署权责需真实宿主。多工具、多轮或更高负载可先单独验证。

## 产品约束

- 异步工具的未知状态保留一笔 3 单位工具预留；本实验未测多资源并发父预算。模型 TCP 丢响应的持久声明独立于工具预留，不能据此称已经实现统一模型/工具计费结算。保护请求在已宣布发送但尚未实际移交、或可信结果尚未交回时会进入待核。样例没有供应商查单、结果缓存回放或无限循环的通用调用序号。
- 当前模型协议仅覆盖受控的两个模型轮次、一个 function call、完整 SSE 模拟帧。保护表 (operation, turn) 中 turn 仅有首轮/含工具结果两种取值。多个工具、额外轮次、分片 ID、模型切换和流式取消需要版本化映射与计量。受控协议模型验证接口，不验证业务质量。
- 旧版本是同二进制上切换产品读取规则。被隔离的任务仍持有轮询工具 Worker；没有证据证明无限期待核的资源成本或真实引擎滚动升级。PG public 全表 COPY 文本逐行查随机字母数字值，另以真实引擎记录中的内部调用引用作阳性。压缩、二进制、日志与外部对象/检索系统未全覆盖。
- 权限排序只覆盖受控产品网关对实际提供方的第一次模拟传输与本地合成接收端。对于产品内部受信的网关可以看到 Windmill 的已取消尝试和合成错误。实验未为跨组织、真实业务 IAM、第三方脚本、持有凭据的任意网络或生产服务划定授权。此例没有验证注册目录三入口治理、无进展、完整多租户、质量契约或目标容量。

## 独立审查与复查入口

独立只读评审在事前协议后提出前台/后台区分、批准 checkpoint 候选、按实际 Worker 归属定位强杀、结构化校验各条模型消息、未知重入与旧子 job 竞争、取消错误外发计数，并复核最终 9cc96af7 的已完成 CI 全部八案。控制器与模板经过修正后重跑；独立复核得到原始账、引擎关系及两次未经保护失败一致。主场 CI 上传制品 SHA256 为 d70c51ddb6e09407cf1c0a31c6d83f77ae7dbb8602cc1c7ee36cc0976da8fda6。原始故障来自实际效果/费提交且工具结果在引擎与产品为空的瞬间，退出码 137。

另外的取消注入使用固定提交 18f2a70f。其控制器先观察已取消的真实 root 与产品结算，再注入正确的同一调用及回执。原生是否自行续发与该控制负例分开计数。结果由同名 CI 的 injected_cancel_denial 和原始工况 final 两条记录分别给出。[取消注入的固定代码](https://github.com/zhuquanwei111/mingjing---agent/blob/18f2a70fd71194bee34cd03b0bd419d59694355a/lab/windmill-native/harness.py) · [针对性完整 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45192950281)
