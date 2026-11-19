# 明镜 P1 Instabox 验收证据

2026-11-19（北京时间），在现有 Instabox `mj-agent` 上完成 P1 云端验收。AT01–AT12 全部通过。JUnit 汇总包含 16 个通过的独立用例，其中一个是云端冒烟。P2 等待用户确认。 [用例汇总](summary.json)

## 环境和范围

- Linux x86_64，4 vCPU、8 GiB RAM，Docker Engine 29.8.2，Compose 5.6.0。专用 Compose 项目使用内部网络，测试、Temporal 和 PostgreSQL 均无公开映射端口。测试进程 UID 为 10101，运行时只放入合成数据与假模型配置。 [机器环境](environment.txt) · [网络和运行环境](runtime-isolation.txt)
- Temporal Server 1.32.2、Python SDK 1.36.1、LangGraph 1.2.22、插件 1.0.0、PostgreSQL 17.12、CPython 3.12.16。Linux amd64 锁保留 Mac 候选的 52 个包版本，使用对应平台的 wheel 哈希。OSV 按这 52 个 PyPI 精确版本查询无命中。AT10 的独立 venv 用插件 0.1.0 生成旧历史。 [版本记录](runtime-versions.txt) · [平台镜像摘要](platform-manifests.txt) · [amd64 锁](linux-x86_64.lock) · [OSV 查询结果](osv-python.json)
- Mac 的固定 Temporal CLI 1.10.1 冒烟单独保留。四份原始文件使用验收前记录的 SHA-256 复核一致。 [本地冒烟日志](../smoke.log) · [本地冒烟校验清单](local-smoke.sha256)

## 验收结果

| 项目 | 观察结果 |
| --- | --- |
| AT01 | 直接 API、确定性 Workflow 和 Agent 共用执行边界、结果契约和收据。重复请求复用结果，第二个普通能力可注册。 [AT01](batch-files/early/AT01.json) |
| AT02 | 等待期间强制结束 Worker，替代进程恢复。三个信号只接受一个有效决定。 [AT02](batch-files/early/AT02.json) |
| AT03 | PostgreSQL 提交后丢失 Activity 回执，两个执行尝试只产生一条业务记录和一条成功收据。无查单与幂等的模拟外部调用保留未知状态，外发计数一。 [AT03](batch-files/middle/AT03.json) |
| AT04 | 未授权审批返回 403；撤权、版本禁用和授权存储不可用均拒绝实际写入。 [AT04](batch-files/middle/AT04.json) |
| AT05 | 等待中和子 Activity 可取消，heartbeat 路径观察到取消，已提交的结果仍可查询。 [AT05](batch-files/middle/AT05.json) |
| AT06 | 非白名单工具、步数、深度、截止时间和预算越界被拒绝，模拟下游调用计数为零。 [AT06](batch-files/middle/AT06.json) |
| AT07 | 两个 Worker 争抢最后一个预算单位，只发生一次模拟调用。预算门禁故障时拒绝，未知尝试保留预留并完成对账。 [AT07](batch-files/middle/AT07.json) |
| AT08 | 同一任务的两个产物版本保留各自内容；跨租户读取和撤权后读取被拒绝，旧版本禁止覆盖。第一次因 pytest 夹具未给父进程配置产物目录而失败，补齐与 API 相同的临时目录后通过。 [首次 JUnit](middle.junit.xml) · [复验 JUnit](at08.junit.xml) · [AT08](batch-files/at08/AT08.json) |
| AT09 | Graph 缓存跨 Run 命中、Functional 类型往返与冷重放、审批中断恢复、流重试后断线续读与去重均通过。 [缓存](late-files/AT09-cache.json) · [Functional](late-files/AT09-functional.json) · [中断](late-files/AT09-interrupt.json) · [流](late-files/AT09-stream.json) |
| AT10 | 旧 Worker 继续处理固定旧运行，新任务走新 Worker，切回后路由如预期。同版本历史重放通过。原地升级、原地降级和节点改名对所选旧/新历史产生预期的 `NondeterminismError`。 [版本路由与重放](at10.log) · [JUnit](at10-files/at10.junit.xml) |
| AT11 | API、Workflow、Agent 和工具的 trace 可关联。模拟 exporter 故障时业务收据与审计仍持久保存。 [AT11](late-files/AT11.json) |
| AT12 | 重建专用 PostgreSQL 与 Temporal，确认新集群健康。用业务库备份在新库恢复，10 张表的行数和内容校验一致。应用角色无法连接 Temporal 主库及可见性库，测试容器无法访问外部地址。 [重建与恢复](at12-backup-rebuild.txt) · [权限和网络](late-files/AT12-network.json) |

## 复现和边界

验收分批在云端执行。对比了各容器内 Python 源文件的哈希。所有批次使用一致的核心实现，后续新增 Temporal 探针。AT09 批次到 AT10 的探针差异是清理闲置导入和记录插件实际加载路径。 [源文件核对](source-revisions.txt) · [探针差异](probe-revision.diff) · [AT10 源文件哈希](at10-source.sha256)

在临时 Linux amd64 检出目录中，将此处的 amd64 锁复制到 `requirements/`，将 Dockerfile 的锁路径从 `linux-aarch64.lock` 替换为 `linux-x86_64.lock`。用 `sh infra/new-run.sh` 创建专用凭据和运行 ID，再启动固定镜像。Compose 5.6 对一次性 namespace 容器的 `up --wait` 会报告其已退出，此处独立验证该初始化步骤的退出码。 [隔离计划](../../../mingjing-codex-engineering-v1/P1_EXECUTION_PLAN.md)

```bash
sh infra/compose.sh up -d --wait db temporal
sh infra/compose.sh run --rm --no-deps -T namespace
sh infra/compose.sh build test
sh infra/compose.sh run --no-deps -T test
```

备份演练覆盖明镜业务库与基础服务重建。Temporal History 库和产物文件字节的灾备恢复仍待专项验证。P1 的版本结论是保留固定旧 Worker 以处理在途旧运行，并用同版本历史重放验证；插件原地跨版本部署需要单独的兼容性措施。
