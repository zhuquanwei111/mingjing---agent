# 明镜工程文档索引

**状态：目录治理草案。** 本页负责帮助维护者和 Codex 找到现行资料，不以目录是否存在替代正式评审或 Git 证据。实际工作分支、提交、PR 和 CI 状态应在使用时重新核对。本次整理不得自动恢复已暂停的业务开发。

## 从哪里开始

| 目的 | 当前权威入口 | 备注 |
| --- | --- | --- |
| 仓库状态与使用方法 | [根 README](../README.md) 与 [根 AGENTS](../AGENTS.md) | 开发前检查实际分支、工作区和相关 PR |
| 已合并 P2 的代码和行为 | [P2 操作说明](../core/README.md) 与 [旧版本说明](../core/VERSIONING.md) | 只代表对应代码版本，不等于新路线 B 已完成 |
| P1 验证与可复现环境 | [P1 说明](../p1-walking-skeleton/README.md)、[P1 历史报告](../p1-walking-skeleton/P1_REPORT.md) | 历史记录以原 SHA 和 CI 为准 |
| 通用 Codex 工程规范 | [通用规范包](../engineering-standard/README.md) | 含执行脚本、Skills、模板，不是明镜业务交付包 |
| 明镜如何采用工程规范 | [项目接入说明](engineering-standard.md)、[执行性审查](engineering-standard-execution.md) | 通用层与项目例外分开 |
| 开发与任务接续 | [开发流程](development.md)、[长任务计划](PLANS.md)、[设置及环境边界](configuration.md) | 任务具体状态以所属任务记录和实际 Git 状态核对 |
| 需求与验收 | [通用工程规范需求](requirements/engineering-standard.md)、[任务记录目录](tasks/) | 已有项目需求摘要不代替用户持有的完整需求原件 |
| 技术决定 | [ADR 目录](adr/) | 记录拟议、接受、替代与撤回，状态必须与当前事实一致 |

## 当前架构与历史的区别

- [v1 历史工程交付包](../mingjing-codex-engineering-v1/README.md) 仍暂存仓库根目录。这是**历史来源**，不应单凭其 `03_TECH_STACK.md` 或启动词确定新开发路线；其中仍被根 AGENTS 引用的安全/阶段约束必须在迁移前识别并保留。
- [v2 路线 B 开发包候选 PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6) 是**未合并的候选交付**，当前 main 不含该目录；不能用 PR 描述等同于独立架构评审完成。
- [整体架构评审与最短贯通草案 PR #7](https://github.com/zhuquanwei111/mingjing---agent/pull/7) 仍为单独的审查任务草案。最终评审结果和是否接受路线，须以有版本、问题处置与批准状态的正式记录为准。
- [独立 Reviewer 机制修改 PR #8](https://github.com/zhuquanwei111/mingjing---agent/pull/8) 不等同于路线 B 选型通过。
- [A/B 隔离实验 PR #5](https://github.com/zhuquanwei111/mingjing---agent/pull/5) 保存两路实际实验材料；它不是合并到 main 的产品实现。

**统一现行架构入口尚待独立评审结论同步。** 在此之前不擅自将某份旧报告或候选包提升为“唯一正式架构”，也不把本目录治理文档当作恢复开发的许可。

## 目录治理及资料规则

参见 [目录职责、迁移映射和验收](repository-layout.md)。目前优先完成入口梳理、引用清单及目录规范，**历史包搬迁与候选方案定版另作为后续受审迁移**，避免与进行中的 PR 冲突。未来的 `docs/architecture/` 与 `docs/designs/` 只在有真正经确认的内容时建立，不为排版创建空目录。正式工程记录留在 Git；Space 可用于讨论和链接，但不自动替代正式提交。