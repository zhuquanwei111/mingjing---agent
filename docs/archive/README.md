# 明镜历史方案与证据

新任务从[现行需求](../requirements/current-engineering-requirements.md)、[76 项映射](../requirements/final-architecture-mapping.csv)和[DeerFlow 架构入口](../designs/current-architecture-baseline.md)接续。下表说明历史材料保留什么，以及开发时如何使用。

| 材料 | 保留用途 |
| --- | --- |
| [Mastra 方案与 H1/H2](mastra-20261126/README.md) | 在固定提交查当时的契约、供应商版本、试验范围与失败记录；新的工程判据按 R3 生效修订执行。 |
| [路线 B 与 PR #14](route-b/designs/whole-product-decision.md) | 追溯早期需求、技术比较、裁决及局部实验。 |
| [v1 工程包](engineering-v1/README.md) | 旧选型供追溯。[原工程规则](engineering-v1/AGENTS.md)仍由[根 AGENTS](../../AGENTS.md)加载，冲突条款按现行需求执行。 |
| [P1/P2 运行回归](legacy-runtime/README.md) | 复现旧实现和故障结果。仓库 CI 仍从这里运行，DeerFlow 的 W0/G 另行取证。 |
| [九件首期与 W0 设计原件](../tasks/reviewed-deliverables.md) | 核验首期范围、旧宿主设计、原始字节和固定来源；现行阶段按[门禁](../designs/architecture-final/gates-and-risks.md)签收。 |

早期知识库和身份专项分别在已关闭的 [PR #23](https://github.com/zhuquanwei111/mingjing---agent/pull/23) 和 [PR #24](https://github.com/zhuquanwei111/mingjing---agent/pull/24)。其中[已确认的知识库岗位需求](https://github.com/zhuquanwei111/mingjing---agent/blob/7575c06a0431c1289cfddb702eef3ae5e839a9fd/docs/requirements/knowledge-base-requirements.md)继续按[现行适用说明](../requirements/current-engineering-requirements.md#知识库岗位需求如何沿用)使用。旧选型和运行试验可按当时的版本查证。
