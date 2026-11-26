# 明镜 P0 核验报告

核验日期为 2026-11-19（北京时间）。已完成只读核验与 P1 计划编制。**保留原四个版本作为 P1 候选，等待确认后进入 P1。**

## 工作区与工具

- 已完整阅读 `AGENTS.md`、`README.md` 和 01–09。检查了交付目录及其上级工作区的可见与隐藏条目。交付目录原有 12 个 Markdown 文件，无业务代码、依赖清单、服务配置、测试源码或 Git 元数据。交付目录的 `git rev-parse` 与上级目录的 `git status` 均确认当前在 Git 仓库之外。本阶段保留文档交付包并规划 P1 目录，实际初始化 Git 与源码目录留待 P1 隔离环境。
- 本机可用 Git 2.54.0、curl 8.7.1、ripgrep 15.2.0、Node.js 22.22.2。PATH 中的 `python3` 是 3.9.6，另找到可运行的 macOS arm64 CPython 3.12.16，配有 pip 26.2.2。Python 解析明确使用 3.12.16。
- PATH 和常用安装位置未发现可用 Docker、Podman、Temporal CLI、PostgreSQL CLI 或 uv，常见 Docker/Colima 套接字未发现。容器权限、实际 PostgreSQL 服务与对象存储资产待环境确认。P1 可先用固定 CLI 做引擎冒烟，全量验收需要隔离 PostgreSQL 及运行固定 Server 镜像的环境。

## 核验结果

| 范围 | P0 证据 | 结论 |
| --- | --- | --- |
| 四个固定版本 | 固定 GitHub Tag、MIT 许可文本、三份精确版本 PyPI 元数据、Temporal 镜像 registry manifest | 四个发行均存在，核心仓库/包均为 MIT。打包时仍须核查 Python 传递依赖及容器组件的许可和通知。 |
| Python 安装依赖 | CPython 3.12.16 上用 pip 对三个核心包做仅 wheel 的 dry-run，解析 43 个包。加 P1 数据库客户端、OTel 和测试依赖后解析 52 个包，并通过 `--require-hashes` dry-run 复验 | 依赖声明与本机解析一致。macOS arm64 候选带 SHA-256，Linux 锁和运行测试留待 P1。 |
| Server / SDK | Server v1.32.2 有固定镜像、SQL Schema 和发行说明。CLI v1.10.1 的源码依赖也指向 Server v1.32.2 | CLI 可用作本地同版本冒烟入口。测试仍须在固定 Server 镜像上核实工作流、数据库、Worker Versioning 和插件运行行为。 |
| 安全 | 查了 GitHub 仓库安全公告、GitHub 全局按精确版本查询、PyPI 公告与候选 52 个 Python 包的 OSV 批量查询 | 已记录命中范围与修复线索。具体容器层、原生库与最终分发物扫描仍待验收。 |
| 上游示例 | 查阅固定 Tag 的 SDK Quick Start、LangGraph 入门、插件 README 与固定提交的官方 Graph / Functional 示例 | 可以提取注册、执行、等待、重放和流式入口。P1 将示例中的模型、工具和审批交互换成合成夹具与可信 API。 |

证据索引与复现命令见 [DEPENDENCY_LOCK.md](DEPENDENCY_LOCK.md)。P0 的验证限于文件清点、版本与元数据核验、镜像 manifest 查询、依赖解析和公告查询。四个核心组件、示例与 AT01–AT12 均未启动执行。

## 恢复语义和可选路线

1. **同一 Run 内恢复。** 插件支持 Graph 节点和 Functional `@task` 的 `execute_in`。已被 Temporal 记录完成的 Activity 在确定性重放中应复用历史结果，未确认完成的 Activity 可能再次执行。纯逻辑留在 Workflow，I/O 节点配置有限重试和超时。图内 `InMemorySaver` 由当前 Run 的历史重建。Activity 型节点从函数入口恢复，P1 采用一个待处理审批中断，并让中断节点无业务副作用。 [插件 1.0.0 文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md)
2. **Continue-As-New 与升级。** 同版本在明确传递类型化状态及 `cache()` 的情况下，可命中前序 Run 的匹配 Activity 结果，每个匹配结果只消费一次。缓存也可能带上审批答案。P1 在没有未决审批的边界续跑，以显式业务游标、版本和收据定位进度。旧版缓存分支及类名/节点名变化可触发重放失败。优先让旧任务留在固定 Worker 或排空，再切换新启动任务。 [插件 1.0.0 发行说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0) · [Worker Versioning](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning)
3. **流与取消。** 1.0.0 发布说明确认插件已 GA，流式接口仍为实验功能。Activity 重试可能重发进度，P1 必须验证断线恢复、逻辑事件去重和以最终结果对账。取消依赖显式 Activity heartbeat、可取消 I/O 与提交前复核。已提交业务结果由收据报告。 [插件 1.0.0 文档](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md)

当前的版本与许可证据支持保留候选。业务若要求审批状态跨 Run 无缝保留，首先验证显式 Workflow 状态、稳定审批 ID 和独立业务收据。若关键节点恢复仍失败或必须侵入上游核心，记录最小重现，优先比较 Temporal + 显式 Activity 编排及 Temporal + Pydantic AI。只有当 Temporal 自托管或顶层持久执行本身不适用时，再比较 Dapr + Dapr Agents。详细触发条件见 [风险登记](RISK_REGISTER.md)。

## 最小运行边界

| 环境 | 最小依赖与启动路径 |
| --- | --- |
| 本地冒烟 | CPython 3.12.16、三个固定 Python 核心包、Temporal CLI v1.10.1。CLI 绑定回环地址，使用临时 SQLite 文件。依次启动 CLI、Worker、Workflow 客户端，运行纯函数或假模型。 |
| P1 隔离验收 | 固定 Temporal Server v1.32.2、同版 admin-tools 一次性建库/迁移、独立 PostgreSQL 17.12、Python API 与 Worker 两个进程、pytest 和本地 OTel sink。数据库可共用一个隔离实例，Temporal 主库、可见性库、明镜业务库分库分角色。用临时本地文件模拟产物字节，元数据走明镜权限接口。 |
| 生产部署前置 | 固定 Server 和 Worker 制品及数据库补丁线，独立迁移权限，显式管理可见性、身份认证、网络、mTLS、容量、HA、备份和恢复。接入批准的对象存储与观测后端，验证制品许可、SBOM、数据库恢复及 Worker 回滚。实际基础设施和对象存储保留待确认。 |

生产规划依据见 [Temporal 自托管部署指南](https://docs.temporal.io/self-hosted-guide/deployment)、[PostgreSQL 可见性兼容范围](https://docs.temporal.io/self-hosted-guide/visibility) 与 [PostgreSQL 17.12 发行说明](https://www.postgresql.org/docs/17/release-17-12.html)。启动命令、隔离边界和证据要求见 [P1 执行计划](P1_EXECUTION_PLAN.md)。

## 复用、适配与自有实现

| 分工 | 内容 |
| --- | --- |
| 复用 | Temporal Workflow/Activity、消息、重试、计时、历史与重放；LangGraph Graph/Functional API 与插件；PostgreSQL 事务、唯一约束和行锁；OTel trace 传播与导出接口。 |
| 适配 | Temporal Worker 注册、超时、取消和 Worker 版本路由；LangGraph 节点执行位置、确定性 ID、转换器、预算约束与流去重；PostgreSQL 事务接口；本地/后续对象存储；API 入参与状态映射、日志与 trace 关联。 |
| 明镜代码 | Capability 契约、注册/发布/授权分离、基于当前权限的可信入口和执行边界、审批校验、可重试业务收据与未知结果、预算预留及结算、产品 Task/Run 映射、产物权限与业务审计。 |

本次新增四份 P0 Markdown。P1 验收等待确认，随后按 [P1 执行计划](P1_EXECUTION_PLAN.md) 先做隔离冒烟与关键故障验证，再决定技术路线。
