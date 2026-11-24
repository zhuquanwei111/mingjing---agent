# 机构知识库选型提案

**已确认的范围是下表五层分类。每层的实现、产品、模型和淘汰线均待评审。** 此稿用于比较方案和出题。正式搭建另由项目方批准。明镜现有路线 B 的任务入口和业务权威继续适用。[架构终裁](whole-product-decision.md) · [固定阶段方案](https://github.com/zhuquanwei111/mingjing---agent/blob/210a24f240c73e86746e608907242a200fc94cc0/docs/designs/whole-product-phased-implementation.md) · [组件选择原稿](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/designs/whole-product-component-selection.md)

## 业务材料从哪里来

设计覆盖机构制度与协作、主播经纪与培养、内容与素材、直播与制作、商务与交付、经营财务与合规、行业研究与组织经验。约 300 名潜在用户是规模背景，实际岗位、场次、资料量及负载有待采样。资料按原件、授权对象、项目、版本、生效时间和衍生引用关联，同一知识可供多个岗位使用。

- 长鲸传媒在策划、排练、妆造、运镜和复盘间使用视频回看。需要区分“说过”与“画面确实做到”，并能回到原片时段。[团队访谈](https://eu.36kr.com/zh/p/3556682743463042)
- 据泰洋川禾披露，一次大促的 20 场直播约有 80 份复盘文档，团队从多场记录整理岗位手册。需要区分单次有效的经验、现行制度和历史制度。[团队访谈](https://i.ifeng.com/c/87SwREinH1B)
- 二咖传媒客户案例描述了多地达人合同归档、商单协作与行业资料共享。需要分别判断资料能否查看、能否跨客户复用、能否再次交付。客户案例由工具供应商发布。[二咖传媒案例](https://www.feishu.cn/customers/erkamedia)

## 五层待比较的实现

| 已确认的分类 | 建议纳入实测的实现及理由 | 决定采用或替换的证据 |
| --- | --- | --- |
| 资料原件、版本和发布 | 隔离候选用 PostgreSQL 记资料号、版本、来源、授权与发布状态，原件放受控持久盘。对照直接复用宿主文档库；现有存储不足时比较受控文件服务与 S3 兼容接口。 | 同名不同项目、按历史日期查当时有效版本、撤回再授予、旧引用重开、到期清理、衍生手册待复核。换引擎后仍可按原号查原件。实时排班、欠款、合同终局由相应系统按现时权限回答。 |
| 检索服务 | 原方案比较 RAGFlow 与 Docling＋pgvector＋明镜发布授权。本稿另提议在同题中试 WeKnora v0.9.0 标准 Compose，以独立 ParadeDB（PG 17、pg_search、pgvector）和 Redis 承载知识检索及入库。已有文档平台按用户身份搜索、纯关键词检索作为基线。三条路线分别跑，可复用相同输入和判卷，无需常驻三套引擎。 | 精确编号、口语改写、同名项目、时效冲突以及重开引用都要评。记录建库、改一份资料、撤回和故障恢复的实际步骤与工时。若无法在发模型和交付前按对象重新核权，则关闭该候选的受限路径。 |
| 文档与复杂版面 | 普通文档先试原生解析；复杂 PDF 同题试 MinerU、Docling；原生 XLSX 比较直接读取工作表和单元格（openpyxl）与引擎解析。对跨章节图文缺失可加试 Ontos-AI Knowhere。 | 表头跨页、金额单位换列、脚注例外、页码、单元格、幻灯片图注分别核验。保存从解析片段回到原件的定位。转成 Markdown 后仍须查得原位置。 |
| 音视频与图片 | 候选为 FFmpeg 提取片段与帧、faster-whisper 做带时段的转写，再关联原片和人工标注。与直接查已有字幕、审片记录的路径同题比较。 | 区分“口头说切镜”与“画面何时切镜”，核时间码、画面版本、可用片段边界及二次使用权。纯字幕不能证明画面时应明确缺证。 |
| 中文向量与回答 | 比较关键词、BGE-small-zh-v1.5 向量及两者混合；其余条件固定后再测重排的增益。生成经获准的明镜模型出口，Qwen3-8B 可作隔离候选。分别评价找资料、读对资料、用员工听得懂的话回答。 | 同批用户原话、同一权限和资料版本下，分开报告遗漏、挑错版本、答非所问、过度追问、编造及成本。模型端点及预算未确定时只报告检索结果。 |

产品资料用于核对能力和接入位置。WeKnora 的库级角色、解析后的文本偏移，都需在本项目验证其能否支撑对象授权和原件定位。固定发行版、镜像与模型摘要、许可、部署资源和数据出口应在实测清单逐项登记。[WeKnora 检索](https://github.com/Tencent/WeKnora/blob/v0.9.0/website-docs/03-features/05-retrieval-engines.md) · [解析接口](https://github.com/Tencent/WeKnora/blob/v0.9.0/website-docs/03-features/03-document-parsing.md) · [RAGFlow](https://github.com/infiniflow/ragflow/releases/tag/v1.0.0) · [Docling](https://github.com/docling-project/docling) · [MinerU 许可](https://github.com/opendatalab/MinerU/blob/mineru-4.2.3-released/LICENSE.md) · [Knowhere](https://github.com/Ontos-AI/knowhere) · [faster-whisper](https://github.com/SYSTRAN/faster-whisper) · [BGE](https://huggingface.co/BAAI/bge-small-zh-v1.5) · [Qwen](https://huggingface.co/Qwen/Qwen3-8B)

若资料主要留在已有办公平台，同时比较按用户身份回源。若核心困难集中在多个源的权限同步，补评 Onyx 并核对所需版本及同步延迟；若需求集中在 Markdown 创作，可评 Obsidian 作为编辑入口。按“草稿可写、批准后发布、客户资料可见范围、发布后能撤回”的完整流程验收。[飞书云文档](https://open.feishu.cn/document/server-docs/docs/docs-overview?lang=zh-CN) · [Onyx 权限说明](https://github.com/onyx-dot-app/documentation/blob/main/security/architecture/access_controls.mdx) · [Obsidian 协作权限](https://help.obsidian.md/Obsidian+Sync/Collaborate+on+a+shared+vault)

## 如何做决定

1. 用[员工原话样题与判卷方法](../requirements/knowledge-base-conversations.md)核对题目现实性。隔离样题均为合成示例；正式盲题由岗位人员以原话提出，保留口误、俗称、纠正和后续追问。确认资料时无需一次性交付完整资料库。
2. 同题固定身份、时间、附件、原件版本和可使用的模型。先跑现有办法和纯关键词，再跑候选，单变量比较解析、检索和回答。记录各题结果及人工操作用时。不得把不同硬件、不同模型或缺失样本产生的差异直接归因于引擎。
3. 权限泄漏、将撤回资料重新交给用户、把错金额或失效使用权答成可执行事实，逐例单列，未修复的路线不得用于相应正式范围。通过硬项的候选再按岗位任务完成率、维护工时、查询等待、每千页处理成本及每百问成本比较。并发、容量、采购金额按实际岗位负载与成本测算。
4. 将逐题结果、原始出处、失败复验、剩余限制、责任人与决定记录在本专题，供项目方选择采用、限范围采用或退回重选。运行中另测并发入库与撤回、索引重建、备份恢复和同一失败运行的追查。公司级验收还需真实接口和岗位签收。当前已交付的是分类、待评候选和公开校准题；技术采用决定、独立评审和知识库实测均待取得。
