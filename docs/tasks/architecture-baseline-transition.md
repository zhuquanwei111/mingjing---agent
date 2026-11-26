# 架构基线过渡与 H2 接续

**状态：文档草稿交付；正式公共基座建设未获准。** 基线 main `aced61ac3855670478c33cc3cb5a1dcb9699ae3e`，任务分支 `docs/mastra-architecture-baseline-transition-20261126`。以 [当前架构](../designs/current-architecture-baseline.md) 和 [ADR 0002](../adr/0002-mastra-architecture-transition.md) 为唯一新路线入口，不创建第二套任务总账。实际 HEAD、PR 和 CI 使用时重新核对。

## 来源与归档边界

- F03 v1.1（2026-11-25，15 个文件）：总控此前核对 ZIP 内容及 14 个 SHA-256 条目一致，整包 SHA-256 `7ff9ffd25a54b237d0588cd987250c6d709eb0f3305f3ff5a324fc8c7ab05638`。本 PR 记录已裁决的架构摘要，不把摘要当完整交付。
- F04 独立报告：4 项阻断、11 项必要修订、合并 V01–V10；F03 R1 设计修订后 H/H1 定向核查。原件、版本及全部细表仍须通过受控交付归档；本公开仓库只保存经授权的非敏感摘要。
- H1 回执日期 2026-11-25，用户已提供正文；执行会话报告证据包 `MJ-ARCH-H1-evidence.tar.gz` 有 61 份材料及逐文件清单，SHA-256 `fb1671f8cafc189e69c78b6d76ca2af40c61a4954e9bfe0432a7d5982e0cb6b6`。当前仅取得回执正文及报告散列，没有直接取得原始压缩包、实验代码和日志，不能宣称校验通过或独立复跑。云机路径不当作公开可下载链接。H2 应交可独立取得的回执、脱敏证据包和代码，逐文件核验后按 docs 现有职责归档。
- [历史 PR #14 裁决](../designs/whole-product-decision.md)与[原始 76 项历史填证](../requirements/whole-product-acceptance-results.md)原判据/数据保留。历史 [Mastra PR #16](https://github.com/zhuquanwei111/mingjing---agent/pull/16) 采用不同 core 版本，不能与 H1 当作同一个试件。原件非公开部分不擅自提交。

<a id="h1-evidence"></a>

## H1 回执摘要（报告结果，未独立重验）

B01：core 1.84.0、pg 1.37.0，隔离 PostgreSQL 17.12、两个执行进程、可独立计数的模型及工具收端。固定 [Mastra 源码](https://github.com/mastra-ai/mastra/blob/10484e3b5544f0a160bc28446e4584be1a32c8e5/packages/core/src/agent/durable/durable-agent.ts) 和[原响应回放](https://github.com/mastra-ai/mastra/blob/10484e3b5544f0a160bc28446e4584be1a32c8e5/packages/core/src/agent/durable/workflows/steps/llm-execution.ts#L1689-L1719)。

| 机制 | 回执报告的观察 |
| --- | --- |
| 丢启动回执 | HTTP 响应 0 字节；另一进程按预绑定 ID 查到 running；重复启动拒绝，顶层 Run 1 条 |
| 相同输入不同回合 | 请求正文 hash 相同，原生步骤 0 和 1，两次合法请求执行 |
| 响应已存故障恢复 | 首轮落盘后终止，第二进程复用响应；模型实际收端 2 次、工具 1 次，无首轮重发 |
| 响应未存且不可查 | 恢复明确停止；模型 1 次、工具 0 次 |
| 旧 Worker | PG 代次递增，旧模型/工具出口均返回 403，下游新增接收 0 |

接受限定顶层动态机制结果，确认主体。必要适配为调用记录、原响应存取、派发认领、可撤销唯一出口；嵌套委派、并发、在途与真实供应商/G 仍待验。

B02：项目方明确后端尚未建设。建设顺序：Keycloak/OIDC 身份；SpiceDB 资源授权；Mastra Server 与 PG 稳定任务受理/Run 绑定；五出口及真实资源端终核；PG 操作查证与共享预算；独立交付及必要管理。中立资源/独立收端先实际验证公共机制，真实业务资源接口接入时另验。G 前必需公共宿主建成，不等待另一个不存在的后端。

B04：WeKnora v0.9.1 标准版、App/DocReader/PG/Redis、两测试租户、合成 PDF 和模型计数收端。固定[文件入队](https://github.com/Tencent/WeKnora/blob/71c32af9273482e0dad013d0e3bea2f4d719516c/internal/application/service/knowledge_create.go#L245-L261)与[解析构造](https://github.com/Tencent/WeKnora/blob/71c32af9273482e0dad013d0e3bea2f4d719516c/internal/infrastructure/docparser/grpc_parser.go#L141-L163)。

| 机制 | 回执报告的观察 |
| --- | --- |
| 同权限分区 | 双来源页两份均属 A，B 访问 A 库 403 |
| 撤回 | 原生重编后来源列表/检索已移除且旧摘要 404，但 Wiki 正文仍有撤回标记。关闭旧版后旧页/引用/缓存均 410 且 0 字节；空白分区只用剩余资料重建后标记消失 |
| 预算归属 | 新版 A2 模型请求归 A2，解析按文件摘要错归旧预算 A，原生解析请求号空；独立实例/队列/冻结清单的单批次 8 次模型、1 次解析可归同批次，逐次可信子作业绑定未证 |
| 发送与重试 | 共享试验 43 次模型/向量接收、5 次解析接收，报告原生队列及模型失败后的后台重试 |
| 额度耗尽 | 最后一单位产生 1 次接收；此后 24 次聊天、1 次向量、4 次解析尝试拒绝，下游新增接收 0 |

B04 不完整准入。禁止静态头/文件摘要归账，不凭来源列表重开旧页；独占同权限批次、旧版关闭与干净重建仅为部分证据。没有证明真实问答质量、全部来源闭包、实际付费、批次容量或所有内部请求可信归属。

## 下一步、并行 PR 与施工记录

| 日期/动作 | 状态 |
| --- | --- |
| 2026-11-25 F03 v1.1 / F04 / H | 架构设计及前置核查已交付，完整归档待取得 |
| 2026-11-25 H1 | 回执报告 B01 限定通过，B02 设计准备，B04 未完整准入；原始证据待核 |
| 2026-11-26 架构入口同步 | 本文档 PR；只调整导航、ADR、历史标识及阶段门槛；未修改代码 |
| H2 | 首先查上游真实修复、类似故障及成熟解决办法；合适时仅定向验证，提交知识库保留/修复/局部反转的证据与维护边界，不先逃避必要问题 |
| 最终批准与实施 | H2 收口、完整材料受控归档、目标环境/版本/许可/外发/费用/实际供应商合同明确并获准后，进入 W0a/W0b/G；G 后才 M |

已发现以下独立 PR；本任务不接管、不合并、不改动其分支。它们包含旧架构或共享文档，合并前须核对最新 main、处理语义/文本冲突并按各自规范复验：

- [#6 路线 B 候选开发包](https://github.com/zhuquanwei111/mingjing---agent/pull/6)：不能按旧栈直接开启新开发；保留可复用资产，后续由维护者裁决其处置。
- [#20 分阶段方案](https://github.com/zhuquanwei111/mingjing---agent/pull/20)、[#21 已审交付归档](https://github.com/zhuquanwei111/mingjing---agent/pull/21)：含共享 README/index/layout 或历史方案，更新/标记历史架构并确保 G-before-M，不把旧设计误标新实现。
- [#22 目录治理](https://github.com/zhuquanwei111/mingjing---agent/pull/22)：不因换线删除历史或仍有效规则。
- [#23 知识库](https://github.com/zhuquanwei111/mingjing---agent/pull/23)、[#24 身份权限](https://github.com/zhuquanwei111/mingjing---agent/pull/24)：保留专项责任，分别对齐 H2 及 B02 后端尚未建设的事实。
- [#26 问题解决优先](https://github.com/zhuquanwei111/mingjing---agent/pull/26)：独立规则草稿；不重复制定，合并前核对根 AGENTS 的兼容差异。

独立 Reviewer 应检查本候选的权威入口、原件与历史证据、H1 不外推、B04 未准入及正式阶段暂停的表述，并回流发现。按现有 CI `make check` / `P1 acceptance` 验证对应提交；旧 P1/P2 CI 不能证明新架构完成。独立评审及 CI 以实际回执为准，本次 GitHub 文档提交本身不计作通过；保持草稿，人工合并。
