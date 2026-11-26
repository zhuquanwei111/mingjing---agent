# 明镜 P1 验收报告

**2026-11-19 · AT01–AT12 功能验收通过，进入 P2 待确认。**

本地 Temporal CLI 1.10.1 冒烟通过，内置 Server 版本为 1.32.2。随后在独立 Lima Linux arm64 VM 中用固定 OCI 镜像完成验收，最后一轮从新建的 Compose 卷开始，16 项 pytest 全部通过。应用数据库备份恢复校验通过，Temporal Server 重启前后同一历史的 SHA-256 相同，独立 Compose project 重建后两项复检通过。 [本地冒烟](evidence/smoke.log) · [全量 JUnit](evidence/lima/acceptance.junit.xml) · [验收日志](evidence/lima/acceptance.log)

## 环境与运行范围

- 本地使用 macOS arm64、CPython 3.12.16、Temporal CLI 1.10.1。CLI 下载文件的 SHA-256 与已核验发行摘要一致。冒烟覆盖普通 Workflow、LangGraph Graph API、Functional API 和真实 Activity 完成事件。 [CLI 版本](evidence/cli-version.txt) · [CLI 哈希](evidence/cli-sha256.txt)
- 隔离环境使用 Lima 2.3.0、Ubuntu 24.04 arm64、Docker 29.1.3、Compose 2.40.3、Temporal Server/admin-tools 1.32.2、PostgreSQL 17.12、CPython 3.12.16、Temporal Python SDK 1.36.1、LangGraph 1.2.22 和插件 1.0.0。插件 0.1.0 仅用于 AT10 旧 Worker/重放，各自用独立 Python 环境并核对实际导入路径。平台依赖以 52 项带哈希的 wheel 锁安装并通过 `pip check`。 [运行时清单](evidence/lima/runtime.txt) · [OCI 平台摘要](evidence/lima/platform-images.json) · [Linux Python 锁](requirements/linux-aarch64.lock)
- VM 未挂载宿主目录，Compose 使用内部网络，API 与假的 HTTP 服务只绑定容器回环。无服务端口发布到宿主，测试 runner 使用 UID 10101。业务角色无法连接 Temporal 主库及可见性库。输入、身份、预算与外部回执均为合成数据，模型由脚本夹具提供。 [Compose 配置](infra/compose.yaml) · [网络与角色证据](evidence/lima/AT12-network.json)

## 验收矩阵

共有三个运行入口和一个可信执行边界。用例、启动命令、测试夹具和备份恢复脚本见 [复现说明](README.md)。以下“通过”指该场景中实际观察到的行为。

| 项目 | 实验和实测结果 |
| --- | --- |
| AT01 · 异构能力 | HTTP 直接执行、Temporal Workflow 和 LangGraph 工具均调用 `record_marker@1`，返回同一 v1 结果结构。每次逻辑操作恰有一条业务收据。重复任务键复用 Task，改变载荷返回 409。第二项普通能力复用执行边界，改动在能力声明与发布夹具。 [证据](evidence/lima/AT01.json) |
| AT02 · 异步恢复 | 在审批等待中对旧 Worker 发送 SIGKILL。新 Worker 恢复同一等待状态。三个引擎 Signal 中只接受一次有效决定，过期 API 回调被拒绝。业务结果和产物可查询。 [证据](evidence/lima/AT02.json) |
| AT03 · 写入与回执丢失 | PostgreSQL 已提交，但历史中尚无 Activity 完成事件时杀进程。引擎尝试为 2，最终仍为一次业务写入、一条收据。无查单接口的合成外部服务接收后断开，业务状态为 UNKNOWN，重复提交合计仅一次发送。 [证据](evidence/lima/AT03.json) |
| AT04 · 审批和撤权 | 无权限审批返回 403。审批后、I/O 前撤权和禁用发布均阻止写入。使用不可达数据库连接时执行门禁拒绝。三条路径均为零业务写入，在线拒绝记录保留于审计。 [证据](evidence/lima/AT04.json) |
| AT05 · 取消 | 覆盖审批等待、带 heartbeat 的子 Workflow、业务提交后和带默认错误处理器的 Agent 节点。等待/执行中取消关闭对应运行，不再启动该操作。已提交结果和收据可查，产品状态同时记录了取消请求。Agent 错误处理器传播取消。 [证据](evidence/lima/AT05.json) |
| AT06 · Agent 边界 | 脚本夹具提出未注册工具、超步数、超深度、超时和余额不足请求，得到相应拒绝码，外部调用数为零。实际 I/O Activity 会重新检查截止时间、当前权限及预算。 [证据](evidence/lima/AT06.json) |
| AT07 · 并发预算 | 两个独立 Worker 同时争夺一个预算单位，只有一次模拟计费调用。预算事务锁超时阻止发送。供应商回执丢失时保留一单位并幂等核对。另注入发送后、结算提交前的数据库失败，状态进入 UNKNOWN，随后的重复调用没有重发。 [证据](evidence/lima/AT07.json) |
| AT08 · 产物权限 | 同任务两个产物版本内容哈希不同，重试保留原版本，同版本异内容被拒。跨租户访问返回 404，撤权后原 ID 返回 403。 [证据](evidence/lima/AT08.json) |
| AT09 · 插件恢复 | Graph 中断在冷 Worker 重启后恢复，History 有两次审批节点调度与一次工具 Activity。Functional 用例首次 Activity 失败、第二次成功，冷恢复和离线重放均保留嵌套模型、日期、UUID 及消息 ID。Graph Continue-As-New 两个 Run 的 Activity 调度数为 2 与 1。流式用例在首批发布后杀 Worker，重试产生重复逻辑事件，消费端去重并按游标跨 Run 取到最终事件。 [中断](evidence/lima/AT09-interrupt.json) · [Functional](evidence/lima/AT09-functional.json) · [缓存](evidence/lima/AT09-cache.json) · [流](evidence/lima/AT09-stream.json) |
| AT10 · 版本演进 | 使用同一任务队列的两个固定 Worker 版本执行前滚和回滚。旧任务与在途新任务均由各自版本完成，回滚后新启动任务进入旧 Worker。旧版复用同输入结果，新版分别调度两次。匹配版本的历史重放通过，原地双向交叉重放与节点改名得到预期的 `NondeterminismError`。 [版本路由](evidence/lima/AT10.json) · [旧历史](evidence/lima/AT10-old.history.json) · [新历史](evidence/lima/AT10-new.history.json) |
| AT11 · 追踪与审计 | 同一 trace 串起 API、Workflow、Agent、工具，并对照任务、运行、操作、尝试和产物 ID。注入 exporter 返回失败后业务收据和审计仍存在。 [证据](evidence/lima/AT11.json) |
| AT12 · 重建和备份 | 使用 `pg_dump` 和 `pg_restore` 恢复至新建数据库，核对 15 条业务收据的聚合哈希、11 条业务写入、82 条审计及 20 条审批。Temporal Server 重启后既有历史字节一致。独立 Compose project 从空库重建，冒烟和网络/角色两项复检通过。 [恢复](evidence/lima/AT12-backup.txt) · [重启](evidence/lima/AT12-restart.txt) · [重建](evidence/lima/AT12-rebuild.txt) |

## 版本与制品门禁

**插件升级须保留旧 Worker 直到在途运行结束。** 0.1.0 与 1.0.0 的行为差异已经在真实历史复现。发布和回滚应切换新启动任务的版本指派，并等待各固定版本的在途任务完成。节点、活动或类型名称的变更先以真实版本的历史样本重放。Continue-As-New 用显式状态推进。实验性 streaming 按 at-least-once 处理，进度按稳定事件 ID 去重，最终状态以业务收据和持久结果确认。 [官方升级说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0) · [实测边界](evidence/lima/AT10.json)

**镜像安全放行仍待处理。** Trivy 0.76.2 生成了四份 CycloneDX 清单，按镜像去重之后，Temporal Server 与 admin-tools 各有 2 个高危 ID，PostgreSQL 镜像有 26 个高危与 1 个严重 ID，测试 runner 有 29 个高危与 2 个严重 ID。Temporal 命中 Go 标准库与 `x/net`，PostgreSQL 镜像命中项指向打包的 `gosu`，runner 命中基础 OS 包。本轮保留固定镜像完成合成隔离验证。后续制品候选可选上游已修复发行，或评审使用修复后的工具链与基础镜像重建，再复扫和重跑验收。OSV 对本次 Linux Python 锁和旧版测试插件的 53 个精确版本查询无命中。 [镜像扫描](evidence/lima/image-scan.json) · [OSV](evidence/osv.json)

## 本次变更和剩余验证

新增独立 Git 工作目录，包含执行试验代码、容器与数据库初始化、两个架构相关的 Python 锁、旧插件测试锁、16 项测试、复现脚本及验收证据。P1 环境使用本地 VM 代替宿主容器安装。首次启动修正了 schema 工具的端口配置和 Functional 示例装饰器用法。随后修正了产物夹具环境变量、Functional 探针的类型导入，以及旧版插件被系统环境同名包遮蔽的问题。最终表格和 JUnit 来自同一轮干净运行。

后续仍需验证生产身份、对象存储、真实供应商回执协议、负载及 HA。镜像扫描结果和 Worker 版本约束需纳入下一阶段决策。隔离工程可通过销毁其专用 Compose project 和 VM 回滚，验收证据可独立重新审阅。**P2 等待用户确认。**
