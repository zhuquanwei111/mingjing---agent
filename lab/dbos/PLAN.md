# DBOS 单一调度器候选 · 事前判据

基线为 #5 bb55c843b8dd2e9ad646e982a38cda350b3df952。沿用 #12 [f5b4df8 的判据](https://github.com/zhuquanwei111/mingjing---agent/blob/f5b4df8f70e3033e52fc8a8906f8f13eeb29b2b1/lab/product-review/PLAN.md) 与 9094630 的独立 HTTP 收端。产品流程和引擎实现另写，不导入 B 的调度器、账本、循环或分派器。范围只含改变调度器去留的动态工具中断切片。单个受控模型和模拟费用；不在生产执行。

## 候选与可证伪假设

[DBOS Transact Python 3.6.0](https://github.com/dbos-inc/dbos-transact-py/releases/tag/3.6.0) 是 MIT 程序库，以 PostgreSQL 保存已完成步骤；选它检验复用产品 PG、移去独立调度服务器的可能。[Restate](https://github.com/restatedev/restate) 的 SDK、持久日志与工作流提供另一条公开恢复路径，但在保留产品 PG 的配置中还需运营 Restate Server。[服务端许可证](https://github.com/restatedev/restate/blob/main/LICENSE) 为 BSL 1.1，涉及 Public Restate Platform Service 的限制；现有信息并不排除内部自托管。本轮没有运行 Restate。

固定 [运行与恢复接口](https://github.com/dbos-inc/dbos-transact-py/blob/3.6.0/dbos/_dbos.py)、[外部调用接口](https://github.com/dbos-inc/dbos-transact-py/blob/3.6.0/dbos/_client.py)、[序列化](https://github.com/dbos-inc/dbos-transact-py/blob/3.6.0/dbos/_serialization.py)。检验 DBOS 公开启动/恢复、持久步骤、去重消息、取消，不开启 Conductor 或付费 suspend。独立受控端保存请求、真实效果与每次发送的模拟费。协议模型动态给出工具名对应调用及唯一 ID，原始响应和回执由产品侧保存，SDK 仅记引用及状态。公开 API 支持报告从引擎原始记录与业务记录独立复核，不能以 SQL 手工改引擎状态代替恢复。若不能观察同一 ID 的引擎重入或不能安全配对，则该项失败。

## 事前用例

在初轮真实 HTTP 请求、202 受理、后台提交效果和一笔费用、工具结果及终局均空后强杀工作 PID。第二个进程恢复同一 workflow ID。分开统计实际 HTTP 工具发送、效果、按到达次数收费、模型请求、交付。保留两个进程身份、引擎检查点、业务账状态和独立接收方逐笔请求。

| 条件 | 判定 |
| --- | --- |
| 原生负对照 | 只用裸 durable step 直接发送，请求成功后、步骤未提交时杀进程。观察恢复后是否重复发送和模拟收费，即使业务效果唯一。裸工作流入参/输出放独有标记作为序列化扫描阳性。不得将失败归咎于收端去重。 |
| 已知、兼容、有权 | 工具/效果/费/交付各 1，模型 2，次轮收到与首次随机 call ID 匹配的真实收据。重复通知不改变计数。 |
| 暂不可查 | 同前首 3 项各 1，模型 1、交付 0，held=3/spent=0。引擎、产品状态和两次独立读回能定位待核。实际失联后恢复，不补发。 |
| 取消及迟到 | 记录上项数据后提交取消并用引擎公开取消；恢复可信查询后至少两次核对，held=0/spent=1，工具/费/模型/交付均无新增，取消的工作流不再推进。 |
| 旧版本不兼容 | 识别产品轮次版本，旧检查点保留；可信结果可结算，不发起新模型/工具/交付。不同进程使用不同读版本配置；不推导 SDK 版本迁移。 |
| 错配负例 | 对回执插入错误 call ID，必须在产品入口或 SDK 配对时拒绝，模型 1、交付 0。 |
| 引擎内容 | 扫描真实引擎所有表及解码参数/输出，核原始工具 ID、两种业务标记只见于产品/收端；含裸对照标记的引擎行必须命中。 |
  
若裸步骤失败而带持久发送意图、查单、保留预算与取消交付屏障的组合通过，则仅组合通过。分列嵌入式引擎能力、自有治理/两轮消息桥、独立收端、核心服务数。同步等候的工作线程容量、部署版本路由、真正付费供方和多出口真实授权均不由此实验作结论。改判条件包括原文进引擎、重复请求/费用、取消后续跑、未知结果失留。先公示本计划与独立审查，再实现，保留修正与失败轨迹。