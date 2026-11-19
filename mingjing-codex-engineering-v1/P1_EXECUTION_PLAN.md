# P1 Walking Skeleton 隔离验证计划

状态为待批准。所有目录、命令、环境变量和测试用例均为 P1 计划。验收只用合成数据、回环或隔离网络、假模型与可重置数据库。

## 验证范围和目录

用同一条合成业务能力 `record_marker@1` 验证三个入口。直接 API 同步调用执行边界。确定性 Workflow 在等待审批后调用 Activity。Agent 以固定假模型选择工具，经 Activity 调用同一执行边界。API 暴露任务提交、查询、取消、审批和产物读取。有限改动应足以注册第二项普通能力，再以受控假 HTTP 服务验证外部适配入口与未知回执。

```text
p1-walking-skeleton/
  README.md
  .gitignore
  requirements/
    smoke.in
    p1-dev.in
    macos-arm64.lock
    linux-<arch>.lock
  infra/
    compose.yaml
    init/
  src/mingjing_p1/
    api.py
    contracts.py
    execution.py
    storage.py
    telemetry.py
    temporal/
      worker.py
      workflows.py
      activities.py
      smoke.py
    agent/
      graph.py
      fake_model.py
  tests/
    conftest.py
    test_smoke.py
    test_at01_at02.py
    test_at03_at05.py
    test_at06_at08.py
    test_at09_at10.py
    test_at11_at12.py
    fixtures/
  .p1/
```

P1 在独立临时目录中建立 Git 仓库，或以已有空仓库的隔离分支/工作树承载。开发者用 Python API 和 Worker 两个进程，共用类型化契约与执行实现。验收时新增第二 Worker、旧版 Worker、假外部服务和本地 trace sink，按用例启停。测试运行文件与可丢弃记录进 `.p1/`，脱敏后的测试证据附 P1 报告。

## 执行、事务和状态

1. API 从测试夹具签发的短期凭据识别主体，服务端绑定租户和委派范围。事务内按调用键和请求摘要分配 Task，固定能力版本。重复请求返回原 Task 或确定的摘要冲突。可信 API 校验审批权限、期限、资源和参数摘要，持久记录决定，再发送稳定决定 ID。API 提交与引擎启动、审批记录与投递分别有可重试状态，使用稳定 Workflow ID 和事件 ID 处理返回丢失。Workflow 实现进度查询及重复、迟到回调归并。
2. 执行边界在实际 I/O 前读取当前主体、租户、发布版本、资源、动作、审批、委派、取消和预算状态。测试内同库授权行、操作行和预算行按一致顺序加锁，将写入与撤权的先后关系固定到提交记录。缺失或异常时失败关闭。外部调用在发送前重新核验，记录核验时间与外部发送边界，区分“撤权先于发送”和“已发送、外部结果未知”。
3. `operation_id` 在逻辑步骤创建时持久分配，随 Task/能力版本和工作流状态传递，跨 Activity 重试与 Continue-As-New 保持稳定。`(tenant_id, operation_id)` 与请求摘要防止重试重复提交或错用同键。业务动作与收据同事务提交，成功重试读取已有结果。跨系统用稳定外部幂等键或查单恢复。两者都缺失时预记尝试，再将结果标为 `UNKNOWN`，进入人工核对并停止自动重发。
4. 预算用整数单位。对实际计费尝试取得或恢复唯一预留，预算行加锁并与尝试状态同事务写入，确认预留和授权后才发起合成动作。结算按 `attempt_id` 或可信回执幂等，未知保留预留。对于支持幂等的模拟供应商，重试先查单或复用外部键。新的真实尝试需要重新经过许可与预算检查。子执行继承截止时间、步数、深度、白名单与额度。
5. 明镜数据库维护 Task/Run、收据、预算、产物与审计。Temporal History 维护执行和恢复。图内 `InMemorySaver` 用于中断状态。本地文件仅保存合成产物字节，以哈希加版本防覆盖，读路径每次核权。OTel 传播 `task_id`、`run_id`、`workflow_id`、`operation_id`、`attempt_id` 和可用的 `artifact_id`，区分明镜 Run 与 Temporal Run ID。

## 插件选型实验

- 用两个最小 Workflow 分别执行 Graph API 和 Functional API。显式指定每个节点或任务的 `execute_in`。Workflow 节点和路由函数采用确定性的 async 实现，I/O 进 Activity。每个 Worker 一个 `LangGraphPlugin` 实例，配置有限重试和超时。在需要收取消的 Activity 中明确 heartbeat 频率、取消等待方式和提交前检查。配置显式终止的确定性错误类型，验证取消不会被默认错误处理器吞掉。
- YAML/数据库配置、凭据和大字段不进入 Workflow 参数。注册可导入的 DTO 和稳定消息类。首条路径用小型字典/类型化数据。另用 Pydantic v2 converter 验证嵌套模型、`AnyMessage`、日期和 UUID 的冷恢复，并保持新旧 Client/Worker 转换器相互兼容。
- 图中一个待处理审批中断，审批节点可重入且无写入。业务审批 ID 由平台管理，消息 ID 在确定性路径生成。观察 Worker 重启前后的待审批查询，使用 `Command(resume=value)` 将已核验决定送入该次等待。使用历史确认恢复发生在 Activity 边界。
- 对比已有 Activity 完成事件后的冷重放、Activity 未报完成后的重试、同版本 Continue-As-New 和跨版本切换。用显式 Workflow 游标和收据演示业务续跑，在纯操作实验中单独比较 `cache()` 的相同输入命中、再次调用和类型变化。续跑时校验最终结果和旧/新 Run ID。保留固定类名、节点名、类型及工作流输入。先等待消息 handler 完成再续跑。
- 流式实验用专用 Worker/队列，每种 Workflow 初始化 `WorkflowStream`。观察 `get_stream_writer()` 的 custom stream，另用 `astream()` 桥接进度更新。用固定的逻辑步骤 ID 和进度序号标识合成进度，客户端游标负责断线接续，逻辑 ID 负责跨尝试去重。最终进度从持久结果查询核对。若业务要求失败尝试产生的不同流内容也能精确合并，提交实测差异并单独决策。

参考 [插件 1.0.0 文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md)、[Temporal Python 样例](https://github.com/temporalio/samples-python/tree/2fb335017cabc56790a6601f56340c16fce68947/langgraph_plugin) 和 [Workflow Streams](https://docs.temporal.io/encyclopedia/workflow-message-passing/workflow-streams)。

## 环境变量

| 变量 | P1 约定 |
| --- | --- |
| `MINGJING_ENV`、`MINGJING_RUN_ID` | `p1` 和本次隔离运行 ID。Compose 项目、命名空间、队列及本地目录使用此前缀。 |
| `TEMPORAL_ADDRESS`、`TEMPORAL_NAMESPACE`、`TEMPORAL_TASK_QUEUE` | 宿主机冒烟使用 `127.0.0.1:7233` 和 `default`。Compose 验收使用 compose 内部或回环地址、专用命名空间及队列。旧/新 Worker 另记录各自 Build ID，流式验证用单独队列。 |
| `MINGJING_WORKER_BUILD_ID` | AT10 固定的 Worker Build ID。分别启动旧版和新版，记录指派规则。 |
| `MINGJING_DB_DSN` | 明镜隔离数据库 DSN。测试 runner 生成短期凭据，以受限权限文件或环境注入。迁移任务另有数据库身份，Temporal 有自己的主库和可见性库。 |
| `MINGJING_API_BIND`、`MINGJING_ARTIFACT_DIR`、`MINGJING_TEST_CREDENTIALS_FILE` | API 回环地址和端口、临时产物目录、受限的合成测试身份文件。`/healthz` 只返回就绪状态。 |
| `MINGJING_MODEL`、`MINGJING_MAX_STEPS`、`MINGJING_MAX_DEPTH`、`MINGJING_DEADLINE_SECONDS`、`MINGJING_BUDGET_UNITS` | 模型值 `fake`，其余为固定的上限。并发预算测试为两个 Worker 配同一个剩余单位。 |
| `LANGSMITH_TRACING`、`LANGCHAIN_TRACING_V2`、`OTEL_TRACES_EXPORTER`、`LANGGRAPH_STRICT_MSGPACK` | 前两项 `false`，OTel 默认 `none`，AT11 使用本地测试 sink。严格反序列化设为 `true`，先验证夹具类型相容。隔离环境清除继承的供应商及观测凭据，并限制外部 egress。 |

## 启动与测试命令

P1 实现以下入口后执行。先用 [候选锁](DEPENDENCY_LOCK.md) 建 venv。固定锁基于运行平台，CI 在隔离目标 Linux 环境重算并补齐哈希。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements/macos-arm64.lock
python -m pip check
export PYTHONPATH="$PWD/src"
export MINGJING_ENV=p1 MINGJING_MODEL=fake
export LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false OTEL_TRACES_EXPORTER=none
export LANGGRAPH_STRICT_MSGPACK=true
```

本地冒烟先校验 CLI v1.10.1 文件哈希，启动开发 Server。在两端设置对应的 `TEMPORAL_ADDRESS`、命名空间和队列。测试模块可管理冒烟 Worker。另在手动验证时先启动 Worker，再运行客户端。 [CLI 启动参数](https://docs.temporal.io/cli/command-reference/server#start-dev)

```bash
mkdir -p .p1
temporal server start-dev --ip 127.0.0.1 --port 7233 --headless --db-filename .p1/temporal.sqlite
# 另一个终端，使用相同的开发环境
python -m pytest -q tests/test_smoke.py
# 手动方式，在两个终端依次执行
python -m mingjing_p1.temporal.smoke worker
python -m mingjing_p1.temporal.smoke run
```

全量验收由 Compose 提供 PostgreSQL、一次性 schema 初始化及固定 Server。DB 初始化创建 `temporal`、`temporal_visibility` 与明镜专用库，命名空间初始化在 Server 就绪后执行。镜像启动、SQL schema 安装、命名空间探测都有健康检查。测试 runner 用独立子进程启动 API 与 Worker 并控制故障点。Compose 仅暴露测试所需端口到回环地址，容器间使用专用网络。以下 `MINGJING_RUN_ID` 为每次运行生成的值，`.p1/runtime.env` 由测试准备程序生成并限制权限。 [官方 Compose](https://github.com/temporalio/samples-server/blob/main/compose/docker-compose-postgres.yml) · [初始化 SQL 脚本](https://github.com/temporalio/samples-server/blob/main/compose/scripts/setup-postgres.sh)

```bash
docker compose --env-file .p1/runtime.env -p "mingjing-p1-${MINGJING_RUN_ID:?}" -f infra/compose.yaml up -d --wait
python -m pytest -q -ra --junitxml=.p1/junit.xml tests
```

单独重跑风险最高的场景可执行 `python -m pytest -q tests/test_at03_at05.py tests/test_at09_at10.py`。清理先导出证据，核对 Compose project 名、容器、卷及路径均属于本次隔离运行，再清理专用容器、临时数据库与目录。

## 验收与故障注入

测试使用进程间屏障和显式持久标记到达故障点。超时是失败证据。故障开关只由本地测试 runner 控制。

| 验收 | 故障注入与断言 |
| --- | --- |
| AT01 · 异构入口 | 三种入口各提交合成操作与重复请求，核对相同输出 Schema、统一身份、收据 (每次逻辑操作一条) 与关联 ID。新增第二项普通能力，记录改动文件。 |
| AT02 · 异步恢复 | Workflow 进入等待后强制停止 Worker，重启新进程并等待重放。经可信 API 发送相同回调两次，再送过期决定。核对仅一次状态推进、History、Task 和产物状态。 |
| AT03 · 回执丢失 | 在 PostgreSQL COMMIT 后、Activity 返回前，由事务后屏障停止首个 Worker。替代 Worker 超时后重试，核对一次业务写、一条成功收据与两次执行尝试。假外部服务另模拟已接受但断开连接、拒绝提供查单且无幂等协议，核对 UNKNOWN 和调用计数一。 |
| AT04 · 审批与撤权 | 合成无权主体尝试审批，验证拒绝并留下审计。有权主体批准后，在真正 I/O 的门禁屏障前撤销权限。恢复后读取当前策略，拒绝写入。覆盖发布禁用与授权存储不可用。 |
| AT05 · 取消 | 分别在审批等待、可 heartbeat 的执行中、业务 COMMIT 后触发取消。检查子执行退出、未发起的新动作被拦截、已提交结果可查。故障注入包含取消与错误处理器交叉。 |
| AT06 · Agent 边界 | 脚本化假模型依次请求白名单外工具、超步数、超深度、过期时钟及预算耗尽。核对失败码、下游调用计数和子执行/重试继承范围。 |
| AT07 · 并发预算 | 两个 Worker 在锁前同到屏障，争夺最后一个单位，用独立数据库连接验证仅一个真实模拟调用。预算读取或提交故障时验证失败关闭，回执丢失时保留预留并执行对账。 |
| AT08 · 产物权限 | 从一租户生成同任务的多版本合成文件，验证不同租户读取拒绝，撤权后已有 ID 读取拒绝，重试保留原哈希及版本。 |
| AT09 · 插件恢复 | 对 Graph 和 Functional 标记边界，记录已完成 Activity 的原历史与冷重放、失败重试、单中断恢复、类型回放、两次同输入调用、跨 Run 缓存命中和显式状态。另在流发送一个批次后终止进程、重连并重试，验证原始重复、逻辑去重、跨 Run 游标和最终结果。 |
| AT10 · 版本演进 | 固定旧 Worker 开启等待任务并导出合成历史，发布新版本后分别启动新任务并恢复旧任务。用对应插件与 converter 的 SDK `Replayer` 测旧/新历史。用隔离样本检验节点/类改名、旧版缓存行为和不兼容回滚，验证旧任务保留及回退路由。 |
| AT11 · 可观测性 | 对照 trace、审计与收据 ID。关掉本地 exporter 或注入导出失败，业务事务与审计仍可提交并查询。 |
| AT12 · 可重建性 | 记录镜像摘要、架构、端口、依赖与数据库角色，执行临时备份/恢复，检查持久结果及隔离环境重建。记录新增能力影响范围。 |

每项记录前置条件、版本、命令、预期、实际结果、历史事件/SQL/调用计数证据、失败归属和门禁结论。P1 阻断包括关键节点级恢复缺失、必须改上游核心、授权/预算绕过、重复副作用、未知结果错误推进或既有运行无法安全保留。待用户确认 P1 才创建上述源码与环境。P2 需要 P1 通过及后续确认。
