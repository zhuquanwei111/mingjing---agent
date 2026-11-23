# 原生队列与证据边界

依据独立事前复核，选择 Agno v3.2.0 AgentOS 原生 QueueConfig(durable=True) 与 PostgreSQL。初始受理和 /continue 均用 background=true,stream=false，读回同一 run 的 PAUSED 和终态，在队列表核对同一个 ticket。原工作进程与 AgentOS 服务均真实退出，新进程必须通过 HTTP 重新读取 pending requirement。对比队列票据、框架会话、产品操作账和独立模型请求内两个合成标记及调用号，若队列留有受限正文，原样登记为载荷边界缺口，不更换标准。直接和固定工作流入口使用同一个受治理工具提交函数，分别观测是否触发模型和独立业务效果。工作流测试只考察入口复用，不用于外推工作流跨故障恢复。固定模拟模型用于协议而非业务推理质量。
