# 首期设计与 W0 历史原件归档

现行建设依据见[最终架构](../designs/current-architecture-baseline.md)和[阶段验收要求](../designs/architecture-final/gates-and-risks.md)。本页保存 2026 年 11 月 24 日归档的三份首期设计、四份公共基座图表和两份 W0 原件，以及当时的签收依据。

| 当时的交付 | 今天如何使用 |
| --- | --- |
| 首期业务范围、组件表、业务调用图 | 首期业务仍为跟播、复盘与次日妆造预约。约满时让运营选其他真实空档，可作为业务验收示例。旧稿指定的采集路径须在业务接入时核实；旧组件表和调用图用于追溯当时的决定。 |
| 公共基座说明、SVG 图、可编辑图、组件取证表 | 历史设计以 Python、Temporal、Pydantic AI 为主体。公共宿主建设按已合并的 #27 执行。 |
| W0 宿主设计、逐场景验收 | 保留当时的设计复审与 16 个场景。承建方、运行组件与开工条件按现行阶段要求执行；场景须在实际收端取证。 |

## 原件及校验

[下载九份原件](../archive/reviewed-deliverables-20261124.zip)。包内保留各文件在受审快照中的路径与字节。下表的在线阅读链接固定到归档提交，原文中的相对链接按当时的仓库结构打开。离线核对可解压逐件计算 SHA-256。

归档 ZIP 的 SHA-256 为 `8a57b9eb23bc7772a62d506975c38eabe92c309ad25688e981636e32f929d59b`。四份公共基座原件的上游 R5 交接包 SHA-256 为 `1cf2210f717d2deb3af007a0bac47ffab538c23e38c6f03a8e08b4d9a4807e71`。

| 固定原件 | SHA-256 |
| --- | --- |
| [first-mvp-product-scope.md](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/requirements/first-mvp-product-scope.md) | `ed8ff831bd1ea7ecefe236ca52930183f3c5ad26a5526ef2500279a506dd03eb` |
| [whole-product-component-selection.md](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/designs/whole-product-component-selection.md) | `d7cf1627004bc9aa61c0f585253f3f916aac63ed898771cea4cdbdda1151a229` |
| [mvp-operation-call-graph.md](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/designs/mvp-operation-call-graph.md) | `06156861308a9ef72584393f52bdfb22281d1266e5f27bf3556da116d4669ccc` |
| [明镜完整产品公共架构与首期通用基座.html](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/architecture/%E6%98%8E%E9%95%9C%E5%AE%8C%E6%95%B4%E4%BA%A7%E5%93%81%E5%85%AC%E5%85%B1%E6%9E%B6%E6%9E%84%E4%B8%8E%E9%A6%96%E6%9C%9F%E9%80%9A%E7%94%A8%E5%9F%BA%E5%BA%A7.html) | `fcb7364359520cb832dce8843f33a6403b3f6f69e7f7d99089a3b5a73fd7fb18` |
| [明镜公共架构.svg](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/architecture/%E6%98%8E%E9%95%9C%E5%85%AC%E5%85%B1%E6%9E%B6%E6%9E%84.svg) | `5d0db2a3e1c98b4bf5a3359776b23c86e0d5cdbe631e6a75b0c286e4a1c4c18f` |
| [明镜公共架构.drawio](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/architecture/%E6%98%8E%E9%95%9C%E5%85%AC%E5%85%B1%E6%9E%B6%E6%9E%84.drawio) | `d4f369d8b0b2cd70ab8746407e2570c086cdd7ac485e2a619b931adc38472949` |
| [明镜公共组件选型_首期运行与证据.csv](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/architecture/%E6%98%8E%E9%95%9C%E5%85%AC%E5%85%B1%E7%BB%84%E4%BB%B6%E9%80%89%E5%9E%8B_%E9%A6%96%E6%9C%9F%E8%BF%90%E8%A1%8C%E4%B8%8E%E8%AF%81%E6%8D%AE.csv) | `2cfbced9e8128c209c4717c5d2dee042475060da70e57225f12537a848023723` |
| [w0-host-design.md](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/designs/w0-host-design.md) | `860ef3797c2e52e89c00018a3a63806e759f9c7ba4e26285b889686720a46029` |
| [w0-host-acceptance.md](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/designs/w0-host-acceptance.md) | `46702a1267ecddd5a95246cc59b7f67b8029b0694e7d9693a955dabb6c041fa2` |

## 评审与证据边界

三份首期文件与 MVP-SCOPE-COMP-01 的原始指纹对应；四份公共基座文件来自 MJ-COMMON-BOUNDARY-02 R5；两份 W0 文件来自固定提交 `8095d6f7`。完整历史说明见[原归档回执](https://github.com/zhuquanwei111/mingjing---agent/blob/8bb23800205d9444d66ce686cb89801cffc0ef6a/docs/tasks/reviewed-deliverables.md)和[W0 独立设计复审](https://github.com/zhuquanwei111/mingjing---agent/pull/18#issuecomment-7105222681)。该次复审记录 W0 实测为 0/16。现行架构的后续专项试验、适用边界与待验事项见[基线施工记录](architecture-baseline-transition.md)。
