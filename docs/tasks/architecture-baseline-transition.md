# 最终架构基线切换与工程证据

**任务状态**　总控已完成选型，独立分支以 Draft PR [#27](https://github.com/zhuquanwei111/mingjing---agent/pull/27) 交审。改动限于架构及工程文档。进入公共基座正式建设仍需项目方批准。

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

需求单独核对项目方《明镜智能体应用_通用工程架构需求说明书_v0.4.1_合并版.docx》，其字节 SHA-256 为 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`，与 F04 原件记录一致。正文 41 FR、11 NFR、7 TS、17 AC 共 76 个唯一编号与 F03/06、[固定 23 组阶段索引](https://github.com/zhuquanwei111/mingjing---agent/blob/210a24f240c73e86746e608907242a200fc94cc0/docs/requirements/whole-product-phase-index.md)逐号相合。原件的四面、核心对象、分阶段及容量/成本待定条款仍适用。新的[76 项映射](../requirements/final-architecture-mapping.csv)保留原组、可观察判据及 G 前的独立盲接；历史填证表保持原貌。

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

上述 H1 的共享后台路径未通过。H2 使用新的批次接入方式验证了下列边界，原负例仍保留。

## H2 补充实测与最终裁决

固定 WeKnora v0.9.1（`71c32af9273482e0dad013d0e3bea2f4d719516c`）。同租户、一个 App/原生队列/DocReader，全程 App 重启 0 次。A 从两份合成 PDF 编出双来源页；关闭 A 后在空白 B 只导入仍获准的同字节 PDF。签发的批次凭据随文档解析配置持久化并传给 DocReader，模型凭据固定到版本。收端观察如下。

| 观察项 | 原始记录支持的结果 |
| --- | --- |
| 物理计数 | 30 次准入对应 27 次模型/向量接收、3 次 PDF 解析。A 为 11 聊天、5 向量、2 解析；B 为 8 聊天、3 向量、1 解析。同字节原件在两批各记入正确父预算。 |
| 拒绝与重试 | 关闭 A、B 活动期间，A 的 4 次解析和 1 次向量尝试在下游前被拒，A 新增接收 0。B 的摘要模型首次受控返回 503，原生阶段由失败重试到完成。 |
| 新版读回 | B 的新 Wiki 引用与检索命中只含合法来源，撤回标记消失、保留标记可见。H1 的旧链接、旧引用、预热缓存已实测关闭。 |
| 证据边界 | 没有两批同时活动的并发证明，没有逐物理模型调用的原生子作业 ID 保证。请求单位、合成模型与两份 PDF 不能证明实际收费、复杂资料质量、生产负载或完整权限。 |

总控限定采用 WeKnora。[上游已合并修复](https://github.com/Tencent/WeKnora/pull/5186)处理重解析误删；[索引修复](https://github.com/Tencent/WeKnora/pull/5024)保留更新失败前的旧内容；[后台费用议题](https://github.com/Tencent/WeKnora/issues/3258)不能提供发包前预算。完整上游修复状态、合并提交与首个适用版本见受控 H2 包的《上游核对表》。合并状态按 H2 固定时点记录。局部适配和剩余 G 判据见[知识契约](../designs/architecture-final/contracts.md)及[风险表](../designs/architecture-final/gates-and-risks.md)。

## 施工记录与接续

| 时间 | 可核记录与动作 |
| --- | --- |
| 2026-11-25 | F03 v1.1 修订 F04 设计；H 核固定接口，H1 作限定实验并保留 B04 负例。 |
| 2026-11-26 过渡 | PR #27 的 `de70569` 记录 H1 当时可见范围。该版[独立复审](https://github.com/zhuquanwei111/mingjing---agent/pull/27#issuecomment-7181281866)与[同版 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45745396068)只证明当轮文档修复和旧仓库回归。 |
| 2026-11-26 最终基线 | 读取受控原件及最新裁决，校验嵌套包，更新选型、开发边界、风险、76 项与可编辑 SVG。当前候选 SHA、独立评审结果和该提交 CI 随本 PR 交付。 |
| 合并与开工 | 待总控审核和人工合并，再由项目方明确建设授权。首项是按建设清单确认目标环境和受控供方、搭建真实中立宿主，W0a 全部通过才入 W0b。G 全部必需项通过并另获 M 授权后开始首个正式业务。 |

已发现以下独立 PR；本任务不接管、不合并、不改动其分支。它们包含旧架构或共享文档，合并前须核对最新 main、处理语义/文本冲突并按各自规范复验：

- [#6 路线 B 候选开发包](https://github.com/zhuquanwei111/mingjing---agent/pull/6)：不能按旧栈直接开启新开发；保留可复用资产，后续由维护者裁决其处置。
- [#20 分阶段方案](https://github.com/zhuquanwei111/mingjing---agent/pull/20)、[#21 已审交付归档](https://github.com/zhuquanwei111/mingjing---agent/pull/21)：含共享 README/index/layout 或历史方案，更新/标记历史架构并确保 G-before-M。#20 原 E1（独立能力接入）规定最迟首个未知实现类型放行前，须纠正 AC-17 为稳定 G 基座后、首个 M 之前的硬门槛；#21 保留已审原件指纹，不把旧设计误标新实现。
- [#22 目录治理](https://github.com/zhuquanwei111/mingjing---agent/pull/22)：与本次修订共改[目录任务](directory-governance.md)。#22 独有迁移清单与历史原件必须保留；目标基线含 #27 后核对实际 main/head，安全合入本次现行入口、历史标记及新旧阶段衔接，处理冲突并复验，不恢复旧路线。
- [#23 知识库](https://github.com/zhuquanwei111/mingjing---agent/pull/23)、[#24 身份权限](https://github.com/zhuquanwei111/mingjing---agent/pull/24)：保留专项责任，分别对齐 H2 及 B02 后端尚未建设的事实。
- [#26 问题解决优先](https://github.com/zhuquanwei111/mingjing---agent/pull/26)：独立规则草稿；不重复制定，合并前核对根 AGENTS 的兼容差异。

## 过渡版独立评审回流及整改（历史记录）

[独立评审回执](https://github.com/zhuquanwei111/mingjing---agent/pull/27#issuecomment-7181160254)对应 base `aced61ac3855670478c33cc3cb5a1dcb9699ae3e`、旧 head `2225b8d5775a56bef3d5c9051cd1194595705352`；由独立 solution_reviewer 回流，结论暂不建议合并，两个发现均由原执行者接受。

| 发现 | 本次实际处置 | 复审要求 |
| --- | --- | --- |
| P1 旧路线仍被活跃文档指引 | 修订[目录治理任务](directory-governance.md)当前状态、历史定位和可执行后续清单；[P2 手册](../../core/README.md)明确旧实现维护/历史复用范围并导向现行入口。保留原历史事实及已有运行命令。#22 后续同步事项已列明。 | 核对旧入口不再误指新建设、迁移责任与历史证据保留 |
| P2 执行类型与开发阶段同名 | F03 原执行类型 P0–P3 一一改记 EXEC-0–EXEC-3（不用 #20 已有 E1 等阶段编号）；[根规则](../../AGENTS.md)链接[新旧开发阶段衔接](../designs/current-architecture-baseline.md#stage-gate-crosswalk)，旧门禁与 H/W0/G/M/T/P 并用，P1 验收确认后 G，G 全部必要能力及 AC-17 通过且获准才 M；原规则文件与 CI 名称不改。 | 核对阶段语义无重叠、旧门禁未削弱，实施仍暂停 |

过渡阶段两个 head 的回归与独立复审以各自固定提交为准。当时未取得完整材料的限制已由本次受控原包及逐项核验补齐，见本页开头。本次在临时副本分别执行 H1 的 verify-evidence.py 和 H2 的 check.py，只对已有记录离线对账，两份输出都与原 results JSON 逐字节一致。未重新运行原实验服务。
