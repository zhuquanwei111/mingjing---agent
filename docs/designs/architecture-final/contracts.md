# DeerFlow 主体架构的职责、接口与必要适配

**设计基线，非已实施接口。** 固定参考源码 `58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a`；详细证据为R3 独立裁决《01-问题与依据》§3–6，见[原件定位](../../tasks/architecture-baseline-transition.md#决定与证据定位)。实际制品由 H 锁定。遵守[当前架构](../current-architecture-baseline.md)及[现行需求](../../requirements/current-engineering-requirements.md)。

![App 的普通程序和 DeerFlow Agent 经真实资源授权复用业务与知识能力，宿主及资源方分别提供治理证据。](architecture.png)

[Mermaid 图源](architecture.mmd) · [矢量图](architecture.svg)。SVG 与本页 PNG 均由同一图源生成。框图为职责与调用关系，不是一框一服务或实际部署清单。

## 一、责任分离（避免重复建设）

| 层 | 原生/成熟优先 | 明镜必要责任及不做事项 |
|---|---|---|
| App 与身份入口 | DeerFlow Gateway、原生 session/OIDC、用户与 owner、线程/事件/API | 实际 App 接入和业务身份映射、用户体验；普通服务按授权直达业务 API；禁止客户端共享内部 token 或任意 owner。不要重做一个通用智能体聊天宿主。 |
| Agent 执行 | 原生 Lead Agent、工具/子任务、扩展、检查点/运行状态、模型配置 | 真实业务工具/参数/权限及实际结果；原生适用机制合理使用，不重写 Loop、上下文或通用调度。 |
| 普通/固定/异步 | 现有业务程序/合适普通代码、原生 scheduler/工作流/MCP Tasks | 同一业务模块/API 实现正式规则；必要无人值守若原生不能满足才补适用成熟任务机制，避免重复调度同一工作。 |
| 资源权限与正式结果 | 原生工具 Provider/Guardrail、真实资源方授权/事务/成熟接口 | 启用原生细粒度授权、最小默认角色，按实际用户和资源核权。业务资源定义批准的动作、正式效果与查证。记录实际事实，不以 Agent 自述/Trace 替代。 |
| 数据/知识/原件 | 原生知识 Provider/范围/来源/管理扩展及成熟知识库/解析/存储 | 必要版本、有效性、实际知识 ACL、正式数据质量和媒体/复杂版面等真实需求；普通资料无需统一发布，原生更新或范围重建可接受。 |
| 管理与质量/运维 | 原生界面/配置/运行证据、成熟测试评测/观测、原生部署/恢复 | 必要业务管理/交付、最小审计、实际费用、版本与回归、实际安全制品及恢复目标。无默认独立平台或金融级总账。 |

## 二、A：身份、授权与实际安全

[身份设计](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/docs/AUTH_DESIGN.md)、[授权配置](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/packages/harness/deerflow/config/authorization_config.py)、[工具授权适配](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/packages/harness/deerflow/authz/adapter.py)。宿主身份与 owner 是原生基础，不等于已实现主播/客户/财务等机构权限。细粒度授权默认关闭，实际启用且 fail-closed；资源服务根据可信 actor、resource、action、purpose 与实际规则授权，工具清单不是最终业务授权。优先正常 session/OIDC；若确需 App 后端代理，由可信后端提供经验证的主体和最小权限，内部共享 token 不给终端/模型，拒绝默认桶/伪造 owner。后端内部 owner 查找异常可能跳过停用检查，[源码](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/app/gateway/auth_middleware.py) 说明需明确实际接线。

常规调岗可在有效任务范围内继续已准分析、提醒、暂停或停止；下一次新无权读取/扩大用途、正式操作或不获准外发仍拒绝。高风险紧急禁用按实际规则采用有效控制，不要求普适跨所有物理交接原子化。AIO 沙盒网络默认 open；仅启用必要的受信沙盒/工具/目的地，最小凭据/挂载，选择实际安全配置。任意第三方扩展在 Gateway 内运行不是安全沙盒；由工程方审批可信扩展。原生 owner 测试为存储层局部证据，真实 App 及资源路径仍 W0/G 验证。

## 三、B：共享能力与不同执行方式

[插件合同](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/packages/extension-api/deerflow_extension_api/plugins.py) 提供 BackendAction/ModelTool 和 host principal；普通 API、固定代码、Agent 工具复用同一实际业务模块。共享业务规则、输入/输出和真实结果，而非强制共享运行引擎。版本、发布、授权通过原生登记/部署启用/资源核权实现；必要 ID 关联而非全局总账。

[AgentRuns](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/docs/extension-agent-runs.md) 的保留授权 handle 不跨重启；交互工作流不提供任意业务 I/O；上游双 Gateway 验证为局部而非明镜无人值守。原生 scheduler/MCP Tasks 处理适用后台场景；必要业务时效按实际合同用合适任务服务或恢复。远端提交在本地 handle 保存之前（[MCP service](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/app/mcp_tasks/service.py)），普通低风险可重做、查或提醒；预约等正式效果按资源端幂等/查询、可靠同意图重试、等待或人工核实。取消后不推进已取消下游，已有效果真实记录。

## 四、C：知识、正式业务、费用与质量

[WeKnora 接线与验证](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/examples/deerflow-extension-weknora/VALIDATION.md) 支持原生 scoped 检索、引用及真实合成中文局部验证，版本 v0.8.3；旧 v0.9.1 兼容和真实复杂文档/模态/中文质量待核。管理扩展按自身策略控制自己的路由，[并不是聊天检索ACL](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/examples/deerflow-extension-knowledge-platform/README.md)。不用宿主全局 admin 代替普通人员资源管理。

普通上传原生处理后可供获准人查询；重要财务/合同/制度/许可按实际审核和正式版本。撤回后停止新检索和新原件访问；合法普通旧历史保留，不强制所有摘要/记忆/文件派生追踪与遮蔽。旧回答不是新的正式事实，真实需核事实走授权资源或当前来源。特殊保密/许可按业务确定。知识复杂版面、表格金额、视觉时码和实际来源仍按完整目标验，局部供方不合格先换局部。

复盘后预约例：正确主播、场次与证据，缺证说明；复盘达到真实完成条件才约。同一妆造时段只能一条有效预约，未知查证或可靠同意图重试；改期失败保留原预约，取消迟到不触发下游。两项结果分别展示，不以运行成功代替正式业务成功。

费用按原生步数、时长、并发、Token、速率及供方资源配额、账单和合理有限重试。原生 TokenBudget 不是精确硬货币上限，实际硬限/昂贵不可逆操作才严格有效准入/核销。普通费用不强制所有物理 Attempt 入统一父预算。重要结果确定性质量门和真实评测回归保留；现成管理和观测优先；备份/回退按批准恢复目标和事实损失，非预设高等级跨域。

## 五、实施边界与后续工程

本轮仅迁移架构基线。H 锁实际版本、许可、镜像/依赖、CI 风险、身份与 App 责任、必要接线和独立环境；W0 另批。实际改动按原生配置、可信扩展、资源/业务适配、必要核心修改分别记，不能承诺零 core 改动或虚构人日。若实际大量重写通用核心/长期 fork 且丧失复用收益，按[门禁](gates-and-risks.md)定向复核。供应商、具体中间件、模型、资源容量与成本不因主体选型自动获准。
