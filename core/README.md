# 明镜 P2 最小公共层

> 本目录继续维护已交付的 P2 v1 接口、迁移和回归。路线 B 的新开发使用[新开发包](../mingjing-codex-engineering-v2/README.md)。

P2 提供能力目录、版本发布、资源授权、任务与 Run API、审批、收据、预算和产物读取。业务模板与统一执行路径见 [SDK 示例](src/mingjing/examples.py)。执行版本和迁移规则见 [VERSIONING.md](VERSIONING.md)。

## 日常开发

使用独立的原生 Linux ARM64 或 AMD64 checkout。从 Git 根目录执行 `make p2-acceptance` 可创建一次性 Compose project，运行测试并清理。需要保留开发卷时，从根目录执行以下命令。

    sh core/infra/dev.sh init
    sh core/infra/dev.sh test
    sh core/infra/dev.sh status

init 创建专用项目名称和合成数据库密码，使用 PostgreSQL 17.12、Temporal Server 1.32.2 和 CPython 3.12.16 的固定镜像，执行三库初始化和产品迁移。test 在内部网络运行 API、Temporal Worker 和合成调用场景。手动测试的 JUnit 位于 `core/.runtime/junit.xml`，自动验收写入命令输出指定的独立目录。构建按目标架构选择 [ARM64 锁](requirements/linux-aarch64.lock)或 [AMD64 锁](requirements/linux-x86_64.lock)，复用 P1 对应架构的相同版本与已验证 wheel 哈希。固定多架构镜像索引保留原 AMD64 子镜像并选择对应的原生 ARM64 子镜像；这不是镜像版本升级。服务使用内部网络，API 在容器内绑定回环，Worker 为 UID 10101。生产制品放行仍需处理 [P1 镜像安全发现](../p1-walking-skeleton/evidence/lima/image-scan.json)。

GitHub 正式 ARM64 作业沿用 `P1 acceptance` 名称，同时运行 P1 与本公共层验收；`P2 regression (amd64, advisory)` 仅作辅助。候选提交是否通过以其完整 CI 日志为准，配置支持某个架构不等于已完成该候选的实际验收。

从根目录执行 `sh core/infra/dev.sh run`，它在数据库和 Temporal 就绪并执行迁移后启动 API 与 Worker。API 容器内地址为 `127.0.0.1:8080`。`sh core/infra/dev.sh stop` 停止此项目容器，开发卷供下次启动复用。迁移和凭据开通使用专用的 `MINGJING_MIGRATION_DSN`。应用角色通过受限认证函数读取身份，凭据开通和撤销由迁移角色管理。

已有开发栈升级后，脚本在 `core/.runtime/dev.env` 缺失时读取原来的 `p2-core/.runtime/dev.env`。两处配置都存在时，默认使用 `core/.runtime/dev.env`。删除旧栈的卷需要在 `clean` 命令显式指定旧配置。迁移配置时在原 checkout 的 Git 根目录运行以下命令，沿用同一项目名、凭据、命名空间和开发卷。

    test -f p2-core/.runtime/dev.env &&
      test ! -e core/.runtime/dev.env &&
      mkdir -p core/.runtime &&
      P2_ENV_FILE=../p2-core/.runtime/dev.env sh core/infra/dev.sh stop &&
      mv -nT p2-core/.runtime/dev.env core/.runtime/dev.env &&
      test ! -e p2-core/.runtime/dev.env &&
      P2_ENV_FILE=.runtime/dev.env sh core/infra/dev.sh run

### API v1

除 /healthz 外，接口使用短期高熵 Bearer 凭据。主体和租户来自产品库中的有效凭据，服务端每次验证其有效期和撤销状态。用受信的交互式终端执行 python -m mingjing add-identity TENANT SUBJECT [--administrator] 创建开发凭据，命令使用隐藏输入。数据库只保存凭据摘要。合成验收使用独立租户和临时凭据。

| 路径 | 行为 |
| --- | --- |
| POST /v1/capabilities/{id}/{version}/{action} | 管理员按 register、validate、publish、deprecate、disable 管理已安装适配器和环境发布。 |
| PUT /v1/grants | 管理员授予或撤销精确主体、能力版本、资源与动作的授权。 |
| GET /v1/capabilities?resource=… | 只发现当前环境已发布且主体有执行授权的能力，返回 JSON Schema。 |
| POST /v1/tasks | 带 Idempotency-Key，提交 capability_id、version、resource 和 input。普通能力同步执行，Temporal 能力返回稳定的 Task/Run。无读取授权时仅返回 Task/Run 引用。重复键要求规范化请求体一致。 |
| GET /v1/tasks/{id} 与 GET /v1/tasks/{id}/runs | 返回产品状态、收据、任务与 Run 映射。读取时观察 Temporal 终态，产品库与引擎各保留自身状态。 |
| POST /v1/tasks/{id}/approval | 以审批授权提交 approved 或 rejected。执行前复核原请求身份、审批身份、期限、发布和资源。 |
| POST /v1/tasks/{id}/cancel | 在业务边界记录取消意图，异步转达引擎。已提交的收据可查询。 |
| POST /v1/tasks/{id}/reconcile | 以对账授权使用任务固定的环境和契约查询适配器，结算已确认的有界成本。未知回执继续保留预留。 |
| GET /v1/artifacts/{id} | 按当前租户和资源重新授权，校验内容哈希，返回产物字节。 |

结构化错误含 schema_version 和 code。API 中出现引擎不可用时，原调用方可用相同请求键重试提交，数据库与引擎 ID 保持稳定。审批决策在发送信号前提交，Workflow 定期查看数据库审批状态。取消采用同样的先持久化原则。

引擎启动尝试和命名空间先写入产品库。并发提交遇到正在启动且尚无 Run ID 的同一任务时可收到 HTTP 503 `engine_start_in_progress`，客户端可在五分钟窗口内用原幂等键和请求体重试。已记录 Run ID 时只查询该 Run，查询暂时失败时返回产品库中已记录的结果。窗口外先向所属命名空间核实，引擎确认历史不可取得且业务收据缺失时，产品状态显示为 `unknown`。开发命名空间保留一天历史。

### 开发能力与扩展

定义 Model 的输入输出类型和 CapabilityContext 上下文，再在应用加载配置中注册 Capability。业务函数通过 NotesPort 使用同库事务。普通程序 normalize_text 返回产物，固定 Workflow 的 write_note 审批后记一条合成笔记，Agent 的 draft_note 使用固定决策和受控工具复用同一笔记实现。业务函数的签名与 Temporal 和 LangGraph 无关。应用根据可信契约决定执行入口。

外部适配器的 send 和 lookup 接口使用稳定 operation_id。开发示例 fake_delivery 以第二次数据库提交模拟外部接收，能验证发送与结算之间的未知态。真实适配器必须指定可信成本上界，且只从其结果查询确认外部回执。

## 持久化边界

- 业务写入、产品收据和审计同事务提交。已有收据阻止重复 I/O。对外发送前先提交预留和发送记录，发送前再次检查实时门禁。
- 跨事务发送期间持有 PostgreSQL 会话锁。发送进程退出后，同键重试会将未完成的发送标为未知，保留预留并等待可信对账。
- 受控写入端口、产物路径和业务提交前重新检查当前授权及 Activity 截止时间。单次尝试超时会回滚非外部写入，由 Temporal 处理后续尝试。权限到期会拒绝操作。
- 产品 Run 与 Temporal Run ID 分别记录。只有可信产品 API 持久化审批，Temporal Signal 仅提示重新检查。
- 摘要寻址的本地文件存储用于开发演练。预先创建产物目录，文件及目录同步成功后才提交产物元数据和业务收据。读取前校验授权。孤立字节可由后续存储清理流程回收。
- OTel SDK 可按 MINGJING_LOCAL_TRACE=1 输出开发追踪。审计表禁止应用角色更新或删除，授权、尝试及结果证据独立保存。

生产接入还需要企业身份、生产对象存储、对外 TLS、供应商回执和成本上界、负载及 HA 验证。当前 API 的同步重试和异步状态查询用于开发闭环。后台无人值守投递和自动对账需专项验证。
