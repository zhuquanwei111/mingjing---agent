# 明镜 P2 开发验收

本页归档 2026-11-19 的历史验收，对应 P2 实现提交 `7d4df4f`，基线为 `40e02a8`。该次测试在 InstaBox mj-agent 上执行真实 PostgreSQL、Temporal 和 LangGraph，业务数据、身份及供应商回执均来自合成夹具。后续候选在独立 checkout 使用 `make p2-acceptance` 复验，以对应提交的 CI 和运行日志为准。

## 环境和文件

只读检查确认 /data 是 /dev/vdb 上的独立 ext4 持久挂载，20 GiB 中约有 16 GiB 可用。检查的持久目录尚无项目检出，随后从同会话的已核验 Git 基线建立新检出和独立分支。InstaBox 为 Linux x86_64、4 vCPU、约 8 GiB RAM。Docker Engine 29.8.2、Compose 5.6.0。现有宿主监听端口由只读检查确认，P2 内部网络没有发布端口。

- [产品 API 和操作手册](README.md) 说明启动、测试、读取和日常调试。
- [合约和生命周期](src/mingjing/catalog.py) 实现环境发布与精确资源授权。[业务执行边界](src/mingjing/service.py) 实现 Task/Run、审批、幂等收据、预算、产物和审计。
- [Temporal 适配器](src/mingjing/temporal_adapter.py) 与 [SDK 样例](src/mingjing/examples.py) 连接普通程序、确定性 Workflow 和受控 Agent。
- [产品迁移](migrations/0001_core.sql) 创建独立 schema，[追加迁移](migrations/0002_append_only_audit.sql) 收紧审计与迁移账本权限。[版本与回退方案](VERSIONING.md) 记录兼容和发布步骤。

## 实测结果

| 范围 | 实际结果 |
| --- | --- |
| 注册、发布与授权 | 版本独立注册、验证及发布。未授权主体无法发现或执行能力，未发布环境不可发现。版本禁用拦截在途写入，废弃版本的重复请求可复用已有结果。 |
| HTTP API 与执行 | 普通程序无需引擎。真 Temporal Workflow 与 LangGraph 工具都通过统一执行边界写入合成笔记。History 存在对应 Activity，产品 Run ID 与 Temporal Run ID 独立。 |
| 审批、撤权和取消 | 无权审批被拒，审批后撤权阻止实际写入。过期或撤销的凭据不能继续执行。审批和取消响应只给控制确认，任务与收据读取仍需读权限。已提交收据在申请取消后保持可查。 |
| 预算、幂等和对账 | 两笔申请竞争最后两个预算单位，只有一次有界供应商发送。预算门禁不可达时未发送。外部发送后结算失败以及回执丢失时都保留预留。可信查单可补结算，无可信回执则保留未知态。重复执行与对账均未重发。 |
| 产物、审计和追踪 | 跨租户及撤权后不能读取产物。产品、引擎和工具 span 可关联，同库审计、尝试与收据持久存在。应用角色不能更新或删除审计。 |
| 启动与迁移 | 运行两份迁移并重跑验证，拒绝篡改的已应用迁移。独立 API 容器健康端点返回 200，Worker 在专用任务队列有轮询者。 |

历史提交 `7d4df4f` 的 `sh infra/dev.sh test` 为 **11 通过，0 失败**。该提交的真实服务与断言见 [运行结果](evidence/runtime.txt)、[测试索引](evidence/test-summary.txt) 和 [JUnit](evidence/junit.xml)。当前 PR 以其 `P2 public layer (amd64)` 运行结果验证实际变更。

## 放行条件与回退

复用 P1 已核验的 Temporal Server 1.32.2、Temporal Python SDK 1.36.1、LangGraph 1.2.22、集成插件 1.0.0 及 Python 3.12.16。运行镜像按 linux/amd64 manifest 摘要固定，Python 52 个包以 wheel SHA-256 锁定并通过 pip check。四个核心组件的许可与原始版本证据见 [P0 依赖记录](../docs/archive/engineering-v1/DEPENDENCY_LOCK.md)。

仍需独立验证生产身份集成、对象存储、真实供应商限额及回执语义，以及负载、备份与高可用。开发镜像沿用 P1 的固定基线，[已知镜像扫描命中](../p1-walking-skeleton/evidence/lima/image-scan.json) 仍是生产制品放行项。跨版本运行沿用固定旧 Worker 的策略，P2 测试使用单一已验证版本。

sh infra/dev.sh stop 可关闭本次独立栈。Git 回退从独立分支执行，数据库按迁移方案做前向修正或从经过演练的备份恢复。
