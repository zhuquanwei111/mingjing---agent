# Agno AgentOS 工具回合对照

Agno 3.2.0 的原生 PostgreSQL 队列、AgentOS HTTP、持久运行和外部工具在七个合成场景中承载了同一回合的持久等待。已知、有权时，新进程核对独立收端的效果与收费，并把同一工具的真实回执送到下一次模型请求。外部发送意图、未知时保留额度、权威查单、按当前权限传输及交付由产品适配承担。[精确 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193822010) · [受审代码](https://github.com/zhuquanwei111/mingjing---agent/commit/b1f1500c5f9a9e7354ea80db8f32bde332b01f95) · [逐笔证据](evidence/45193822010/raw.jsonl) · [文件校验](evidence/45193822010/SHA256SUMS)

| 独立场景 | 工具发 | 效果 | 模拟费 | 模型请求 | 交付 | 预算持留 / 核销 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 已知、有权，原生默认载荷 | 1 | 1 | 1 | 2 | 1 | 0 / 1 |
| 暂不可查，重复核对 | 1 | 1 | 1 | 1 | 0 | 3 / 0 |
| 取消后迟到，重复核对 | 1 | 1 | 1 | 1 | 0 | 0 / 1 |
| 初代写入的数据版本不兼容 | 1 | 1 | 1 | 1 | 0 | 0 / 1 |
| 通知工具号错误 | 1 | 1 | 1 | 1 | 0 | 3 / 0 |
| 权限撤回，尝试实际模型出口 | 1 | 1 | 1 | 1 | 0 | 0 / 1 |
| 已知、有权，受控引用 | 1 | 1 | 1 | 2 | 1 | 0 / 1 |
| 确定性 HTTP 与固定工作流，各自 | 1 | 1 | 1 | 0 | 0 | 仅测相同提交能力 |

两个独立 PostgreSQL 实例分别记录产品状态与实际接收。旧 AgentOS PID 2667、派发 PID 2783 真实遭 SIGKILL，退出状态均为 -9，新 AgentOS PID 3025。中断发生在独立服务返回 202 并已实际产生效果、费用，产品还未保存工具结果时。新进程从 HTTP 读到同一 session、run、pending requirement。已知有权的两个样本均在同一个原生 ticket 上完成第二轮。取消样本的原生运行与票据均为 cancelled，已发生的费用仍在。未知、版本不兼容、错配、撤权的原生运行保持 paused，产品状态分别保留其原因。

## 原生载荷和受控引用

默认样本完成时，调度票据、框架运行表与带服务授权的 HTTP run 读回均包含原始工具参数、业务回执和模型调用号；会话元数据表未出现这三个标记。引用样本让平台使用一个与真实模型工具号不同的随机代理调用号，并将初始输入、参数、收据和最终答案换为受控标签。受控模型及业务出口按合成范围与用途解析，独立业务收端和第二轮模型均收到同一个真实原号及权威回执。在旧进程暂停和新进程完成两个时点，原生队列表、运行表、会话表和 HTTP run 的三个原始标记均零命中。受权产品引用表与实际模型请求供交叉验证。完整的产品原值和关联事实仍由产品自己的受限数据表保留。[默认票据](evidence/45193822010/known-completed-queue.json) · [引用票据](evidence/45193822010/reference-completed-queue.json) · [实际模型请求](evidence/45193822010/reference-completed-wire.json)

引用适配器含 70 行 Python，服务与 API 装配 67 行、模型网关入口 21 行、操作账与派发恢复 161 行，四个文件共 319 行，包括实验接线。控制和观测 268 行，另复用 #12 的中立接收方 115 行。65 项 Python 发行包固定版本，归档保留安装用 wheel 摘要。没有修改 Agno 上游。多工具形状、流式与多模态、其他模型 API 的兼容和运维成本未计入。原生责任和自有责任的分界不能按实验行数折算长期人天。

首次引用对照采用通用 opaque 前缀，固定版本的 OpenAIChat 重整了工具号，网关因绑定不符拒绝向实际模型发送。将代理工具号改为模型适配器接受的 call_ 前缀加独立随机值后，全部强断言通过。[首次失败日志](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193536995) · [固定上游格式化代码](https://github.com/agno-agi/agno/blob/3bfc84113fdd80c1522ef7bafa80721ce79fdf62/libs/agno/agno/models/openai/chat.py#L384)

## 适用边界

- 固定版本使用合成服务凭据和单个合成范围，尚需实际宿主、真实主体/租户、可撤回资料、五类实际出口及各个资源服务的自主终核。受控引用只在一个工具契约和 OpenAI Chat 的已知分支做了原始载荷核查。尚无适配后全矩阵、日志全覆盖或所有业务模型的结果。
- 共享预算本次仅测单操作持留 3／核销 1。跨子任务并发、其他资源计量与真实账户费用未测。运行已写 continuing 后、继续请求尚未被接收，以及交付已生效但产品尚未落账的其他中断窗口未测。样例在未解决时保留 continuing。进一步恢复取决于继续受理和交付侧的可靠核查。
- 工具回合已进入持久等待才强杀。没有观察运行中的模型任务因 lease 到期重投。直接和工作流只证明在有权时可共用提交入口，不包括迟到回调、全程恢复或重复受理。版本样本使用首代持久数据的版本标记，未实际滚动升级两个 SDK 版本。
- 使用真实 SDK 对接可观测的合成模型协议。真实模型质量、真实服务权限、供应商账单、混合负载容量、灾备、灰度或上线均没有本项目证据。Agno 的公开用户实践仅用于评估成熟度。[Key Data Dashboard](https://www.agno.com/blog/scaling-ai-not-complexity-how-key-data-dashboard-integrated-agent-intelligence-without-slowing-down)

固定上游 3bfc84113fdd80c1522ef7bafa80721ce79fdf62 的根许可为 Apache-2.0。该实验以 Agno 原生队列和外部工具实现后台等待，无需另行部署 Temporal。对已完成运行再次普通 continue 可能创建后续分支，重复回调由产品操作状态阻止。受理和继续均使用公开 AgentOS HTTP 的 background=true 和 stream=false。[固定许可](https://github.com/agno-agi/agno/blob/3bfc84113fdd80c1522ef7bafa80721ce79fdf62/LICENSE) · [外部工具暂停](https://github.com/agno-agi/agno/blob/3bfc84113fdd80c1522ef7bafa80721ce79fdf62/libs/agno/agno/models/base.py#L2562) · [结果配对](https://github.com/agno-agi/agno/blob/3bfc84113fdd80c1522ef7bafa80721ce79fdf62/libs/agno/agno/agent/_tools.py#L748) · [原生队列继续](https://github.com/agno-agi/agno/blob/3bfc84113fdd80c1522ef7bafa80721ce79fdf62/libs/agno/agno/os/routers/agents/router.py#L1687)
