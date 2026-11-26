# 完整产品架构复审任务

> **历史任务记录。** 下文记录当时的审查和裁决，不是新任务授权。接续新架构请从[架构过渡任务](architecture-baseline-transition.md)和[现行架构](../designs/current-architecture-baseline.md)进入。

目标是决定整个明镜智能体开发可依赖的架构，而非批准功能开发。以 v0.4.1 原件（SHA-256 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`）、R4 固定 `9d61564347dbea5ada09678c1aa8b9d16f36a2df` 和原 23 组/76 个编号为准。PR #7 在本轮进行期间由仓库端合入 main；本轮审查在单独分支 `codex/whole-product-architecture-review-20261123`，其文档草稿为 [#14](https://github.com/zhuquanwei111/mingjing---agent/pull/14)。旧 W0 裁决及原冻结表作固定输入。

[设计者逐组分析与责任边界](../designs/whole-product-review.md) · [扩大候选及入围依据](../designs/whole-product-alternatives.md)

| 独立草稿 | 比较目的与当前记录 |
| --- | --- |
| [#12](https://github.com/zhuquanwei111/mingjing---agent/pull/12) | B 的真实工具回合中断，正式用例先于代码冻结。5 个在途 Activity、2 次迟到复核，已归档、独立代码与结果复核通过。 |
| [#13](https://github.com/zhuquanwei111/mingjing---agent/pull/13) | 完整应用 Windmill，原生作业/Agent、治理网关和供方终局分开记录。 |
| [#15](https://github.com/zhuquanwei111/mingjing---agent/pull/15) | 比较 DBOS 是否能以嵌入式执行和 PostgreSQL 替换一个独立工作流服务。 |
| [#16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) | 自托管 Mastra 原生持久 Agent，验证替代 Python Agent 与独立编排运行时的实际边界。 |
| [#17](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | Agno AgentOS 的公开外部执行/续跑接口，验证完整应用宿主、持久运行及业务接收出口。 |

每条路线使用独立工程、服务和合成数据。为避免分数失真，确认工具业务实际效果和收费、原调用配对、取消后的模型实收及交付；逐项标明其适配与未测范围。未知结果、不能启动的装置和真实不合格分别记录。评审完成后只更新技术决策和证据，W0 实施、MVP 和真实流量继续暂停。

## 同题证据与独立评审

[总决策、具体验收条件和全产品独立裁决入口](../designs/whole-product-decision.md)。本轮 #12、#13、#15、#16、#17 的定向集成均有成功记录和固定测试代码。启动、编排和观察装置的失败及改动保留在各草稿；旧 W0 的标准和证据范围保留。整体裁决以本任务草稿 PR 的固定修订和独立回流为准。

[B 原始记录](https://github.com/zhuquanwei111/mingjing---agent/tree/554367bf8528a9500a88bac4033ad15a5983b4de/lab/product-review/evidence/45190768318) · [Windmill 报告](https://github.com/zhuquanwei111/mingjing---agent/blob/c847da6c10608f33ba0d88277d20400885afc04d/lab/windmill-native/REPORT.md) · [DBOS 报告及失败记录](https://github.com/zhuquanwei111/mingjing---agent/blob/75d6fccf821c5ebcd70cd837f8fa52a3e78cf936/lab/dbos/RESULT.md) · [Mastra 报告与完整锁](https://github.com/zhuquanwei111/mingjing---agent/blob/a9b6570419f6f6877e824a4abcb889e3867e6517/lab/mastra/RESULT.md) · [Agno 报告与原始事件](https://github.com/zhuquanwei111/mingjing---agent/blob/60dc1965c4cea6d4e976ed40875f82403dbb386f/lab/agno-agentos/REPORT.md)

首轮总评独立裁决暂缓，设计者接受并开出两个可隔离复测的窗口。两项均有明确失败去向和复审条件。见[固定受审稿](https://github.com/zhuquanwei111/mingjing---agent/commit/5a3c2c5cf2c00509e503fc4b44280390b0409bf5)。

逐编号填证、23 组候选横向对照、方案判断按[原表验证结果](../requirements/whole-product-acceptance-results.md)回流。计费观测只作为特定硬门槛的证据。首轮暂缓的两个窗按 [#12 事前预注册](https://github.com/zhuquanwei111/mingjing---agent/blob/041c9683df779732b82f3e9c8161e509bac9dcbd/lab/product-review/round-gate/PLAN.md)执行。

独立验收审查按原件和冻结主表，要求统一正式交付故障的 W0a 时点、拆出模型/工具两种实际传输、为 A/B 写入对称的真实模型和扩展证据、移除原件未要求的无限类型零改动标准。已按固定记录修正。#12 的两个相邻窗口、旧回归与持久原件已进入逐编号表。

最终独立总评对 8a26591 和 #12 固定证据裁决“调整指定组件后采纳路线 B 为完整产品开发基线”。原件逐号独审独立完成全表实质复核和四点修正复验。目标正式 W0、MVP 实施未开始。

## 证据复查

| 实验归档提交 | 同一提交重新运行的定向验收 | 同一提交的仓库回归 |
| --- | --- | --- |
| [#13 · c847da6c](https://github.com/zhuquanwei111/mingjing---agent/pull/13) | [真实集成 45193190934](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193190934) | [Verify 45193190978](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45193190978) |
| [#15 · 75d6fccf](https://github.com/zhuquanwei111/mingjing---agent/pull/15) | [真实集成 45194266215](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194266215) | [Verify 45194266672](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194266672) |
| [#16 · a9b65704](https://github.com/zhuquanwei111/mingjing---agent/pull/16) | [真实集成 45194249778](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194249778) | [Verify 45194249601](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194249601) |
| [#17 · 60dc1965](https://github.com/zhuquanwei111/mingjing---agent/pull/17) | [真实集成 45194292791](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194292791) | [Verify 45194292841](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45194292841) |

[#12 补测归档提交的复跑](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45196243746) · [同一提交原用例复跑](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45196243719) · [仓库 Verify](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45196244064)
