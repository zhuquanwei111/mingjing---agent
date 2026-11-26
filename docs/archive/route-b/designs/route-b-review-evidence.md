# 架构复审证据与同门槛比较

## RB34 Lab

[PR #10](https://github.com/zhuquanwei111/mingjing---agent/pull/10) 从 #5 实验分支的 `bb55c843b8dd2e9ad646e982a38cda350b3df952` 分出，按预先冻结的[八例协议](https://github.com/zhuquanwei111/mingjing---agent/blob/e263e9403097fbee12d2d12da82efd2ea66cd941/lab/rb34/PLAN.md)检验[上轮独立复审的两项必要修改](https://github.com/zhuquanwei111/mingjing---agent/pull/7#issuecomment-7100697588)。本次引用的[测试提交](https://github.com/zhuquanwei111/mingjing---agent/commit/51c47060826cc3cae0347a4f22d22c29f9288a3f)为 `51c47060826cc3cae0347a4f22d22c29f9288a3f`，[目标 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45175497629)成功。版本与完整历史、原始收端和产品记录在[永久归档](https://github.com/zhuquanwei111/mingjing---agent/tree/9c39c0f624e0736985491c1aaa49fb471df27ca9/lab/rb34/evidence/45175497629)；[Actions 原始制品](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45175497629/artifacts/14817864455)另含服务日志。

| 场景（撤权、取消各有独立样本） | 供方收到 POST 次数 | 业务效果次数 | 模拟计费笔数 | 下游收到交付次数 | 产品预算（预留 / 已核销） |
| --- | ---: | ---: | ---: | ---: | --- |
| 正常确认，重复对账 | 1 | 1 | 1 | 1 | 0 / 1 |
| 默认 SDK，首次回执丢失后撤权或取消 | 2 | 1 | 2 | 0 | 0 / 2 |
| 关闭 SDK 重试，同样故障且查询未知 | 1 | 1 | 1 | 0 | Activity 第 2 次进入后仍为 3 / 0 |
| 关闭重试，随后查得可信迟到终局 | 1 | 1 | 1 | 0 | 两例均先为 3 / 0，随后为 0 / 1；重复通知新增费用为 0 |
| 只有幂等键、任务仍有效，无查单能力 | 1 | 1 | 1 | 0 | Activity 第 2 次进入后为 3 / 0，无查单、无重提 |

数据来自 [111 条逐笔记录](https://github.com/zhuquanwei111/mingjing---agent/blob/9c39c0f624e0736985491c1aaa49fb471df27ca9/lab/rb34/evidence/45175497629/raw.jsonl) 及 14 份 Temporal 历史。四项计数分别来自 HTTP 供方的到达、按操作号与输入指纹去重的效果、按到达记录形成的费用，以及另一个 HTTP 交付进程的收据。八个样本首个请求的正文摘要相同。供方先提交效果与费用，再断开套接字。各故障样本在控制前均见 1/1/1/0、未公开终局、产品预留 3。控制器等客户端记录真实断连后，单独提交撤权或取消事务，再释放传输异常；默认重试样本的第二次到达带 SDK 重试号 1。真实 Temporal Activity 重入是同一轮操作的第二次尝试。此处取消指产品取消并通知仍在对账的 Workflow；实验没有调用引擎强制终止。

独立代码审查在[首轮 CI](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45175256225)成功后发现供方收据的可见性取决于 SDK 组别，且只核对组内输入摘要。已在测试提交统一成同一供方规则，并断言八组收端首发摘要完全一致。代码复审确认两项均修复，表中只采用修订后的 CI。实验台将短授权事务与外部响应分离，未复现 #5 原持锁实现。触发后查单验证的是隔离供方的终局记录；对真实账单、外部回调认证、首次交接竞态、父预算并发、断电或备份恢复与生产权限系统仍应分别验证。

复核时在归档目录运行 `sha256sum -c SHA256SUMS`，原始 JSONL 的 SHA-256 为 `f125ac056e380797e358b921b78af9c00cf898b9a1d73b31cad527455a7d7984`。核对 `before_control`、`after_recovery`、`final` 与逐条 `product_event`，再对照同一 Workflow ID 的完整历史。重跑时检出上述测试提交，从仓库根目录在 Linux AMD64、可运行 Docker Compose 的一次性目录执行 `TEST_HEAD=$(git rev-parse HEAD) CI_RUN=local RB34_OUT=$(mktemp -d) bash lab/rb34/run.sh`。构建沿用 #5 的锁文件，产品库、供方账本、Temporal namespace、容器和卷按实验单独创建。[运行入口](https://github.com/zhuquanwei111/mingjing---agent/blob/51c47060826cc3cae0347a4f22d22c29f9288a3f/lab/rb34/run.sh) · [固定版本](https://github.com/zhuquanwei111/mingjing---agent/blob/9c39c0f624e0736985491c1aaa49fb471df27ca9/lab/rb34/evidence/45175497629/versions.txt)


**证据日期为 2026-11-23。** 本轮新增原件指纹核对、归档原始日志复算、PR #6 质量库重跑、固定发行源码与许可检查。没有启动新的产品服务，没有 Dify/Windmill 或新路线端到端结果。逐项回复和关闭要求见[修订稿](route-b-architecture-revisions.md)。

## 1．版本、来源与证据强度

| 证据 | 本轮核对及可复查位置 |
| --- | --- |
| 原件与架构初审 | 私有原件 v0.4.1 的 SHA-256 为 `75ac634a98393b5f99fb28901a6a91bc7431290143b6458bbf1f9a2af5f23062`。复核正文含 76 个不同 FR/NFR/TS/AC 编号，文档含七个图像文件。公开库只放指纹。三份 PR #7 文件按字节重算，全部匹配[云端回执](https://github.com/zhuquanwei111/mingjing---agent/pull/7#issuecomment-7099239826)。分项评审范围与等级见[终审原文](https://github.com/zhuquanwei111/mingjing---agent/pull/7#issuecomment-7099754918)。 |
| 三份研究 | 两份可定位的 B0 内容摘要分别为 `18a466e3640159f6cdf31c7bb89d6e66cf8765b08723cdb701b3441cfb4983a9`（Temporal、LangGraph、LiteLLM 与治理网关）及 `3f87f1541e1d0f181c177722a5665eb314c4b0e1386220f68e8c079ed68046a8`（Temporal 与 Pydantic AI，Windmill 为应用备选）。第三份综合报告主张择留 P2，引用的独立 B0-FREEZE.md 未取得，冻结顺序及筛选过程未证实。输出类型检查、租户预算与合成查单均不足以证明 P2 已满足 V05、父子共享预算或取消迟到场景。 [三份报告的指纹](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/evidence/inputs.json) |
| 实验代码、执行与归档 | P2 基线 `fdf04240eba747a9a681a1dad627da22d4b89cdd`。A/B 分支 `bb55c843b8dd2e9ad646e982a38cda350b3df952`，最终 Actions 的测试检出 `7d618721f3e9f7a7a54dd09bc6f13035289401c2`；原始日志和决定归档在 `553114d2114cc77081c415ad1697e74be282c9a8`。三者分开引用。[A 作业](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45131052175/job/137546379626) · [B 作业](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45131052175/job/137547609477) · [归档目录](https://github.com/zhuquanwei111/mingjing---agent/tree/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/evidence) |
| 已有质量库 | PR #6 的 `c22aff11d48bd6bc0accf245e799e889e7c8f4a1` 处于 Open、非 Draft、未合并（本次读取时）。此前 ARM64 CI 的实际测试合并提交是 `287023acb8d3a430ae240be2025c8752c8de061b`，日志为 15 项 OK。本轮用 `git archive` 仅从 #6 精确提交导出 app 和 Makefile，在干净目录用 macOS ARM64、CPython 3.12.16 执行 `make agent-test`，15 项 OK、退出 0。该命令只执行判定库。 [测试源码](https://github.com/zhuquanwei111/mingjing---agent/blob/c22aff11d48bd6bc0accf245e799e889e7c8f4a1/app/tests/test_quality.py) · [原始 CI 作业](https://github.com/zhuquanwei111/mingjing---agent/actions/runs/45158240092/job/137636604676) |

## 2．从独立接收端复算

从固定树读取 run-logs.zip，ZIP 的 SHA-256 为 `ae90549c4ec4595a017c707e554edb479eada87bcf50afd9265144381dc45498`。逐一检查 16 个成员的字节数与 SHA-256，全部匹配清单。重新解析两个最终日志中的 RAW、HISTORY、REAL_MODEL 与 BUDGET_TRANSITIONS；同名 quality 场景保留四条独立样本，不能只读汇总表里最后一条。以下是原始运行的离线复算。 [ZIP](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/evidence/run-logs.zip) · [成员清单](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/evidence/log-manifest.json) · [测试断言](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/suite.py) · [接收器](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/witness.py)

| 问题 | A 与 B 各自的运行事实 | 能说明的边界 |
| --- | --- | --- |
| V01/V02 | 每路 30 个 RAW 场景、42 段顶层历史，V01–V06 六组记录均为 pass。真实模型各 2 次请求、1 次工具、0 项任务条件确认，仍缺 2 项。冻结后扩展在两路分别产生 3 次接收调用，安装前后运行核心文件指纹相同。 | 说明原生循环/动态接入能工作。模型终止仍可业务失败。契约外的新执行类型仍要评估。 |
| RB-03 | 每路持续与暂停恢复各 5 个撤权点，指定接收点及其后续接收数为 0。交付前撤权时，先前的正式提交依然可见。 | 未测开放式时序竞态、真实身份源、远端撤销或延迟分位。 |
| RB-02/04 | 每路丢回执但可查时供方效果 1、下游 1；不可查时效果 1、下游 0、预留 3；取消且迟到时效果 1、查单 2、下游 0、结算 2。 | 独立业务库与接收库证明指定故障点；缺产品受理至引擎启动间的端到端证据。 |
| RB-04 | 父额度 5，竞争轨迹末四个（实耗，预留）均为 (0,3)、(2,0)、(2,3)、(4,0)。A 比 B 多一笔初始 (0,0) 观测。两边取消时尚在途的额度有记录。 | 采样条数不同；同一约束是已结算加预留不超 5。供方超额、无法查单和真实定价策略待测。 |
| RB-05 | 每路三个负例的（正式提交，交付）都是 (0,0)，完整正例为 (1,1)。#6 的单库测试另外覆盖错误任务/版本、重复引用、冲突和验证者不可用。 | 夹具收端与 #6 单库分属不同代码。尚无新宿主串起两者的证据。 |
| RB-07 | B 的 Agent 在一个 `b_execute` Activity 中执行；P1 的匹配版本回放成功，旧/新双向交叉回放及改名有预期的非确定性失败。 | P1 的成功及失败均不能外推到 B 的逐轮恢复、脱敏历史或灾备。 [B 工作流](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/b/flow.py) · [P1 版本记录](https://github.com/zhuquanwei111/mingjing---agent/blob/fdf04240eba747a9a681a1dad627da22d4b89cdd/p1-walking-skeleton/evidence/lima/AT10.json) |

**独立复算方法**：在上表所列归档树的 `lab/architecture/evidence/` 目录运行以下 Python 3 代码，仅读取 ZIP 和清单，断言失败即非零退出。对质量库，在 #6 精确提交的独立检出执行 `make agent-test PYTHON=python3.12`。

```python
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

manifest = json.loads(Path("log-manifest.json").read_text())


def records(lines, label):
    result = []
    for line in lines:
        fields = line.split(" ", 2)
        if len(fields) == 3 and fields[1] == label:
            result.append(json.loads(fields[2]))
    return result


def events(row):
    return [name for name, payload in row["events"]]


def cases(rows, name):
    return [row for row in rows if row["case"].rsplit("-", 1)[0] == name]


def verify_route(lines):
    rows = records(lines, "RAW")
    histories = records(lines, "HISTORY")
    assert len(rows) == len({row["case"] for row in rows}) == 30
    assert len(histories) == 42
    groups = records(lines, "RESULT")[0]["groups"]
    assert groups == {f"V{i:02}": "pass" for i in range(1, 7)}

    stages = ["read", "model", "tool_out", "commit", "deliver"]
    receivers = ["read", "model", "tool", "commit", "deliver"]
    for mode in ["staged", "continuous"]:
        for index, stage in enumerate(stages):
            row, = cases(rows, f"revoke-{mode}-{stage}")
            assert row["account"]["product"] == "denied"
            assert set(events(row)).isdisjoint(receivers[index:])

    counts = Counter(
        (row["account"]["product"], events(row).count("commit"), events(row).count("deliver"))
        for row in cases(rows, "quality")
    )
    assert counts == {("review", 0, 0): 3, ("succeeded", 1, 1): 1}
    for name, held, spent, downstream in [("unknown", 3, 0, 0), ("confirm", 0, 2, 1), ("cancel", 0, 2, 0)]:
        row, = cases(rows, name)
        assert len(row["effects"]) == 1 and row["effects"][0][1] == "supplier_send"
        assert (row["account"]["held"], row["account"]["spent"]) == (held, spent)
        assert events(row).count("downstream") == downstream
    assert events(cases(rows, "cancel")[0]).count("lookup") == 2
    transitions = records(lines, "BUDGET_TRANSITIONS")[0]
    assert transitions[-4:] == [[0, 3], [2, 0], [2, 3], [4, 0]]
    assert all(spent >= 0 and held >= 0 and spent + held <= 5 for spent, held in transitions)
    model, = records(lines, "REAL_MODEL")
    assert model["turns"] == 2 and len(model["tools"]) == 1
    assert len(model["result"]["missing"]) == 2 and not model["result"]["completed"]
    extension, = records(lines, "EXTENSION")
    frozen, = records(lines, "FROZEN_CORE")
    assert extension["receiver_calls"] == 3 and frozen["before"] == frozen["after"]
    print(len(rows), "receiver cases,", len(histories), "histories,", groups)


with zipfile.ZipFile("run-logs.zip") as logs:
    assert set(logs.namelist()) == set(manifest)
    for name, spec in manifest.items():
        data = logs.read(name)
        assert len(data) == spec["bytes"] and hashlib.sha256(data).hexdigest() == spec["sha256"]
    print("verified", len(manifest), "log files")
    for route in ("a", "b"):
        verify_route(logs.read(f"06-final-{route}.log").decode().splitlines())
```

## 3．同一硬门槛与资源比较

对每个候选采用同一 V01–V06 契约。同一测试模型和定向改变输入的真实模型探针、独立接收端、合成租户、额度、故障位置和成功判据。先判定五个授权出口、未知副作用及业务交付是否安全；仅对通过者比较复用和长期负担。待测项不记零分，也不记通过。

| 候选与证据 | 可直接复用 | 自研、迁移和运行责任 | 目前判断 |
| --- | --- | --- | --- |
| P2 择留 / A（固定 P2、LangGraph 1.2.22、Temporal SDK 1.36.1） | Catalog、发布和资源授权、回执、迁移与负例。同一标准下新增兼容能力无需改运行核心。 | A 实际另写动态图、模型/工具分发和配对，另建供应商及父预算/质量机制。需要 API、Worker、PG、Temporal、模型端；有旧依赖与迁移维护。在途留给原 Worker，先冻结旧受理，新任务走新版本，契约和回归逐项转移。 | A 的两份路线文件合计 341 新增行；P2 core 修改 0，关键旧 Agent 路径已被替换。原始 P2 的 32 项回归仅证明旧断言。 [差异](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/evidence/changes.txt) |
| B（Python 3.12.16、PG 17.12、Temporal Server 1.32.2、SDK 1.36.1、Pydantic AI Slim 2.71.0） | 原生 Agent、Tool、模型适配与请求限制；Temporal 管调度；兼容时复用 #6 判定库。 | 自建任务账本、出口授权、幂等对账、验证者、父预算。服务类别和 A 相同；不迁入旧任务或凭据。版本化契约允许替换 Agent，离开 Temporal 仍需处理历史、在途 Worker 和运行映射。 | 同范围两份路线文件 295 新增行，上游框架源码修改 0。A/B 的 AMD64 Python 锁分别为 52/32 项。首试理由是原生循环和扩展位置；尚无维护人天、成本或容量结论。 [B 实现](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/b/runtime.py) |
| Windmill v1.882.0 | 脚本、OpenFlow、Job 管理、Worker 和运维界面。可从受限脚本/流程开始接入明镜 API。 | PG、Server、Worker；部署还可含原生 Worker 和代理。要限制全部实际执行组及网络出口，将 Job ID 映射到业务操作、质量和预算。脚本与流定义需维护、迁移。固定版 Python 沙盒模板的联网隔离由部署配置决定。 | 完整应用首个对照。若受控模式需禁掉实际使用的核心能力、无法封住一条出口，或使用方式受发行条款限制，记录残余复用和替换代价。 [Compose](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/docker-compose.yml) · [网络隔离配置](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/backend/windmill-worker/nsjail/run.python3.config.proto) |
| Dify 1.20.0 | 已有 UI、知识、Agent、工作流和插件调用。App 只嵌后端时可复用的 UI 收益需单独计算。 | 固定 Compose 含 API、Worker、Web、DB、Redis、插件守护进程、沙盒和代理等，按选定配置测实际开启项。模型和工具各有插件调度路径，可信租户绑定、实际出口、业务回执和父预算仍需接入。存量数据与知识需验证导出、撤权和迁移。 | 可作完整应用对照。官方代码传递 tenant ID 证明调用接口存在，不能证明权限新鲜或所有路径受控。多组织对应多少 workspace 是许可和隔离前置事实。 [Compose](https://github.com/langgenius/dify/blob/7bef4e1b2dc21b2c694d3243425dd3fa6288f916/docker/docker-compose.yaml) · [模型](https://github.com/langgenius/dify/blob/7bef4e1b2dc21b2c694d3243425dd3fa6288f916/api/core/plugin/impl/model.py) · [工具](https://github.com/langgenius/dify/blob/7bef4e1b2dc21b2c694d3243425dd3fa6288f916/api/core/plugin/impl/tool.py) |
| Dapr Agents v1.1.1 | DurableAgent、工作流内触发 Agent，可复用多语言 sidecar 和状态组件。 | 运行时、sidecar、支持工作流的状态存储及 Worker 运维；需要重做与产品库的权威边界、V03/V04/V06。旧 Temporal 历史不能直接迁入。 | 替代调度器备选；多语言/既有 Dapr 运维能带来实际收益时，同样重跑故障矩阵。 [固定样例](https://github.com/dapr/dapr-agents/blob/8763fbb5756eb56e9989dda062f047ffae5fcc04/quickstarts/02_durable_agent_trigger_within_workflow.py) · [许可](https://github.com/dapr/dapr-agents/blob/8763fbb5756eb56e9989dda062f047ffae5fcc04/LICENSE) |
| DBOS Python 3.6.0 | PostgreSQL 上的持久执行和恢复代码，可能省去独立 Temporal Server。 | 仍需宿主/执行进程、PG 容量、Agent 与上述治理。需转换工作流状态和旧运行策略，比较 PG 故障对账本及调度的共同影响。 | 保留为运行服务数量或恢复粒度成为决定因素时的竞争者；未参加同场试验。 [恢复源码](https://github.com/dbos-inc/dbos-transact-py/blob/2cf279cf380152b426ecd451d573ccc41f5715a6/dbos/_recovery.py) · [MIT 许可](https://github.com/dbos-inc/dbos-transact-py/blob/2cf279cf380152b426ecd451d573ccc41f5715a6/LICENSE) |

### 完整应用的可重复试验任务（待执行）

从上表的 Windmill 源码版和 Dify 发行版固定提交各建一套独立 Linux 环境，登记最终镜像 digest、构建选项和实际启用服务。先用同一无副作用清单任务，将候选真实触发/运行入口映射到冻结协议；保留自己的执行器，禁止为满足断言而把真实业务全部转交 B。Windmill 走 Job API、脚本、流程和实际启用的 Worker 组；Dify 走应用调用、模型插件、工具插件及所启用的 HTTP/代码节点。先跑正例证明各路径真的可达，再在出口受控条件下复跑相同负例。未经许可的工作区形态只登记限制，不以同一 workspace 内的两个合成身份冒充已验证的独立 Dify workspace 隔离。

1. 对照[已冻结标准](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/DECISION.md)与[黑盒测试](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/suite.py)。分别注入工具顺序变化、事后新增能力、撤权五点、丢回执和 Worker 被杀、缺项交付、三子任务争同一预算；独立模型、工具、写入和交付接收端逐笔核对。
2. 每路额外执行并发撤权、同键异参、取消时正在发送、无查单和跨版本回放。所有候选使用同样输入与上限；与历史 A/B 比较新增用例前，A/B 也必须按新增标准运行，旧成绩不补记。
3. 归档启动命令、脚本/流程或 DSL 导出、正常/禁止路径、各收端记录、作业/业务键映射、锁等待、CPU/内存/磁盘/启动耗时、故障后需人工的步骤，以及实际修改框架/业务文件清单。不同硬件或不同流量分别列示。商业扩展、禁用功能与维护分叉按实际使用记录。
4. 任一例出现失权后出站、同操作多次生效、未知时盲目再发、质量缺项仍交付或跨父额度，先停止该候选的扩大测试，保留失败。缺容器服务、合适发行权或无法构造外部见证，报告未测。当前会话未发现可调用的 Docker、Podman、PG 或 Temporal 服务命令；本轮做了源码抽证与离线复算，未把它们记作完整应用实测。

## 4．依赖、发行与许可台账

**用途假设**为明镜 App 接入组织用户、内部服务处理任务。将组件界面直接开放给客户、按组织提供工作区、把镜像随产品分发或对外运营，分别核定。P2 基线递归 Git 树中未见 LICENSE/COPYING 文件；复制或对外分发前请权利人确认。私有需求原件、调研原件及图片仅留指纹。

- **Windmill**：固定版根许可将非 enterprise 源码构建、官方 CE 发行和企业代码分别规定。源码构建遵守 AGPLv3，客户端/OpenAPI 等按指定路径为 Apache-2.0；企业部分为专有。官方镜像与二进制含非公开代码，条款允许内部原样使用/API 调用，对包装、修改、托管服务、直接向客户暴露或商业嵌入另有条件和例外。采用前选定具体发行与用途。 [固定版 LICENSE](https://github.com/windmill-labs/windmill/blob/28985a122cc303200bb36c5c67037f5f2157299c/LICENSE)
- **Dify**：基于 Apache-2.0 并附有条件，条款将一个 workspace 定义为一个 tenant。运营多租户环境须获得书面授权，采用其前端时保留标识和版权信息。单一组织用户数量不能直接判定许可；单 workspace 也不能替代明镜的组织隔离验收。 [固定版 LICENSE](https://github.com/langgenius/dify/blob/7bef4e1b2dc21b2c694d3243425dd3fa6288f916/LICENSE)
- **B 的上游源码**：Temporal Server/SDK 和 Pydantic AI 固定版根许可为 MIT；PostgreSQL 采用其数据库许可；Psycopg 采用 LGPLv3，二进制包的附带库另核。 [Temporal Server](https://github.com/temporalio/temporal/blob/v1.32.2/LICENSE) · [Python SDK](https://github.com/temporalio/sdk-python/blob/1.36.1/LICENSE) · [Pydantic AI](https://github.com/pydantic/pydantic-ai/blob/v2.71.0/LICENSE) · [PostgreSQL](https://github.com/postgres/postgres/blob/REL_17_12/COPYRIGHT) · [Psycopg](https://github.com/psycopg/psycopg/blob/3.3.9/LICENSE.txt)
- **镜像和模型**：实验已固定 Python、PostgreSQL、Temporal Server/admin-tools、Ollama 镜像以及 Qwen2.5 1.5B 权重摘要。精确摘要可定位内容，不会赋予容器内所有 OS/第三方组件同一种许可。P1 曾生成 SBOM 并有待处置的制品风险，B 的新 runner、完整应用、所选模型权重及其使用方式须按目标平台重新生成 SBOM、核对许可和 NOTICE、核对制品来源、扫描及复验。实验用 admin-tools / Ollama 不自动计入正式部署。 [Python 镜像](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/b/Dockerfile) · [数据库与引擎镜像](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/core/infra/compose.yaml) · [推理镜像和权重](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/model.sh) · [旧制品结果](https://github.com/zhuquanwei111/mingjing---agent/blob/fdf04240eba747a9a681a1dad627da22d4b89cdd/p1-walking-skeleton/P1_REPORT.md)

以下 32 项取自[B 的 AMD64 锁](https://github.com/zhuquanwei111/mingjing---agent/blob/553114d2114cc77081c415ad1697e74be282c9a8/lab/architecture/b/linux-amd64.lock)，按每个包标明核到的层级。15 项用整份本地 wheel 的 SHA-256 对上锁值，再读取 METADATA；3 项只有同版本本地发行元数据；13 项核到对应上游许可文件；1 项尚缺固定发行的可核对许可。包声明不能替代发行物内原生组件的逐项义务核查，目标 ARM64 仍须另锁、另验。

| 包与锁定版本 | 声明或源码条款 | 证据范围 |
| --- | --- | --- |
| annotated-types 0.8.0 | MIT | 固定 wheel |
| anyio 4.16.0 | MIT | 固定 wheel |
| certifi 2026.11.20 | MPL-2.0（CA 证书包） | [上游许可](https://github.com/certifi/python-certifi/blob/2026.11.20/LICENSE) |
| charset-normalizer 3.5.3 | MIT | [上游许可](https://github.com/jawah/charset_normalizer/blob/3.5.3/LICENSE) |
| genai-prices 0.2.5 | MIT | [上游许可](https://github.com/pydantic/genai-prices/blob/v0.2.5/LICENSE) |
| griffelib 2.4.1 | ISC | [上游许可](https://github.com/mkdocstrings/griffe/blob/2.4.1/LICENSE) |
| h11 0.16.0 | MIT License | 固定 wheel |
| httpcore2 2.16.2 | BSD-3-Clause | 固定 wheel |
| httpx2 2.16.2 | BSD-3-Clause | 固定 wheel |
| idna 3.20 | BSD-3-Clause | 固定 wheel |
| jiter 0.19.0 | MIT | [上游许可](https://github.com/pydantic/jiter/blob/v0.19.0/LICENSE) |
| logfire-api 6.0.0 | MIT | [上游许可](https://github.com/pydantic/logfire/blob/v6.0.0/LICENSE) |
| nexus-rpc 1.5.0 | MIT | 固定 wheel |
| openai 3.57.0 | Apache-2.0 | [上游许可](https://github.com/openai/openai-python/blob/v3.57.0/LICENSE) |
| opentelemetry-api 1.45.2 | Apache-2.0 | 固定 wheel |
| protobuf 7.36.2 | 3-Clause BSD License | 同名同版本本地元数据 |
| psycopg-binary 3.3.9 | LGPL-3.0-only | 同名同版本本地元数据 |
| psycopg 3.3.9 | LGPL-3.0-only | 固定 wheel |
| pydantic-ai-slim 2.71.0 | MIT | [上游许可](https://github.com/pydantic/pydantic-ai/blob/v2.71.0/LICENSE) |
| pydantic-graph 2.71.0 | MIT | [上游许可](https://github.com/pydantic/pydantic-ai/blob/v2.71.0/LICENSE) |
| pydantic 2.14.4 | MIT | [上游许可](https://github.com/pydantic/pydantic/blob/v2.14.4/LICENSE) |
| pydantic_core 2.50.5 | MIT | [上游许可](https://github.com/pydantic/pydantic/blob/v2.14.4/pydantic-core/LICENSE) |
| regex 2026.11.19 | 原 CPython 部分的许可及新增部分 Apache-2.0 | [上游许可](https://github.com/mrabarnett/mrab-regex/blob/2026.11.19/LICENSE.txt) |
| requests 2.34.2 | Apache Software License | 固定 wheel |
| sniffio 1.3.1 | MIT License, Apache Software License | 固定 wheel |
| temporalio 1.36.1 | MIT | 同名同版本本地元数据 |
| tiktoken 0.14.0 | MIT | [上游许可](https://github.com/openai/tiktoken/blob/0.14.0/LICENSE) |
| truststore 0.10.5 | MIT | 固定 wheel |
| types-protobuf 7.35.1.20261122 | 待核 | 缺此固定 wheel 的许可元数据 |
| typing-inspection 0.4.5 | MIT | 固定 wheel |
| typing_extensions 4.16.0 | PSF-2.0 | 固定 wheel |
| urllib3 2.8.0 | MIT | 固定 wheel |
