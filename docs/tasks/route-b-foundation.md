# 路线 B 开发切换与首项交付

## 范围和基线

用户采纳路线 B，并要求依既有规范治理旧包和已有开发，再交付新包、开始新开发。[冻结需求](../requirements/route-b-foundation.md)、[架构决定](../adr/0002-route-b-foundation.md)、[开发包](../../mingjing-codex-engineering-v2/README.md)共同说明本任务。新分支 `codex/route-b-foundation` 从已合并 PR #4 的 `3b5b9d2c285de011c523174d794792eb7cafbd97` 创建。旧选型对照是 fdf0424。实验 PR #5 继续保留独立证据。与用户并行的原工作区及数据不属于本任务。

先提交版本化开发包、ADR 和指向新旧入口的标记并交付，再按工程规范启动首项实现。后续任务沿根规则进入，不从旧包启动词重新开始。拟将新增代码放在 `app/src/mingjing_agent/`，回归在 `app/tests/`。

## 首项实施候选

选择 FR-24/36 和 AC-15 的应用库部分。使用 Python 标准库、不接服务，库的可信调用者传入契约和已核实的证据快照，下一批把它接入真实授权和提交方。现有 P2 的 schema 校验不能表达跨项业务完成，实验的两个固定项不具有通用性。复用它们的失败场景，保持旧接口、合同、队列、数据及旧测试兼容。此次不做推理、公开网络入口、可信凭据签发、生产存储迁移或实际交付。

1. 方案关卡在干净任务分支运行。独立 reviewer 读取本任务、冻结需求、v2 的完整方案和仓库规则，首个实际动作是创建 `app/src/mingjing_agent`、`app/tests` 目录。命令如下。方案改变按现行规则回审。
2. 实现一个可由宿主、Worker 直接导入的纯 Python API。契约固定非空 task_id、规则版本和有序且不重复的必需项，证据绑定同一任务、规则、项和引用。输入由可信适配器提供；库不解析用户自报权限。逐项肯定、否定/缺项、待核；任一证据冲突、未知结论、版本/任务错配、验证不可用、无效证据引用不能使任务就绪。对错配采取整批待核，未声明的项也不能提升就绪。完全重复记录等价。就绪只表示当前完成条件成立。无效契约或无效类型在库边界显式报错。返回稳定原因与按契约顺序的逐项结果，仅含受控引用。库没有模型、网络、I/O 或旧运行时导入。
3. 补聚焦的 unittest。至少验证两项正控、工具返回但缺项、否定和待核、验证不可用、错绑任务/规则、冲突、重复确认、同一证据重放、坏契约、增加未知要求项；检验无业务写入路径及可解释结果。新增 `make agent-test`，由已有正式 ARM64 作业和一项 amd64 辅助作业运行，原 P1/P2 步骤和检查名继续使用。同步各入口的检查范围。
4. 运行 `make check`、新目标、适用的仓库烟测和 CI；发起独立代码审查，核实与修复问题，向同一草稿 PR 回写各次提交与 CI/完整日志。用户人工决定合并。回退只撤销本任务的新增代码、测试与入口，历史状态无迁移。

```sh
python3 engineering-standard/adapters/codex-cli/start_implementation.py docs/requirements/route-b-foundation.md docs/tasks/route-b-foundation.md -- mkdir -p app/src/mingjing_agent app/tests
```

## 进展与接续

1. 已交付 [v2.0 冻结开发包](https://github.com/zhuquanwei111/mingjing---agent/tree/501de2e63834f2d8dcbece246bb34c85ad292193/mingjing-codex-engineering-v2)，提交 `501de2e63834f2d8dcbece246bb34c85ad292193`。新开发入口与旧资产处置已列入[同一草稿 PR #6](https://github.com/zhuquanwei111/mingjing---agent/pull/6)。旧包、原执行代码、迁移与测试均可回查。单独提供给用户的 ZIP 经解压字节比对，SHA-256 为 `156950f6b6b668b704ff7f588efdc569c94b080aa3a9e6875a20c7bb101b4fef`。
2. 本地包内 4 份文档、仓库文档链接与差异检查通过。Mac 受管沙盒拒绝既有测试使用 `ps`，本地整套 `make check` 有 4 个子用例报错。[开发包提交的 GitHub 运行](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45135933312)的三个作业均通过。原生 [ARM64 完整日志](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45135933312/job/137562077265)检出合并测试提交 `c5b0845b8f0e03f04aaf4e7a27db8765be8faafc`，工程检查 41 项、P1 两批 16 和 2 项、P2 32 项均通过。两个 amd64 作业为辅助回归。结果覆盖旧资产与开发入口。
3. 已从干净隔离副本调用上文的正式方案评审入口。该次本地提交为 `35f1397750ce85c543d1fef93e0f4eff04eb2da7`，与公开开发包提交使用同一父提交和 Git tree `654679dbd0494e739db813004f600bde2d1abe2d`。当时冻结需求摘要为 `cc57f61163a10073348862e2f86012ea26ba1bdc904be191a2d287ddc061b73b`，方案为 `2378463dbcb8dce26cb21ce3958747d145f8a18f352750452d806b77c7ca91bd`，首个命令为 `b61fa5d9a49a674746326a28eb782924d58d8d3c41c4d476d3797d25fb2dd123`。Codex CLI 0.167.0 检出已有 ChatGPT 登录。评审进程退出 1，入口退出 2；同一只读启动方式实查返回 `failed to initialize in-process app-server client: Operation not permitted (os error 1)`。首次实现命令没有执行，未创建 `app/`。对开发包提交另行发起的原生独立审查也在同一初始化阶段失败，尚无独立审查结论。
4. 现有 Daytona 的实例列表在当前会话因域名解析失败而无法读取，Instabox 客户端在会话内无法设置其本机配置目录权限。未创建新实例。当前缺少可运行的独立只读评审会话，首批实现不依赖云沙盒、数据库或工作流服务。项目曾在已登录的 Mac Codex CLI 上[验证只读评审路径](../engineering-standard-execution.md)。恢复时在隔离 checkout 核对 PR 最新 head、工作区和本任务账，再执行上文原命令。评审会按当时实际候选重新生成摘要。原实施者接收意见、处理修订或在通过后开始实现，并在同一 PR 跟进测试和独立代码审查。无需重新决定选型、迁移旧项目或开通云服务。
