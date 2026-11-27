# 历史 Mastra 架构（PR #27/#28，2026-11-26）

此页保留固定历史导航，不是当前技术或施工指令。原文件以 Git 固定提交 `114af05ea6a24cde7f36d3e3dce7225234aa279a` 为准，不改历史原件；过去 H1/H2 的有限正反例不能当作新 DeerFlow 实际验收。现行入口：[当前架构](../../designs/current-architecture-baseline.md)，[现行需求修订](../../requirements/current-engineering-requirements.md)。

| 旧原件 | 固定位置 |
|---|---|
| 架构终裁 | [current-architecture-baseline.md](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/current-architecture-baseline.md) |
| 契约/图 | [contracts.md](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/contracts.md) · [SVG](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/architecture.svg) · [PNG](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/architecture.png) |
| 技术/复用/许可 | [technology.csv](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/technology.csv) · [reuse.csv](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/reuse.csv) · [licenses.csv](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/licenses.csv) |
| 原 76 映射与阶段 | [final-architecture-mapping.csv](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/requirements/final-architecture-mapping.csv) · [gates-and-risks.md](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/designs/architecture-final/gates-and-risks.md) |
| 旧 ADR / H1 H2 证据记录 | [ADR 0002](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/adr/0002-mastra-architecture-transition.md) · [历史施工记录](https://github.com/zhuquanwei111/mingjing---agent/blob/114af05ea6a24cde7f36d3e3dce7225234aa279a/docs/tasks/architecture-baseline-transition.md) |
| 合并 PR | [#27](https://github.com/zhuquanwei111/mingjing---agent/pull/27) · [#28](https://github.com/zhuquanwei111/mingjing---agent/pull/28) |

原工程规则与旧 P1/P2 实际回归保留在已有归档目录，根规则明确加载其有效部分；与已采纳 R3 冲突的机制判据由现行需求修订覆盖。旧知识/身份/阶段专项未合并候选的来源见现行任务记录；不默认合并或部署旧候选。
