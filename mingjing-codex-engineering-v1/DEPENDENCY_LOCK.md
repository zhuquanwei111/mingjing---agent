# 明镜依赖锁定候选

核验日期为 2026-11-19（北京时间）。本文件记录 P1 候选及只读解析证据。最终锁需通过目标平台安装、集成测试、制品扫描和许可复核。

## 四个核心候选

| 组件 | 固定版本与提交 | 许可和发行证据 |
| --- | --- | --- |
| Temporal Server OSS | `v1.32.2` · `6d085822273f4336796e6959c73ab1d14a23eb77` | MIT。 [发行说明](https://github.com/temporalio/temporal/releases/tag/v1.32.2) · [LICENSE](https://github.com/temporalio/temporal/blob/v1.32.2/LICENSE) · [go.mod](https://github.com/temporalio/temporal/blob/v1.32.2/go.mod) |
| Temporal Python SDK | `temporalio==1.36.1` · `968c3c9dcf508ceca3f4e34b9ea910425351f6c5` | MIT，Python ≥3.11。 [发行说明](https://github.com/temporalio/sdk-python/releases/tag/1.36.1) · [LICENSE](https://github.com/temporalio/sdk-python/blob/1.36.1/LICENSE) · [PyPI JSON](https://pypi.org/pypi/temporalio/1.36.1/json) |
| LangGraph OSS Python | `langgraph==1.2.22` · `08a2016953789a4f579b4d36bd1967941ec62012` | MIT，Python ≥3.10。 [发行说明](https://github.com/langchain-ai/langgraph/releases/tag/1.2.22) · [库 LICENSE](https://github.com/langchain-ai/langgraph/blob/1.2.22/libs/langgraph/LICENSE) · [PyPI JSON](https://pypi.org/pypi/langgraph/1.2.22/json) |
| Temporal LangGraph 官方插件 | `temporalio-langgraph==1.0.0` · `b7995551f9f8ebb3bb710c29486c21d9fcd05870` | MIT，Python ≥3.11。上游在本版本声明 GA，流式仍为实验功能。 [发行说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0) · [LICENSE](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/LICENSE) · [PyPI JSON](https://pypi.org/pypi/temporalio-langgraph/1.0.0/json) |

所有三个 PyPI 固定版本的发行文件查询均未标为 yanked。MIT 许可随对应组件保留版权与许可通知。商业 Agent Server 具有独立的部署和授权条件。 [LangSmith 部署许可说明](https://docs.langchain.com/langsmith/data-plane)

## 包兼容范围与 Server 条件

| 来源 | 运行依赖声明 |
| --- | --- |
| `temporalio-langgraph==1.0.0` | `temporalio>=1.36.0,<2`、`langgraph>=1.2.0,<2`、`langchain-core>=1.4.0,<2`、`pydantic>=2.7.4,<3`、`typing-extensions>=4.2.0,<5`。 |
| `langgraph==1.2.22` | `langchain-core>=1.4.7,<2`、`langgraph-checkpoint>=4.3.0,<5.0.0`、`langgraph-prebuilt>=1.1.0,<1.2.0`、`langgraph-sdk>=0.4.6,<0.5.0`、`pydantic>=2.7.4`、`xxhash>=3.5.0`。 |
| `temporalio==1.36.1` | `nexus-rpc==1.5.0`、`protobuf>=4.21.12,<8`、`types-protobuf>=4.24,<8`、`typing-extensions>=4.2.0,<5`。可选 `opentelemetry` extra 引入 API/SDK `>=1.26,<2`。 |
| 交集 | CPython ≥3.11，选择 3.12.16。选中的 SDK 与 LangGraph 在插件范围内。共同约束为 `langchain-core>=1.4.7,<2`、`pydantic>=2.7.4,<3`。 |

`temporalio[langgraph]` 对插件的最低约束是 0.1.0。显式固定独立插件包，采用发布包的 `temporalio.langgraph` 入口。插件源码使用 LangGraph 内部接口，新的 LangGraph 次版本和传递版本变动同样需要回归验证。 [插件固定 pyproject](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/pyproject.toml) · [SDK PyPI 元数据](https://pypi.org/pypi/temporalio/1.36.1/json)

Temporal 文档给出 SDK/Server 一般兼容说明。Worker Versioning 单独要求自托管 Server ≥1.29.1，候选 1.32.2 达到该最低要求。P1 应核对运行中的命名空间配置、版本指派和具体插件 API 能力。PostgreSQL 可见性文档列出 PostgreSQL ≥12 与 Server ≥1.20 的支持范围，P1 选处于支持期的 PostgreSQL 17.12，使用 v1.32.2 的 `schema/postgresql/v12` 主库和可见性 schema。 [Temporal Server 兼容说明](https://docs.temporal.io/temporal-service/temporal-server) · [Worker Versioning 最低版本](https://docs.temporal.io/production-deployment/worker-deployments/worker-versioning#minimum-versions) · [可见性矩阵](https://docs.temporal.io/self-hosted-guide/visibility) · [固定 Server SQL Schema](https://github.com/temporalio/temporal/tree/v1.32.2/schema/postgresql/v12)

## 制品与运行依赖

| 用途 | 固定候选 | SHA-256 |
| --- | --- | --- |
| Server 镜像 | `docker.io/temporalio/server:1.32.2` | 索引 `7bf69188a6232fea14869b9cef3d94aa82a1601d99517f7e86c71f22da4e0670` |
| SQL 初始化/管理镜像 | `docker.io/temporalio/admin-tools:1.32.2` | 索引 `4a95866efba29d7e17ab012df5232795e8b0ad0f7d5f9d1ec4df321f7792a754` |
| P1 PostgreSQL 镜像 | `docker.io/library/postgres:17.12-alpine` | 索引 `526f86d93c6ea08fd3f1fe5605650cacc781b2c6013169a0ad8f42c7d3d84f32` |
| 本地 CLI · macOS arm64 | `temporal_cli_1.10.1_darwin_arm64.tar.gz` | `94f7f982b26438e8abbde6000ba471b694be6a2413b31f6162f87a9f9c48c738` |

已从 registry manifest 或 Docker Hub 的精确标签元数据读取镜像索引。三组索引均含 linux/amd64 与 linux/arm64。P1 Compose 应使用 `image@sha256:...`，并记录实际平台的子 manifest。`temporalio/auto-setup:1.32.2` 查询返回 404，采用同版 Server、admin-tools 与显式 schema job。CLI v1.10.1 的 `go.mod` 指向 `go.temporal.io/server v1.32.2`，适用于本地 `start-dev`。用于生产的 PostgreSQL 版本和基础镜像待部署环境确认。 [Server 镜像标签](https://hub.docker.com/r/temporalio/server/tags?name=1.32.2) · [admin-tools 标签](https://hub.docker.com/r/temporalio/admin-tools/tags?name=1.32.2) · [Postgres 精确标签元数据](https://hub.docker.com/v2/repositories/library/postgres/tags/17.12-alpine) · [CLI 发行文件](https://github.com/temporalio/cli/releases/tag/v1.10.1) · [CLI go.mod](https://github.com/temporalio/cli/blob/v1.10.1/go.mod)

- 本地冒烟的 Python 依赖为三个核心包。P1 全量增加 `psycopg[binary]==3.3.9`、`pytest==9.2.0`、`temporalio[opentelemetry]==1.36.1`。Psycopg 与 binary wheel 标记 LGPL-3.0-only，生产分发需复核动态链接组件和应带通知。pytest 为 MIT，PostgreSQL 服务采用 PostgreSQL License。 [Python 3.12.16](https://www.python.org/downloads/release/python-31216/) · [Psycopg](https://pypi.org/project/psycopg/3.3.9/) · [Psycopg binary](https://pypi.org/project/psycopg-binary/3.3.9/) · [pytest](https://pypi.org/project/pytest/9.2.0/) · [PostgreSQL 许可](https://www.postgresql.org/about/licence/)
- 已解析依赖包含 HTTP 客户端、LangSmith SDK、原生 wheels 和多种 SPDX 许可。例如 LangSmith 的 `httpx2` 来自其声明，`orjson` 的 wheel 元数据含 MPL-2.0，不能沿用四核心 MIT 作依赖许可结论。P1 复核 wheel 许可文件、来源证明和原生库清单。保持供应商与 SaaS 遥测出口关闭。 [LangSmith 包依赖](https://pypi.org/pypi/langsmith/0.15.0/json) · [orjson 包元数据](https://pypi.org/pypi/orjson/3.13.0/json)

## 官方样例入口

| 组件 | P1 参考入口 |
| --- | --- |
| Temporal Server | 固定 Tag 的 dev 入口及官方 PostgreSQL Compose 拓扑。明镜配置采用隔离网络、数据库角色和固定镜像。 [Server README](https://github.com/temporalio/temporal/blob/v1.32.2/README.md) · [PostgreSQL Compose 示例](https://github.com/temporalio/samples-server/blob/main/compose/docker-compose-postgres.yml) |
| Python SDK | Quick Start 的 Activity、Workflow、Worker 和 Client，及文档化 `Replayer`。 [SDK 1.36.1 README](https://github.com/temporalio/sdk-python/blob/1.36.1/README.md) |
| LangGraph | 固定 Tag 的 `StateGraph` 示例与中断语义。 [LangGraph 1.2.22 README](https://github.com/langchain-ai/langgraph/blob/1.2.22/libs/langgraph/README.md) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) |
| 官方插件 | 固定 Tag 的注册、重试、中断、缓存与流式说明。固定提交的 Graph/Functional Hello World 含 `run_worker.py` 与 `run_workflow.py`，另有中断、流和 Continue-As-New 的独立例子。示例清单范围较宽，P1 烟测依赖以本候选锁为准，并仅选用纯函数示例入口。 [插件 1.0.0 README](https://github.com/temporalio/ai-integrations/blob/b7995551f9f8ebb3bb710c29486c21d9fcd05870/python/langgraph/README.md) · [官方样例固定提交](https://github.com/temporalio/samples-python/tree/2fb335017cabc56790a6601f56340c16fce68947/langgraph_plugin) · [样例依赖](https://github.com/temporalio/samples-python/blob/2fb335017cabc56790a6601f56340c16fce68947/pyproject.toml) |

## 安全公告与查询范围

- **Temporal Server v1.32.2。** 上游发行说明记录 Go 1.26.10、`x/net` 0.60.0、`go-jose` 4.1.6、Alpine 3.24.3 安全更新。公告源同时记录命名空间写权限变化。仓库公告 API 和 GitHub 全局 `go.temporal.io/server@1.32.2` 查询未返回匹配条目。运行前检查实际镜像层、Go 二进制和已知受影响文件。 [安全修复 PR](https://github.com/temporalio/temporal/pull/12831) · [发行说明](https://github.com/temporalio/temporal/releases/tag/v1.32.2) · [仓库公告](https://github.com/temporalio/temporal/security/advisories)
- **SDK 与官方插件。** 两个仓库公告 API、GitHub 全局按 PyPI 精确版本查询以及 PyPI JSON 均未返回命中。插件仍有已记录的重放、取消和缓存限制。 [SDK 公告](https://github.com/temporalio/sdk-python/security/advisories) · [插件仓库公告](https://github.com/temporalio/ai-integrations/security/advisories) · [插件发行说明](https://github.com/temporalio/ai-integrations/releases/tag/python/langgraph/v1.0.0)
- **LangGraph OSS 与传递依赖。** 历史 checkpoint 反序列化公告涉及 `langgraph<=1.0.9` 或 `langgraph-checkpoint<=4.1.0`。SDK 流路径公告涉及 `langgraph>=1.2.3,<1.2.14` 和 `langgraph-sdk>=0.4.0,<0.4.6`。当前解析为 1.2.22 / 4.3.2 / 0.4.14，均在这些影响区间之外。CLI 和可选数据库 checkpointer 的公告涉及其他制品。P1 使用受信输入、严格 msgpack 模式并核验允许的 DTO。 [LangGraph 公告列表](https://github.com/langchain-ai/langgraph/security/advisories) · [checkpoint 反序列化公告](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-fjqc-hq36-qh5p) · [SDK 流路径公告](https://github.com/langchain-ai/langgraph/security/advisories/GHSA-3fx2-cqw9-xr3c) · [4.3.2 serializer](https://github.com/langchain-ai/langgraph/blob/checkpoint%3D%3D4.3.2/libs/checkpoint/langgraph/checkpoint/serde/jsonplus.py)
- **P1 Python 候选快照。** 将下方 52 个 PyPI 包名及精确版本提交至 OSV `/v1/querybatch`，本次返回 52 项且无漏洞命中。这个查询范围为所列的 PyPI 包版本。P1 在安装前重查安全公告，并单独扫描镜像、OS、原生库及生产制品。 [OSV 批量查询接口](https://google.github.io/osv.dev/api/#tag/api/operation/OSV_QueryBatch)

## 解析复现

以下 dry-run 只解析项目和 wheel 元数据。本次使用 macOS arm64、CPython 3.12.16 和 pip 26.2.2。版本解析结果保留在本文件的候选快照中。

```bash
PIP_CONFIG_FILE=/dev/null python3.12 -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --only-binary=:all: --no-cache-dir \
  --index-url https://pypi.org/simple --report /tmp/mingjing-p0-pip-report.json \
  'temporalio[opentelemetry]==1.36.1' 'langgraph==1.2.22' \
  'temporalio-langgraph==1.0.0' 'psycopg[binary]==3.3.9' 'pytest==9.2.0'
```

### macOS arm64 / CPython 3.12.16 候选快照

这 52 项来自 P0 解析选择的 wheel 和哈希，已用 `--require-hashes --dry-run --only-binary=:all:` 复验。可作为 P1 `requirements/macos-arm64.lock` 的初始输入。Linux 重新解析与审查，并在目标架构用 `--require-hashes` 安装、运行 `pip check` 及样例/故障测试。macOS 候选含要求 macOS 15 或以上的 wheel。


```text
annotated-types==0.8.0 --hash=sha256:f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0
anyio==4.16.0 --hash=sha256:c66ae634e0b8228396b801741beb3294326d4b6102f7bba4041c0dfb58c29026
certifi==2026.10.23 --hash=sha256:e9b54de76e530bb6cf0ccd036787103acb58fd42ba930ea8bf948ddbaa2f61d1
charset-normalizer==3.5.2 --hash=sha256:ed2a239c0ea213acc1908150a3037257083c7c083128f1a4cec2ec4b97dca491
distro==1.9.0 --hash=sha256:7bffd925d65168f85027d8da9af6bddab658135b840670a223589bc0c8ef02b2
h11==0.16.0 --hash=sha256:63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86
httpcore==1.0.9 --hash=sha256:2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55
httpcore2==2.16.2 --hash=sha256:16051ae2a42f776007543f32de9349a317b23d2cbb4e1456b4bac0e88b87419a
httpx==0.28.1 --hash=sha256:d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad
httpx2==2.16.2 --hash=sha256:f05c13aade4c45dbf1c9060647a1058f0acad62398fad96e741269edb33d46f5
idna==3.20 --hash=sha256:ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c
iniconfig==2.3.1 --hash=sha256:9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7
jsonpatch==1.47 --hash=sha256:c9ba6de59c481bf2be05041514ecb0d97f994aa645c4e00831805dbe2281811a
jsonpointer==3.12 --hash=sha256:89f391335ee2719ae72149e1bf30a4d4c7c5d92f15a3f53faa8d20cc7c6c7f19
langchain-core==1.8.3 --hash=sha256:4d2764d2ab4faf3fec9f17515f15c0d3485a6ef55f75c088f6929944225ff578
langchain-protocol==0.0.21 --hash=sha256:7f42f9eae7c08bb9d74850057da50b5483970a3df91b7a8a5aadec6a3dfa4d12
langgraph==1.2.22 --hash=sha256:0f8ebec55a58667e40474a0e55bdb4f06a8c7a1d98cde2b7c8d996a2ee78fe3f
langgraph-checkpoint==4.3.2 --hash=sha256:60e02eb2c2eefc4c22fb1549f1c90b85ce9617377604596c5f34fbd6af0bd6e9
langgraph-prebuilt==1.1.3 --hash=sha256:7b55eb1c2004348b73b9af9e2f81e5f3eda47dcf13d885ccb4195538426c55ce
langgraph-sdk==0.4.14 --hash=sha256:d47a6755890ae537aa80613a3138680ac77f5d256a2d3953af95a96328e6964d
langsmith==0.15.0 --hash=sha256:d6f7aa67e4c984ce7c7b6a1bdb7fc50ce3caaca032b42805f0f6a2d6458f42be
nexus-rpc==1.5.0 --hash=sha256:5d6e856972be812573948df02da2257344c407a8eaa99977b5d38be54448305a
opentelemetry-api==1.45.2 --hash=sha256:2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34
opentelemetry-sdk==1.45.2 --hash=sha256:ff974ea70ee4f1d51e2ec152db37c2b626c7bf82bb3f7d86114fd8704e7199c6
opentelemetry-semantic-conventions==0.66b2 --hash=sha256:4cbe61e5f9275d57ab31708446e7938ef4291ebbe6a7fca6f7a629c5acae87d8
orjson==3.13.0 --hash=sha256:6ff2a2c67f35202f7d823753d38ad371a9b7fc297567cdfff4420e763cb9f6f8
ormsgpack==1.13.1 --hash=sha256:c0098ca1145f64c07a12ad08156220c51a41904ad51ef5d8038ddd284aca6525
packaging==26.3 --hash=sha256:d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c
pluggy==1.7.0 --hash=sha256:7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec
protobuf==7.36.2 --hash=sha256:cbc70b17ee27e28894c7fee8bb04be1abead49e936bc70eb60052531eee2079e
psycopg[binary]==3.3.9 --hash=sha256:d2d7d04a1ce6dab4f5b27316bea3b52585cafa2f2d631e5b09dd69823f5c26f6
psycopg-binary==3.3.9 --hash=sha256:08689018e9169ca8e6769f5b3f2ce748442bda95b5f1ec260995a8ff63e6d6a4
pydantic==2.14.3 --hash=sha256:3f7b347782ab7e4cf4c798496ae3a82787d9f21ec12676a9c564355eeef8daa8
pydantic_core==2.50.4 --hash=sha256:1e20cbde2b6deb33a51d08cd168454dd9044ec7d4474056f4d98d63f51578783
Pygments==2.21.0 --hash=sha256:2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9
pytest==9.2.0 --hash=sha256:07acdcf88ec174f907dc01af70bf52d49b014bbab03faeeade31c96b18c2e588
PyYAML==6.0.3 --hash=sha256:fc09d0aa354569bc501d4e787133afc08552722d3ab34836a80547331bb5d4a0
requests==2.34.2 --hash=sha256:2a0d60c172f83ac6ab31e4554906c0f3b3588d37b5cb939b1c061f4907e278e0
requests-toolbelt==1.0.0 --hash=sha256:cccfdd665f0a24fcf4726e690f65639d272bb0637b9b92dfd91a5568ccf6bd06
sniffio==1.3.1 --hash=sha256:2f6da418d1f1e0fddd844478f41680e794e6051915791a034ff65e5f100525a2
temporalio[opentelemetry]==1.36.1 --hash=sha256:175a89e59ed9e7cc5795609d937c80111513ca9d70b0ed9da4ed7792163c863a
temporalio-langgraph==1.0.0 --hash=sha256:13026c212e489b29289bc76bf64b7913185102bbc98d35f654a2dc1cd8f6a30a
tenacity==9.2.1 --hash=sha256:9e56f17539296baab7beabb08b92f6ee3d7be92d8be72d763360677c2ad6580e
truststore==0.10.5 --hash=sha256:9aaaedaefaf06d8b206278cf8b5012bc897f485a874503501e12d776df78951c
types-protobuf==7.35.1.20260906 --hash=sha256:5155e48569e0dabff303fdf578db96cd31ea9a4a63b18018a4ceac6b0ae17462
typing-inspection==0.4.5 --hash=sha256:bc210535442b39e1bf2805e0c7a17dfd6a4ace760c84c7f7d16245d23a6b1c39
typing_extensions==4.16.0 --hash=sha256:481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8
urllib3==2.8.0 --hash=sha256:0cf3cae568d36aa9576b28dfb35f11328f1cb974ca7647d9475ebb86c75ac6e3
uuid_utils==0.19.0 --hash=sha256:84929d8c594381c6f1444afa2a25cce9ff7edac99d35e071ebc48275bae83730
websockets==17.4 --hash=sha256:bcad49104711f88b2b7c3ba166de172857d837248205e541b044a552558fecc3
xxhash==4.1.0 --hash=sha256:163e47667ae6449ddbcb58aff4b9a32e937473cdca927fe74e0685919b226d88
zstandard==0.25.0 --hash=sha256:913cbd31a400febff93b564a23e17c3ed2d56c064006f54efec210d586171c00
```
