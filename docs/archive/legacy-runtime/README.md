# 历史 P1/P2 运行与取证

明镜现行架构采用 Mastra OSS。此处保留早期 Temporal/LangGraph 隔离实现，用于复现已交付行为、故障和回归结果。正式公共宿主的职责与验收见[现行架构](../../designs/current-architecture-baseline.md)。

| 归档内容 | 复现入口 | 原始出处 |
| --- | --- | --- |
| P1 行为、撤权、预算、重放与重建 | [运行手册](p1-walking-skeleton/README.md)、[历史报告](p1-walking-skeleton/P1_REPORT.md) | [迁移前源码与证据](https://github.com/zhuquanwei111/mingjing---agent/tree/395a7edf891aee1244d762ea89bc6b45318ea88f/p1-walking-skeleton)，Git 树 `e9867de70565b57078bba26bfce0ef0644b0f61e` |
| P2 公共层接口、事务、授权与收据 | [操作说明](core/README.md)、[历史报告](core/P2_REPORT.md) | [迁移前源码与证据](https://github.com/zhuquanwei111/mingjing---agent/tree/395a7edf891aee1244d762ea89bc6b45318ea88f/core)，Git 树 `08a471558a452c260cc4d4bc91135f3094f255c0` |
| 旧实现专属工程检查 | [静态导入边界](scripts/check_architecture.py)、[检查用例](scripts/tests/) | 归档前位于根 `scripts/` |

从仓库根运行 `make check` 可同时检查归档与现行工程入口。准备好的 macOS 环境使用 `make smoke`。隔离 Linux 的 `make acceptance` 与 `make p2-acceptance` 分别运行 P1、P2。ARM64 必需作业仍执行两套回归。更新已有 checkout 时，先按相应运行手册核对旧运行目录、项目身份和卷。

## 证据校验

P1、P2 的 `evidence/` 共 98 个跟踪文件，与各自迁移前证据树逐文件对应。P1 在本节目录下的 `p1-walking-skeleton/` 内运行 `shasum -a 256 -c evidence/SHA256SUMS` 可核对 39 项，P2 在 `core/` 内用同一命令核对 4 项。P2 的 `evidence/source.sha256` 对应提交 `7d4df4f` 下的 `p2-core/`，其中 22 条应与该版本比较。

Instabox 原始清单共 52 条。迁移基线中 51 条匹配，README 自 #22 更新计划链接后已与采集时摘要不同。本次保留证据目录原字节；按原清单核验 README 请取[采集版本](https://github.com/zhuquanwei111/mingjing---agent/blob/40e02a86a3594af3edc3f77199973514c6cbd1c1/p1-walking-skeleton/evidence/instabox/README.md)。其“隔离计划”在当前树的[位置](../engineering-v1/P1_EXECUTION_PLAN.md)。镜像扫描发现、未放行项和原始失败记录同成功记录一并保留。
