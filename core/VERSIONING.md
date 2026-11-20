# P2 契约、迁移与 Worker 版本管理

## 能力版本

能力版本由 capability_id 与正整数 version 标识。服务端从已安装的适配器提取输入和输出 JSON Schema、执行方式、权限、超时、预算及产物约定，并计算契约 SHA-256。注册写入版本和摘要，验证通过后才能按环境发布。授权独立绑定租户、主体、能力版本、资源和动作。

已经受理的 Task 固定版本、载荷摘要、运行环境和契约摘要。废弃版本停止接收新任务，既有任务可以在权限有效时完成。禁用立即拦截尚未提交的写入。已经提交的收据仍可在读授权下访问。更改输入输出或执行策略时增加版本，安装新旧实现后分别发布。发现和执行都核对安装中的契约摘要。

## 数据库

执行 python -m mingjing migrate，使用独立 MIGRATION DSN。迁移在 PostgreSQL advisory transaction lock 下按文件名顺序执行，同事务记录每个迁移的 SHA-256。重跑校验既有文件，并拒绝缺失、篡改或乱序的迁移。产品库、Temporal 主库和可见性库分角色使用。P2 从空产品库创建独立 schema，P1 的合成数据供验收参考。

部署前在隔离库应用全部迁移和重复运行。真实数据变更先备份并演练恢复，再采用可前向兼容的扩展迁移。代码回滚仅使用仍理解当前 schema 的已验证版本。破坏性变更需要单独的恢复或前向修复步骤。

## Temporal 与 LangGraph

稳定引擎入口为 MingjingTaskV1，Activity 名称采用 mingjing.check.v1 和 mingjing.execute.v1，Agent 图注册名为 mingjing.agent.v1。Workflow 输入只包含产品任务 ID 和受信的执行形态，数据库查询和副作用处于 Activity。产品运行状态由 PostgreSQL 保存，Temporal History 用于引擎恢复。

首个启动尝试绑定任务环境和命名空间，同键启动重试限于五分钟。该窗口须短于实际配置的命名空间历史保留期。运行中的启动调用持有 PostgreSQL 会话锁，防止并发查询将其误判为历史缺失。已记录的 Run ID 保持固定。旧任务缺少原命名空间时保留产品状态，由运维核实后再登记绑定。

开发 Compose 用当前固定版本执行。Worker 支持 MINGJING_WORKER_DEPLOYMENT 和 MINGJING_WORKER_BUILD，两个值成对设置后使用固定 Worker Deployment 版本。正式升级时，应在隔离环境先对新/旧已完成历史做同版本重放，再使用固定版本路由并保留旧 Worker 直到其在途任务结束。回滚通过切换新任务路由并保留已有执行所属 Worker 完成。P1 已实测直接跨插件版本重放与节点改名会导致非确定性错误。 [P1 AT10](../p1-walking-skeleton/evidence/lima/AT10.json)

生产放行前复核已知高危与严重镜像命中，验证修复后的镜像兼容性、锁定摘要和回退路由。
