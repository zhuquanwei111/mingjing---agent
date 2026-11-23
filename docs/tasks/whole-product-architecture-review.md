# 完整产品架构复审任务

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
