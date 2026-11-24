# 已审设计交接与 W0 复审回执

本页供开发者从 Git 核对三次设计交付的版本、用途和原件。真实宿主上 W0a、W0b 的 16 项实测仍待执行。

| 评审 | 对应交付及读法 |
| --- | --- |
| W0 宿主契约 | [设计](../designs/w0-host-design.md)及[逐场景验收](../designs/w0-host-acceptance.md)逐字节取自[受审提交](https://github.com/zhuquanwei111/mingjing---agent/commit/8095d6f79e2e4e42fbdef03c8fdbfdf6b4785b35)。文中“首期产品范围草案”描述的是当时的[单场复盘草案](https://github.com/zhuquanwei111/mingjing---agent/blob/8095d6f79e2e4e42fbdef03c8fdbfdf6b4785b35/docs/requirements/first-mvp-product-scope.md)，本仓库同一路径现在提供后续定稿。 |
| MVP-SCOPE-COMP-01 | [首期产品范围](../requirements/first-mvp-product-scope.md)、[组件选择](../designs/whole-product-component-selection.md)和[业务调用图](../designs/mvp-operation-call-graph.md)。三份 Markdown 均与独立复审回执记录的完整 SHA-256 相符。 |
| MJ-COMMON-BOUNDARY-02 R5 | [首期基座说明](../architecture/明镜完整产品公共架构与首期通用基座.html)、[架构图](../architecture/明镜公共架构.svg)、[可编辑源图](../architecture/明镜公共架构.drawio)及[组件运行与取证表](../architecture/明镜公共组件选型_首期运行与证据.csv)。使用说明与评审记录可在 HTML 中阅读，克隆后可本地打开。 |

两份选型材料按评审顺序阅读。MVP-SCOPE-COMP-01 给出业务范围和组件候选，R5 补充首个可运行版本、最迟可用时点、第一条真实链路和验收取证。受控知识库、撤回验证、失败追查和公共评测均已列入首个业务功能开发前的验收。

## 文件指纹

散列对应本次归档的原始文件。四份基座交付物来自同一份通过完整性校验的 ZIP，源包 SHA-256 为 `1cf2210f717d2deb3af007a0bac47ffab538c23e38c6f03a8e08b4d9a4807e71`。

| 文件 | SHA-256 |
| --- | --- |
| [first-mvp-product-scope.md](../requirements/first-mvp-product-scope.md) | `ed8ff831bd1ea7ecefe236ca52930183f3c5ad26a5526ef2500279a506dd03eb` |
| [whole-product-component-selection.md](../designs/whole-product-component-selection.md) | `d7cf1627004bc9aa61c0f585253f3f916aac63ed898771cea4cdbdda1151a229` |
| [mvp-operation-call-graph.md](../designs/mvp-operation-call-graph.md) | `06156861308a9ef72584393f52bdfb22281d1266e5f27bf3556da116d4669ccc` |
| [明镜完整产品公共架构与首期通用基座.html](../architecture/明镜完整产品公共架构与首期通用基座.html) | `fcb7364359520cb832dce8843f33a6403b3f6f69e7f7d99089a3b5a73fd7fb18` |
| [明镜公共架构.svg](../architecture/明镜公共架构.svg) | `5d0db2a3e1c98b4bf5a3359776b23c86e0d5cdbe631e6a75b0c286e4a1c4c18f` |
| [明镜公共架构.drawio](../architecture/明镜公共架构.drawio) | `d4f369d8b0b2cd70ab8746407e2570c086cdd7ac485e2a619b931adc38472949` |
| [明镜公共组件选型_首期运行与证据.csv](../architecture/明镜公共组件选型_首期运行与证据.csv) | `2cfbced9e8128c209c4717c5d2dee042475060da70e57225f12537a848023723` |
| [w0-host-design.md](../designs/w0-host-design.md) | `860ef3797c2e52e89c00018a3a63806e759f9c7ba4e26285b889686720a46029` |
| [w0-host-acceptance.md](../designs/w0-host-acceptance.md) | `46702a1267ecddd5a95246cc59b7f67b8029b0694e7d9693a955dabb6c041fa2` |

## W0 原始回执

摘自 [PR #18 的独立复审评论](https://github.com/zhuquanwei111/mingjing---agent/pull/18#issuecomment-7105222681)。以下保留原文与当时的业务范围。

### 正式 W0 独立方案复审通过

全新上下文的独立评审者对固定提交 [8095d6f7](https://github.com/zhuquanwei111/mingjing---agent/commit/8095d6f79e2e4e42fbdef03c8fdbfdf6b4785b35) 的四份文档执行复审，逐项核对 A1–A8、B1–B8 与 #14 的需求及阶段边界。首轮对 [63cdb2f](https://github.com/zhuquanwei111/mingjing---agent/commit/63cdb2f875d3ab337ece917244fdaa9960f9b8f2) 的结论为需要修改。原设计者已补齐并由同一评审者复核：原工具请求尚未落账和下一轮认领前后的中断、目录与模型实收的区别、同一异步能力三入口与拒绝负例、父取消传播与迟到结算、撤权前已交接与撤权后新增字节、欠参任务不得派发、干净环境失败非零复跑，以及业务退回须计返工。

**裁决仅通过 W0 的接入契约和验收设计。当前没有真实宿主，正式 W0 实测 0/16。** 未来真实应用入口与权限权威就绪并另获批准后方可实施 W0a，A 全通过才做 B，最终用同一候选复验。首期单场复盘为产品范围草案；真实业务选择及 MVP 实施方案留待 W0 实测与业务确认，再独立评审并决定开发。
