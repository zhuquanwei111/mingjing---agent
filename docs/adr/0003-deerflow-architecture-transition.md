# ADR 0003：由 Mastra OSS 主体转入 DeerFlow 应用工程底座

- 状态：用户已确认主体选择；本 ADR 随基线迁移候选审查、人工合并后作为仓库正式决定。尚未批准实际制品部署或 W0 开工。
- 日期：2026-11-27（北京时间）。
- 替代：[ADR 0002](0002-mastra-architecture-transition.md) 的当前主体与冲突机制；保留其历史事实与证据。原旧主线 PR #27/#28 固定提交 `114af05ea6a24cde7f36d3e3dce7225234aa279a`。
- 依据：R3 独立最终裁决《00-最终独立裁决.md》推荐采用；《01-问题与依据.md》及《02-证据.csv》；R3 D01–D13 用户决定。原始交付包指纹见[基线施工记录](../tasks/architecture-baseline-transition.md)。

## 情境及决定

目标为完整明镜应用，而非理论最严的通用架构。历史 Mastra 方案有成熟运行层及 H1/H2 限定证据，但公共宿主未建、部分旧治理判据过重。R3 经用户调整不再强制普适即时撤权、所有历史派生追溯、统一执行账本、所有物理调用精确恢复/费用及预设复杂治理。相同标准比较 DeerFlow、LibreChat、Omnara 与 Mastra：DeerFlow 提供成套原生宿主、身份/owner、运行/工具、扩展及部分工作流/异步/知识接线，方向性公共工程复用收益较高；LibreChat 独立企业实践更强，保留优先备选。没有同条件净成本/稳定性测量，不虚构领先比例。决定采用 DeerFlow 主体而非保护旧投入，也不将其它组件的选择一并锁死。

## 边界、后果与验证

研究固定 v2.2.0 / `58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a`，具体安全制品和依赖/许可/镜像待 H；一个固定版后端 CI 分片失败，根因未取得。身份与实际业务授权、原生任务/工作流限制、真实知识 ACL、正式操作正确性和费用等按[契约](../designs/architecture-final/contracts.md)及[门禁](../designs/architecture-final/gates-and-risks.md)。A 原阻断按用户新口径解除，仍限定可行；B/C 限定可行；没有本项目新增运行实证。旧原件、P1/P2 及回归保留，不启动旧栈并行开发。具体组件/供应商按实际需要选择。

遵守[现行需求](../requirements/current-engineering-requirements.md)、[76项映射](../requirements/final-architecture-mapping.csv)、[当前架构](../designs/current-architecture-baseline.md)。本次基线迁移经独立审查及适用 CI 后用户人工合并，H/W0a/W0b/G/M/T/P 分开批准；必要 G、AC17 先于正式 M。若有真实证据表明严重不可修复缺陷、基本安全/必要业务无法实现或需广泛重写核心/重复建通用平台致净收益丧失，停止受影响工作并定向复核；个别供方缺口优先局部替代。回滚本次文档不自动恢复旧开工权。
