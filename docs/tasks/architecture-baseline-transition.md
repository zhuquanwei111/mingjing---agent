# 最终架构基线切换与工程证据

## 2026-11-27　DeerFlow 基线迁移

项目方已采纳 R3 最终独立裁决及 D01–D13。[PR #29](https://github.com/zhuquanwei111/mingjing---agent/pull/29) 已合并至 main，合并提交为 `c56b1e7cc82321a41a1495a036d41e7d72b6b925`。受审提交 `3e1e8b3a27aa24b6f50d5f8fa0ee2cd012d0c512` 通过[独立复审](https://github.com/zhuquanwei111/mingjing---agent/pull/29#issuecomment-7210702553)和[三项 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45946186146)。正式开发按[现行需求](../requirements/current-engineering-requirements.md)接续，W0 和业务开发仍待另批。

以下保留 #29 从基准 `114af05ea6a24cde7f36d3e3dce7225234aa279a` 起步的施工方案及当时记录。

1. 稳定现行架构、76 项映射及三张矩阵的入口，新增 ADR、现行需求与旧 Mastra 固定导航。逐项对照原 ID、R3 取舍、W0 A/B 场景和 G 十组实际效果。
2. 同步根规则、README、索引、开发流程和任务。仅覆盖旧规则与 R3 的明确冲突，保留原件、独立审查、真实敏感写入终核、旧运行回归及授权边界。
3. 核查文件清单、图源与派生图、链接与锚点、历史指纹，运行 `make check`，独立审查实际差异，按最终提交记录 ARM64 必需回归及两项 amd64 辅助结果。施工现场与最终证据可从已合并的 PR #29 追溯。
4. 人工合并前可关闭候选。合并后按批准回退此 PR 的文档变更，回退不授予旧路线开工权。本轮不部署制品或运行 W0。下一项是另行批准 H 制品及实施准备。

### 决定与证据定位

R3 的独立裁决在方案层确认 A（身份、资源权限与隔离）、B（异构能力共享）、C（知识、正式业务与费用）限定可行。原 A 阻断的解除来自项目方修订需求；评审没有新增明镜端到端运行试验。R2 未送独立评审。正式决定见 [ADR 0003](../adr/0003-deerflow-architecture-transition.md)，13 项生效修订、覆盖的旧要求及保留底线见[需求修订](../requirements/current-engineering-requirements.md)。[76 项映射](../requirements/final-architecture-mapping.csv)按原编号和原组保留追溯，并逐项给出可观察结果、证据来源和适用阶段。

下表中的原包由项目方保管。按包内相对路径、文件名及 SHA-256 可核对原件。公开仓库只收录正式决定、必要证据定位及限定结论。

| 受控原件与索引 | SHA-256 | 使用范围 |
| --- | --- | --- |
| MJ-DeerFlow-Codex 架构基线迁移交接包 | `472d3b6715220eadb570a0e39dbc841e40088acce1f6ab8308de569dcfe94ed0` | 09 清单的 33 件与实际长度、散列相符。07-证据定位.csv 中 M01–M25 为交接证据，另收录独立 Q01–Q24。 |
| 参考原件/01-MJ-DeerFlow-R3-最终独立裁决评审包.zip | `0d826d3152982017e6daf6784a94898563071b6c4d85299d61faf52363b078bc` | 02 为现行修订，05 为 76 项预映射，06-证据总索引.csv 的 E、I-E、R、N、D 共 150 条含继承记录；D01–D13 为项目方决定。 |
| 参考原件/02-MJ-DeerFlow-R3-最终独立裁决交付包.zip | `d0d2b1cc06aa128f00adce8a7afad92ac2bdca41fd5f216eb09e0fd5c1ac99dd` | 00 为最终意见，01 为逐问题论证，02-证据.csv 共 72 条。矩阵用 Q01–Q24 指向独立增补记录，E、N、R 等旧编号按上一行所列送审包的 06 索引查找。两表有继承，不能相加为实测数。 |
| 送审包内 v0.4.1 需求原件 | `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062` | 原始 FR、NFR、TS、AC 编号和未修订要求保留；修订只覆盖与 D01–D13 明确冲突处。 |

**可公开核查的关键证据。** 已复核研究版 [v2.2.0](https://github.com/bytedance/deer-flow/releases/tag/v2.2.0) 标签指向 `58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a`；同一提交的[后端分片 2](https://github.com/bytedance/deer-flow/actions/runs/41787895350/job/126434505342)结论为失败。R3 的[授权配置](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/packages/harness/deerflow/config/authorization_config.py)、[后台运行合同](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/backend/docs/extension-agent-runs.md)和[WeKnora 扩展实测报告](https://github.com/bytedance/deer-flow/blob/58fc5bd5b8e6ea46538e9481ba06ca2a46e14e2a/examples/deerflow-extension-weknora/VALIDATION.md)分别说明显式启用授权、重启后授权句柄的限制，以及 v0.8.3 合成资料检索的证据边界。

### 开工条件与接续

| 编号 | 当前状态与下次需要的证据 |
| --- | --- |
| U01 制品 | H 核实失败分片的影响、可维护的修复制品、镜像摘要、组件许可和回退。研究版未获部署批准。 |
| U02 现场 | 已核干净主工作区、独立分支、远端 main、实际保护规则。继续旧分支前重新核对差异。#20/#23/#24 已关闭且未合并；#21/#22/#26/#27/#28 已合并。 |
| U03 接入 | 项目方已确认应用后端尚未建设。必要可信接入归公共基座，H/W0 确认真实身份源、对象和目的地。 |
| U04 执行 | H/W0/G 确认共享业务接口、确需无人值守的时效和持久任务责任。 |
| U05 知识 | H/G 确认实际供方、版本、知识访问控制、许可及适用的中文、复杂版面和多媒体质量。 |
| U06 使用条件 | 模型/外服合同、硬费用限额、真实负载、值守和恢复目标按 H/G/T/P 实测或获批。 |
| U07 实证 | H1/H2 归档保留原正反例，本次未取得其受控运行日志重新取证；DeerFlow W0/G 及业务均未签收。 |
| U08 维护 | 后续记录实际原生复用、配置、扩展和核心改动及升级负担。必要业务若迫使重写运行核心，先核上游修复或局部替代，再提交定向裁决。 |

### 本次施工核对

独立迁移方案审查对应 `f7b8b2ff661f6f86127e1eece6d43c252e7d79c0`，结论通过。依据评审意见，历史 H1/H2 链接固定到原提交；两种展示图均从同一灰阶 Mermaid 源渲染，保留运行、业务与知识证据三条连线；跨期逐项分列隔离与真实业务证据。文件级清单 56 个非归档路径中，55 个 blob 与固定树逐字相符；通用评审配置路径 `engineering-standard/agents/solution-reviewer.toml` 的清单值漏写 `ace5`，现场 blob 为 `efc421a36fe043e33ba85b9a04e25895bace5fee`，两份评审配置内容相同且均保留原件。

旧归档 16 件 v1 规则和方案、12 件路线 B 资料、9 件设计原件 ZIP 与旧运行回归保留。178 个历史运行路径中，两份仍被开发入口直接引用的 README 校正导航措辞，原版可在[固定归档树](https://github.com/zhuquanwei111/mingjing---agent/tree/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/archive/legacy-runtime)逐件核查。现有 CI、运行代码、锁文件和 Makefile 继续承担原回归职责。服务器实际必需检查为 ARM64 `P1 acceptance`，包括 P1 恢复与 P2 公共层，另有两项 amd64 辅助回归。实施复审、整改、最终提交和同版 CI 登记在[PR #29](https://github.com/zhuquanwei111/mingjing---agent/pull/29)，合并结果见本节开头。

独立实施审查比对 `3d2abedbe48bebc4d51cb8be2ea37f0d91e93703` 和基准，要求修正 H-A 的撤权措辞，以及 FR-15/21/26 的中立测试边界。现行门禁已限定按具体风险决定即时阻断；W0/G 用测试身份与可独立查证的中立资源，实际复盘、预约及岗位结果在另批 M 取证。另已澄清下文离线对账发生于 #27。

项目方在 #29 明确 D05 的图示语义。普通业务直查在图中只占一条调用线；DeerFlow 作为唯一主体承载 Agent，并优先承载适用工作流、异步任务与调度。正式需求、契约、技术/机制表和验收映射同步体现两类调用，从同一 Mermaid 源重绘展示图，按此修订重新独审与验证。

## 2026-11-26　Mastra 历史归档

以下各节均记录 #27 及更早版本当时的工作、证据、权限与后续计划。DeerFlow 接续只使用本页上方的决定、未决清单及其现行入口。

**当时任务状态**　总控已完成选型，架构基线经 [#27](https://github.com/zhuquanwei111/mingjing---agent/pull/27) 审核并合入主分支（提交 `3828592`）。改动限于架构及工程文档。进入公共基座正式建设仍需项目方批准。

## 可追溯原件与公开范围

项目方持有本次会话附件 `MJ-ARCH-FINAL-执行会话完整交接包.zip`，整包 SHA-256 为 `e02759806467a496b0025b788e2258b12f7de46523d9045717990c339a4e2b37`。从包根的 `00-阅读索引.md` 和 `SHA256SUMS.txt` 进入，以下路径相对于总包。公开仓库保存经审核的技术选择、合成计数、失败结论及散列。受控原包内的实验代码、日志、凭据相关配置、环境标识与真实需求原件由项目方保管，不随公开 PR 分发。

| 文件或目录 | SHA-256 / 核对范围 |
| --- | --- |
| 总包校验清单 | 8 项原字节逐项一致。两个历史 ZIP 仅供追溯。 |
| 01-正式架构与评审 / F03 v1.1 最终送审 ZIP | `7ff9ffd25a54b237d0588cd987250c6d709eb0f3305f3ff5a324fc8c7ab05638`；内部 14 项一致。 |
| 同目录 F04 独立综合报告 | `7c07ec4327c276ba7c239684f7208311dcf3904b026ec5e5d7c47b586670e7e3`；B01–B04、S01–S11、V01–V10 分别归入实施入口及风险。 |
| 02-前置核查与实际证据 / H 核查回执 | `d0ead67a7c9097e1e97c3ce2249d56a7a3ca2e2790bab04f09e6c8aacc7fed1b`；属固定接口与实施前置核查。 |
| 同目录 MJ-ARCH-H2-delivery.zip | `4b3a0becc8626952aef469130987de6931b9bceb4ac306e8b9a88cfeeab5d7cb`；内层 `SHA256SUMS` 的 26 项一致。 |
| H2 内 H1/MJ-ARCH-H1-evidence.tar.gz | `fb1671f8cafc189e69c78b6d76ca2af40c61a4954e9bfe0432a7d5982e0cb6b6`；包内 `evidence-SHA256SUMS` 的 61 项一致。相邻 H1 回执为 `327aaa10ae8aa62ba8b4020353ffa18750f33ac0eded9b728ea60e7cbf0f6f6c`。 |
| H2 内 H2/evidence/H2-results.json | `e44589a1877e97f15f89f23f918459cfe002e7fd7bb1445f23823d76b042fbc5`；可按 H2/RUN.md 离线重核收端、重试、拒绝和发布观察。 |

需求单独核对项目方《明镜智能体应用_通用工程架构需求说明书_v0.4.1_合并版.docx》，其字节 SHA-256 为 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`，与 F04 原件记录一致。正文 41 FR、11 NFR、7 TS、17 AC 共 76 个唯一编号与 F03/06、[固定 23 组阶段索引](https://github.com/zhuquanwei111/mingjing---agent/blob/210a24f240c73e86746e608907242a200fc94cc0/docs/requirements/whole-product-phase-index.md)逐号相合。原件的四面、核心对象、分阶段及容量/成本待定条款仍适用。新的[76 项映射](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/requirements/final-architecture-mapping.csv)保留原组、可观察判据及 G 前的独立盲接；历史填证表保持原貌。

<a id="h1-evidence"></a>

## H1 限定实测与失败记录（原包已核，未重新运行服务）

B01：core 1.84.0、pg 1.37.0，隔离 PostgreSQL 17.12、两个执行进程、可独立计数的模型及工具收端。固定 [Mastra 源码](https://github.com/mastra-ai/mastra/blob/10484e3b5544f0a160bc28446e4584be1a32c8e5/packages/core/src/agent/durable/durable-agent.ts) 和[原响应回放](https://github.com/mastra-ai/mastra/blob/10484e3b5544f0a160bc28446e4584be1a32c8e5/packages/core/src/agent/durable/workflows/steps/llm-execution.ts#L1689-L1719)。

| 机制 | 回执报告的观察 |
| --- | --- |
| 丢启动回执 | HTTP 响应 0 字节；另一进程按预绑定 ID 查到 running；重复启动拒绝，顶层 Run 1 条 |
| 相同输入不同回合 | 请求正文 hash 相同，原生步骤 0 和 1，两次合法请求执行 |
| 响应已存故障恢复 | 首轮落盘后终止，第二进程复用响应；模型实际收端 2 次、工具 1 次，无首轮重发 |
| 响应未存且不可查 | 恢复明确停止；模型 1 次、工具 0 次 |
| 旧 Worker | PG 代次递增，旧模型/工具出口均返回 403，下游新增接收 0 |

当时据此确认 Mastra 的限定顶层动态机制。必要适配为调用记录、原响应存取、派发认领、可撤销唯一出口；嵌套委派、并发、在途与真实供应商/G 仍待验。

B02：项目方明确后端尚未建设。建设顺序：Keycloak/OIDC 身份；SpiceDB 资源授权；Mastra Server 与 PG 稳定任务受理/Run 绑定；五出口及真实资源端终核；PG 操作查证与共享预算；独立交付及必要管理。中立资源/独立收端先实际验证公共机制，真实业务资源接口接入时另验。G 前必需公共宿主建成，不等待另一个不存在的后端。

B04：WeKnora v0.9.1 标准版、App/DocReader/PG/Redis、两测试租户、合成 PDF 和模型计数收端。固定[文件入队](https://github.com/Tencent/WeKnora/blob/71c32af9273482e0dad013d0e3bea2f4d719516c/internal/application/service/knowledge_create.go#L245-L261)与[解析构造](https://github.com/Tencent/WeKnora/blob/71c32af9273482e0dad013d0e3bea2f4d719516c/internal/infrastructure/docparser/grpc_parser.go#L141-L163)。

| 机制 | 回执报告的观察 |
| --- | --- |
| 同权限分区 | 双来源页两份均属 A，B 访问 A 库 403 |
| 撤回 | 原生重编后来源列表/检索已移除且旧摘要 404，但 Wiki 正文仍有撤回标记。关闭旧版后旧页/引用/缓存均 410 且 0 字节；空白分区只用剩余资料重建后标记消失 |
| 预算归属 | 新版 A2 模型请求归 A2，解析按文件摘要错归旧预算 A，原生解析请求号空；独立实例/队列/冻结清单的单批次 8 次模型、1 次解析可归同批次，逐次可信子作业绑定未证 |
| 发送与重试 | 共享试验 43 次模型/向量接收、5 次解析接收，报告原生队列及模型失败后的后台重试 |
| 额度耗尽 | 最后一单位产生 1 次接收；此后 24 次聊天、1 次向量、4 次解析尝试拒绝，下游新增接收 0 |

上述 H1 的共享后台路径未通过。H2 使用新的批次接入方式验证了下列边界，原负例仍保留。

## H2 补充实测与最终裁决

固定 WeKnora v0.9.1（`71c32af9273482e0dad013d0e3bea2f4d719516c`）。同租户、一个 App/原生队列/DocReader，全程 App 重启 0 次。A 从两份合成 PDF 编出双来源页；将 A 批预算清零后在空白 B 只导入仍获准的同字节 PDF。签发的批次凭据随文档解析配置持久化并传给 DocReader，模型凭据固定到版本。收端观察如下。

| 观察项 | 原始记录支持的结果 |
| --- | --- |
| 物理计数 | 30 次准入对应 27 次模型/向量接收、3 次 PDF 解析。A 为 11 聊天、5 向量、2 解析；B 为 8 聊天、3 向量、1 解析。同字节原件在两批各记入正确父预算。 |
| 拒绝与重试 | A 批预算清零、B 活动期间，A 的 4 次解析和 1 次向量尝试在下游前被拒，A 新增接收 0。B 的摘要模型首次受控返回 503，原生阶段由失败重试到完成。 |
| 新版读回 | B 的新 Wiki 引用与检索命中只含合法来源，撤回标记消失、保留标记可见。旧发布的读入口由 H1 实测关闭（旧页/旧引用/预热缓存均 410、零字节）；H2 的 A 切换动作实际是清零父预算。 |
| 证据边界 | 没有两批同时活动的并发证明，没有逐物理模型调用的原生子作业 ID 保证。请求单位、合成模型与两份 PDF 不能证明实际收费、复杂资料质量、生产负载或完整权限。 |

当时总控限定采用 WeKnora v0.9.1。[上游已合并修复](https://github.com/Tencent/WeKnora/pull/5186)处理重解析误删；[索引修复](https://github.com/Tencent/WeKnora/pull/5024)保留更新失败前的旧内容；[后台费用议题](https://github.com/Tencent/WeKnora/issues/3258)不能提供发包前预算。完整上游修复状态、合并提交与首个适用版本见受控 H2 包的《上游核对表》。合并状态按 H2 固定时点记录。局部适配和剩余 G 判据见[知识契约](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/contracts.md)及[风险表](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/gates-and-risks.md)。

## 施工记录与接续

| 时间 | 可核记录与动作 |
| --- | --- |
| 2026-11-25 | F03 v1.1 修订 F04 设计；H 核固定接口，H1 作限定实验并保留 B04 负例。 |
| 2026-11-26 过渡 | PR #27 的 `de70569` 记录 H1 当时可见范围。该版[独立复审](https://github.com/zhuquanwei111/mingjing---agent/pull/27#issuecomment-7181281866)与[同版 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45745396068)只证明当轮文档修复和旧仓库回归。 |
| 2026-11-26 最终基线 | 读取受控原件及最新裁决，校验嵌套包，更新选型、开发边界、风险、76 项与可编辑 SVG。最终候选、复审回执与同版 CI 已随 #27 归档。 |
| 合并与开工 | 总控审核通过，#27 已合并。正式建设待项目方另行批准。首项是按建设清单确认目标环境和受控供方、搭建真实中立宿主，W0a 全部通过才入 W0b。G 全部必需项通过并另获 M 授权后开始首个正式业务。 |

以下清单保留 #27 交审时对并行 PR 的处理要求。其后 #21、#22、#26 已合并，#6、#20、#23、#24 已关闭，固定来源继续供追溯。

- [#6 路线 B 候选开发包](https://github.com/zhuquanwei111/mingjing---agent/pull/6)：不能按旧栈直接开启新开发；保留可复用资产，后续由维护者裁决其处置。
- [#20 分阶段方案](https://github.com/zhuquanwei111/mingjing---agent/pull/20)、[#21 已审交付归档](https://github.com/zhuquanwei111/mingjing---agent/pull/21)：含共享 README/index/layout 或历史方案，更新/标记历史架构并确保 G-before-M。#20 原 E1（独立能力接入）规定最迟首个未知实现类型放行前，须纠正 AC-17 为稳定 G 基座后、首个 M 之前的硬门槛；#21 保留已审原件指纹，不把旧设计误标新实现。
- [#22 目录治理](https://github.com/zhuquanwei111/mingjing---agent/pull/22)：与本次修订共改[目录任务](directory-governance.md)。#22 独有迁移清单与历史原件必须保留；目标基线含 #27 后核对实际 main/head，安全合入本次现行入口、历史标记及新旧阶段衔接，处理冲突并复验，不恢复旧路线。
- [#23 知识库](https://github.com/zhuquanwei111/mingjing---agent/pull/23)、[#24 身份权限](https://github.com/zhuquanwei111/mingjing---agent/pull/24)：保留专项责任，分别对齐 H2 及 B02 后端尚未建设的事实。
- [#26 问题解决优先](https://github.com/zhuquanwei111/mingjing---agent/pull/26)：独立规则草稿；不重复制定，合并前核对根 AGENTS 的兼容差异。

## PR #27 独立评审与修订

独立评审固定读取候选 `7240ab2`、需求原件与 F03/H1/H2，提出四项修订。已恢复四个逻辑面的正式发布权威；澄清 PG 与成熟预留/权益组件的取舍；按测量点分列 H1 的旧读入口与 H2 的预算关闭和干净重建；补足 Hop 样本与真实行质检的区分、S3 同键覆盖与固定字节保护。对应行及证据范围随本 PR 复审，最终 head、复审回执和同版 CI 见 PR 审核记录。

## 过渡版独立评审回流及整改（历史记录）

[独立评审回执](https://github.com/zhuquanwei111/mingjing---agent/pull/27#issuecomment-7181160254)对应 base `aced61ac3855670478c33cc3cb5a1dcb9699ae3e`、旧 head `2225b8d5775a56bef3d5c9051cd1194595705352`；由独立 solution_reviewer 回流，结论暂不建议合并，两个发现均由原执行者接受。

| 发现 | 本次实际处置 | 复审要求 |
| --- | --- | --- |
| P1 旧路线仍被活跃文档指引 | 修订[目录治理任务](directory-governance.md)当前状态、历史定位和可执行后续清单；[P2 手册](../archive/legacy-runtime/core/README.md)明确旧实现维护/历史复用范围并导向现行入口。保留原历史事实及已有运行命令。#22 后续同步事项已列明。 | 核对旧入口不再误指新建设、迁移责任与历史证据保留 |
| P2 执行类型与开发阶段同名 | F03 原执行类型 P0–P3 一一改记 EXEC-0–EXEC-3（不用 #20 已有 E1 等阶段编号）；[根规则](../../AGENTS.md)链接[新旧开发阶段衔接](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/current-architecture-baseline.md#stage-gate-crosswalk)，旧门禁与 H/W0/G/M/T/P 并用，P1 验收确认后 G，G 全部必要能力及 AC-17 通过且获准才 M；原规则文件与 CI 名称不改。 | 核对阶段语义无重叠、旧门禁未削弱，实施仍暂停 |

过渡阶段两个 head 的回归与独立复审以各自固定提交为准。当时缺少的材料后来在 #27 交付时补齐，见[固定历史回执](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/tasks/architecture-baseline-transition.md)。#27 当时在临时副本分别执行 H1 的 verify-evidence.py 和 H2 的 check.py，只对已有记录离线对账，两份输出都与原 results JSON 逐字节一致。未重新运行原实验服务。
