# 中断实验运行记录

受审代码 `90946305a8f16c74e8603a8f2974831ec7590d1c`，判据先行提交 `f5b4df8f70e3033e52fc8a8906f8f13eeb29b2b1`。[云端 GitHub Actions](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45190768318) 启动了互相独立的产品 PostgreSQL 与观察 PostgreSQL、实际 Temporal Server、新旧 Worker 进程、HTTP 模型与业务收端。每个实收、查证、效果、逐次费用与交付可回查。假模型固定协议，只使用合成输入。

| 同一次 Worker 强杀时五个未完成的 Activity | 工具到达 | 效果 | 模拟收费 | 交付 | 模型请求 | 预留 / 实耗 |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 正常查回、v2 读旧格式 | 1 | 1 | 1 | 1 | 2 | 0 / 1 |
| 暂不可查 | 1 | 1 | 1 | 0 | 1 | 3 / 0 |
| 已取消、暂不可查 | 1 | 1 | 1 | 0 | 1 | 3 / 0 |
| 同一取消任务收到两次可信迟到通知后 | 1 | 1 | 1 | 0 | 1 | 0 / 1 |
| 已知、旧格式不兼容 | 1 | 1 | 1 | 0 | 1 | 0 / 1 |
| 已知、故意传错调用 ID | 1 | 1 | 1 | 0 | 1 | 0 / 1 |

已运行的五个用例属于一次故障注入。接受时实际业务效果与费用均为零。由后台独立提交效果后，旧 Worker 尚未记录回执，控制器发 SIGKILL。Temporal 在同 Workflow ID、Run ID、Activity ID 下进行第二次尝试。新进程使用真实不同的宿主检查点读取模块。已知有权样本用原 tool_call_id 和原收据进入第二次模型请求；SDK run_id 更新，conversation_id 延续。错误配对被固定 SDK 拒绝。产品共享模型请求槽与实际模型请求数对应。Token、实际供方费用以及依赖库跨版本升级未测。原生 TemporalDurability 未测。

代码承担的公共修改有外部异步能力适配、持久化操作与回合检查点、模型请求限额、可信查单、版本兼容和待核状态。按本提交物理行计，worker.py 189、adapters.py 23、两个 release 文件合计 31、flow.py 23；这些包含实验代码，不作开发工时或长期维护费用估计。未更改 #5 的运行核心或上游，因为这是另一种宿主实现；不能把 0 处上游修改解释为无需自研。实验仅通过 Agent 入口验证此异步类型。暂不可查的活跃任务已保留预算和查询资料；其后来变为可查时重新唤醒、跨版本库升级、真实宿主权限和共享账的完整恢复仍须验证。新版本若任意旧载荷均无法解析，须保留可用的旧 Worker 或封存待核，不得重新派发。

在固定测试提交的仓库根目录用隔离 Linux AMD64、Docker Compose 和可拉取的固定镜像启动，命令为 `LAB_OUT=/tmp/mj-product-run TEST_HEAD=$(git rev-parse HEAD) CI_RUN=local bash lab/product-review/run.sh`。核对归档时在本目录执行 `sha256sum -c SHA256SUMS`（macOS 可用 `shasum -a 256 -c SHA256SUMS`）。9 个原始成员含 25 条观测、7 份原始工作流历史和 1 份版本记录。最初的 CI [45190367120](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45190367120) 因文件末尾空行在 make check 阶段退出，未执行实验。后续复审使模拟计费逐次对应物理到达、校验真实模型线缆参数、独立对齐产品/收端/引擎三方标识和已知正例。
