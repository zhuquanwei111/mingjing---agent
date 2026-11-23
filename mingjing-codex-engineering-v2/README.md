# 明镜智能体开发包 v2.0

**适用对象**　明镜 App 后端开发、能力开发和验收人员。本包按通用工程需求 v0.4.1 开展正式开发。采用 Python、PostgreSQL、Temporal 和 Pydantic AI。版本 v2.0 标识这份开发包；App API、数据库和能力有各自的版本。

明镜面向组织内获授权的多用户。约 300 人是首期用户规模。实时请求、后台任务、模型调用和外部资源的并发各自测量。保持一个宿主应用、按需分开的 API 与 Worker；新增能力可以是普通程序、确定性工作流、Agent Loop 或受控外部服务。

| 开发时需要作的判断 | 阅读位置 |
| --- | --- |
| 代码写在哪一层，哪些动作需要实时核权，谁有权判定完成 | [架构与契约](architecture.md) |
| 从哪一项开工，怎样验收，如何逐步走到完整产品 | [开发顺序与验收](delivery.md) |
| 哪些旧资产继续使用，已有调用方和在途任务怎样保护 | [旧包与旧代码处置](legacy.md) |

从完整仓库根目录进入。先读根 `AGENTS.md` 和 `docs/engineering-standard.md`，再读 `docs/requirements/route-b-foundation.md` 与当次任务账 `docs/tasks/route-b-foundation.md`。独立方案评审、独立代码审查、ARM64 合并门禁和用户人工合并按项目原流程执行。下一项任务从该任务账和实际 Git 状态接续。本包提供开发目标与边界，实际完成情况以对应提交的代码、测试和 CI 为准。

**基线。** 需求原件《明镜智能体应用——通用工程架构需求说明书》v0.4.1，2026-11-21，SHA-256 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`。旧 P2 对照为 `fdf04240eba747a9a681a1dad627da22d4b89cdd`。正式工作从已合并项目工程规范的 `3b5b9d2c285de011c523174d794792eb7cafbd97` 起步。

[适用的工程规范](https://github.com/zhuquanwei111/mingjing---agent/blob/3b5b9d2c285de011c523174d794792eb7cafbd97/docs/engineering-standard.md) · [技术决策与失败记录](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md) · [同场运行](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45131052175)
