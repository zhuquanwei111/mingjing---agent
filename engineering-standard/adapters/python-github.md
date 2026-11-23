# Python、Make 与 GitHub Actions 适配

适用于已有 Python 代码、Make 本地入口和 GitHub PR 的项目。项目决定支持的 Python、操作系统、架构、依赖方式和正式验收作业。采用者记录实际最小版本并在干净环境验证。

| 用途 | 实现选项 | 采用项目需要填写的证据 |
| --- | --- | --- |
| 快速检查 | `make check` 调用现有格式、语法、类型、导入、文档检查中的适用项 | Python 版本和检查覆盖范围 |
| 聚焦测试 | 在锁定环境用 `python -m pytest` 运行相关用例，或沿用已有入口 | 正常、失败、兼容及关键回归；证实新增反例能失败 |
| 正式验收 | `make acceptance` 或已有命令启动真实依赖，结束后按任务 ID 清理 | 运行器 OS/架构、服务版本和清理结果 |
| 状态与接续 | `git status --short --branch`、`git rev-parse --show-toplevel HEAD`、项目只读入口 | 新上下文核对差异和下一步的输出 |

用项目已有依赖工具从可信来源生成锁。安装以实际用途和架构解析 lock；使用 pip 哈希锁的项目可按 `python -m pip install --require-hashes -r <lock>` 安装，并执行 `python -m pip check`。仅支持 wheel 时加 `--only-binary=:all:`。镜像按目标架构固定摘要或可核验的多架构索引。在新增平台检查对应 wheel、原生运行和依赖冲突；辅助平台结论保留在该平台范围内。

GitHub Actions 复用相同 Make 入口。PR 改动可快速收到检查结果，正式作业选声明的目标 runner。选用 GitHub 托管标准 runner 前核对仓库可见性、额度及费用。配置 `contents: read`，checkout 默认可显式设置 `persist-credentials: false`；第三方 Actions 固定经核验的提交。流水线记录 `uname -sm` 和 `git rev-parse HEAD` 或可核验的等价日志。将合成服务的启动和清理失败传播到作业状态，保留受控证据，不上传包含运行凭据的数据目录。必需检查要在对应 PR 情况都有明确结果，变更名称前核对当前生效规则及迁移影响。[GitHub runner 参考](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) · [Actions 费用](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

创建 Draft PR 后核对实际 base/head、受审差异、该 head 关联的完整 CI 及实际 checkout。核实服务器规则可用 `gh api repos/<owner>/<repo>/rules/branches/<branch>`；查看运行可用 `gh run view <run-id> --json headSha,event,jobs,conclusion,url`。PR 事件默认检出合并引用，证据应分别写明 PR head 和运行中被检出的提交。依赖另一未合并 PR 时，先确认用户知道交付顺序。其合并、改写或关闭后重查实际差异和测试，再按授权调整目标。由项目维护者验收与合并。[GitHub PR](https://docs.github.com/en/pull-requests/reference/pull-requests) · [规则集](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
