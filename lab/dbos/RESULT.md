# DBOS 与 PostgreSQL 的工具回合恢复结果

**产品选择。** 在本次受控异步工具、单笔预留、旧格式读回和同一 SDK 的范围内，更换成嵌入进 Python 工作进程的 DBOS 后可以除去单独部署的 Temporal Server。产品账和引擎库在同一个 PostgreSQL 实例中分库、分角色。独立见证方用另一数据库实例，仅用于实验。这个选择没有移走长期的业务开发责任：发出前的意图、按操作号查单、预算保留/结算、迟到时关闭交付、工具回合消息版本和业务终局都由应用侧维护。

## 结果

所有模型请求均进入真实 HTTP 协议接收器，返回一次真实生成的随机工具调用。两轮由 Pydantic AI 2.71.0 的公开 Agent.run/deferred/message-history 接口执行。正式外部供应商、真实价格、App 权限均未参与。计费夹具对每次实际到达记一笔，效果按稳定 operation 去重，刻意区分“执行效果一次”和“收费一次”。每个标准样本均在独立接收端效果与费用已提交、业务结果与 DBOS 第 2 步尚未提交时强杀进程。

| 路径 | 发送 | 效果 | 模拟收费 | 模型请求 | 交付 | 最终观测 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 裸 DBOS step | 2 | 1 | 2 | 1 | 0 | 同一步被另一 PID 重新执行，两次到达使用相同 operation 与 call |
| 带产品账，已知且有权 | 1 | 1 | 1 | 2 | 1 | 两次相同通知；新 SDK run 沿用 conversation，第二轮返还原调用 ID 与独立收据 |
| 仍不可查 | 1 | 1 | 1 | 1 | 0 | 又一次强杀、重启及真实不可查通知后仍 PENDING；held=3/spent=0 |
| 取消与两次迟到结算 | 1 | 1 | 1 | 1 | 0 | 在 PENDING 调用 DBOSClient.cancel_workflow；两个通知各实际执行，第一次结算，第二次无增量；held=0/spent=1 |
| 旧 v0 不兼容 | 1 | 1 | 1 | 1 | 0 | 保留旧的数组检查点，可信费已核销，产品 quarantine |
| 错误调用 ID | 1 | 1 | 1 | 1 | 0 | SDK 拒绝配对，第二轮未出站，可信费已核销 |

在已知正例，旧进程实际写 v1 格式，新进程支持读 v1/v2；故意拒绝的 v0 由旧进程另行编码。同一 SDK 和同一引擎 application_version，实验只覆盖产品检查点兼容。运行原始 PG 行含默认 pickle/base64；裸对照输入、输出均携带特有标记，以公开 API 解码可读。五条受控轨迹的 15 个提示标记、真实工具 ID 和业务回执没有出现在扫描的 14 张 DBOS 表或公开解码记录，合成原文在产品或接收端可核。它们在引擎外仍需权限、保留和脱敏政策。

## 服务与责任

| 项目 | 官方供给或观测 | 维护者持有的责任 |
| --- | --- | --- |
| 本样本的部署 | 一个 PG 服务 + 工作进程，DBOS 嵌入工作进程；基准 B 为 PG + Temporal Server + 工作进程。收端见证与控制器另计 | 同一个 PG 的容量、数据库内资源争用、备份、分角色还原，工作进程生命管理 |
| 稳定 ID 的进程重启 | 3.6.0 DBOS.launch 自动重入本 executor、同 application_version 的未完成 workflow；已完成 prepare 可回放，未完成 send_job 再执行 | 确保身份稳定和旧版有可用执行进程；受限数据用引用，权威回执在业务 DB |
| 分布式接管与长等待 | 下表是在线备用的实测。公开 recover_workflows 可显式重新入队。普通 recv 为持久消息等待；无需商业授权即可执行本实验 | 探测宿主失效、避免误判、轮换与告警。官方 Conductor 提供自动探测与跨 executor 恢复；suspend=True 释放长等待工作线程属 Transact Enterprise。本轮未启用两者 |
| Agent 与应用治理 | Pydantic AI 提供延迟工具调用及验证。不依赖 Temporal 的执行内核；DBOS 提供恢复、状态、消息、取消。原生 DBOSDurability 也有公开集成 | 本方案自编引用、历史、意图、查证与结算适配。固定的上游集成会将模型请求放入 DBOS step，自定义普通工具不保证自动包裹；本轮没有将它登记为通过了原文隔离或外部费用幂等的实现 |
| 安全边界 | 实验出站限合成接收协议，模型客户端禁隐式重试；动作与交付由业务账作决定 | 工具发送意图已记且实际尚未送达时安全保留待核。模型/交付自己的不确定提交窗口、撤权与交接排序、多出口和生产 IAM 仍需独立措施，本实验只中断工具发送步骤 |

[DBOS 固定 SDK、MIT 许可证](https://github.com/dbos-inc/dbos-transact-py/tree/2cf279cf380152b426ecd451d573ccc41f5715a6) · [官方接管路径](https://docs.dbos.dev/production/workflow-recovery) · [Enterprise 的适用范围](https://docs.dbos.dev/explanations/transact-enterprise) · [Pydantic AI 2.71.0 固定集成](https://github.com/pydantic/pydantic-ai/blob/v2.71.0/docs/durable_execution/dbos.md)

Restate v1.8.1 有单机可运行的独立服务端、SDK 和持久日志。保留产品 PG 时，该部署还需单独维护 Restate 的状态与升级。服务端采用 BSL 1.1，追加授权限制 Public Restate Platform Service，内部自托管须按实际用途对照条款。本轮只做官方路径对照，未对 Restate 运行同题用例。[固定发行版](https://github.com/restatedev/restate/releases/tag/v1.8.1) · [固定许可证](https://github.com/restatedev/restate/blob/v1.8.1/LICENSE)

Python 依赖有 36 条仅适用于 Linux x86-64 / CPython 3.12 的散列锁。DBOS 与 Pydantic AI 为 MIT，PostgreSQL 17.12 为 PostgreSQL License。实际安装的许可元数据逐项随证据归档，包括 psycopg 与二进制驱动的 LGPL-3.0-only、certifi 的 MPL-2.0；再发行还需按具体包装核对通知和义务。没有测量长期人天、总体拥有成本、同规模吞吐或实际业务模型质量。[PostgreSQL 许可](https://www.postgresql.org/about/licence/)

## 判据与复跑

先冻结 [标准六例](PLAN.md) 和[不同执行器接管](TAKEOVER-PLAN.md)，再实现。[独立审查、修订与失败](REVIEW.md)。在临时 Linux x86-64、Python 3.12 与 Docker 实例上，从对应 Git 根目录执行以下命令。创建的两个 PG 容器和凭据只存在于实验期间。夹具要求空闲的本机 8080 端口与 /tmp/dbos-env。

```sh
LAB_OUT="$(mktemp -d)" TEST_HEAD="$(git rev-parse HEAD)" CI_RUN=local bash lab/dbos/run.sh
```

## 已在线的另一执行器

两例的 B 在故障或误报前均已启动。B 没有运行探测器；控制器等待期间使用单调时钟并在两个数据库采样。A 与 B 使用不同 executor ID，连接同一引擎 PG。显式命令在已就绪的 B 进程中执行。

| 情形 | 显式命令之前 | 公开 recover_workflows 返回与真实执行方 | 发送/效果/模拟收费/模型/交付 |
| --- | --- | --- | --- |
| A 已 SIGKILL，exit=-9 | 8.079 秒、26 次采样均指向 A 的原 PENDING、第 2 步与一次发送；B 存活 | 返回原 run-takeover；步骤从 PID 3995 转到 B 的 PID 4059，B 为终态 owner；第二轮恢复原工具调用和会话 | 1/1/1/2/1 |
| 错判仍存活的 A，裸步骤 | 8.109 秒、26 次采样中 A/B 均存活，A 持有原 PENDING | B 的公开命令返回原 run-false_recovery。重新入队的步骤被原 A 的 PID 4299 再次取得，导致 A 以相同 operation 再发。收端的两条 accepted 对应同一 PID；B 的 PID 4362 持续在线 | 2/1/2/1/0 |

第一次独立运行亦观察到同样的接管/误报结果。固定时间窗不能推出更长时间内必不接管；开源接口能接替已确认死亡的执行器，决定死亡和发起重新入队仍要由运行环境承担。若上线要求自动跨主机接管、运维团队又不负责该判定，则须另评 Conductor 或保留独立调度服务。受控意图在误报时可能防止再次发外部请求，但此处误报对照只运行了裸步骤。

## 原件与检查

[固定实现 1bd54add](https://github.com/zhuquanwei111/mingjing---agent/commit/1bd54add02f661d28a002933bfb88b5d26c3b4ec) 的 [GitHub Actions 验证](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193721756/job/137758488650) 通过八例、依赖完整性和 make check。[CI 原生完整工件](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193721756/artifacts/14826588408) 含每个工作进程日志，SHA-256 为 `44ee54511437b0137321fb4e7414ad0aa049a1c343f149343e20b8eab030a07f`。

[持久证据包](evidence/raw-records.zip) 包含最终 29 个从 Actions 输出取回并逐笔核验 SHA-256 的 JSON/txt，另有此次去除重复 base64 区段的 job.log、此前两次失败和两次通过的样本。包内 MANIFEST.json 将每份内容关联到固定提交、run、job 及 SHA-256。[最终标准六例](evidence/summary.json) 与[接管/误报结果](evidence/takeover-summary.json) 可直接阅读。还原后可独立复算工具调用、模拟费用、原始/恢复 PID 和预算结果。本轮未合并。
