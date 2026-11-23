# Mingjing P1 Walking Skeleton

> 本目录用于既有 P1 验收与恢复回归。路线 B 的新开发使用[新开发包](../mingjing-codex-engineering-v2/README.md)。

这是 [P1 执行计划](../mingjing-codex-engineering-v1/P1_EXECUTION_PLAN.md) 的隔离验证仓库。所有数据、身份、模型输出和外部回执均由测试夹具生成。验收结论和证据索引见 [P1_REPORT.md](P1_REPORT.md)。

`record_marker@1` 通过普通 HTTP API、Temporal Workflow 和受控 LangGraph 工具调用同一个 PostgreSQL 执行边界。API 使用回环地址。Worker 和 API 在独立进程运行。Temporal 主库、可见性库与明镜业务库分库分角色，业务数据库保存任务、审批、预算、收据及审计。Workflow History 保存执行与重放事件。产物字节使用试验目录，版本和读取权限按业务库记录判断。

## macOS arm64 本地冒烟

需要 CPython 3.12.16、curl 及 shasum。以下命令从本仓库的 `p1-walking-skeleton/` 目录执行。脚本使用空闲回环端口和项目临时目录，并在退出时关闭 CLI Server。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements/macos-arm64.lock
.venv/bin/python -m pip check
mkdir -p .p1/bin
curl -fL https://github.com/temporalio/cli/releases/download/v1.10.1/temporal_cli_1.10.1_darwin_arm64.tar.gz \
  -o .p1/temporal_cli_1.10.1_darwin_arm64.tar.gz
printf '%s\n' '94f7f982b26438e8abbde6000ba471b694be6a2413b31f6162f87a9f9c48c738  .p1/temporal_cli_1.10.1_darwin_arm64.tar.gz' | shasum -a 256 -c -
tar -xzf .p1/temporal_cli_1.10.1_darwin_arm64.tar.gz -C .p1/bin temporal
bash infra/smoke.sh
```

## Linux ARM64/x86_64 隔离验收

从 Git 仓库根目录执行 `make acceptance`，可按同一顺序运行以下验收和恢复检查，并在成功或失败后清理本次 Compose project。支持原有 ARM64 环境与已有 Instabox 的 x86_64 环境；Docker 构建按目标架构选择对应带哈希的依赖锁，无需手工修改 Dockerfile。各环境分工见[开发流程](../docs/development.md#现有环境怎么使用)。

在专用 Linux VM 中复制本仓库的文件，排除 `.git/`、`.p1/`、`.venv/`。本次使用 Lima 2.3.0 和 [VM 配置](infra/lima.yaml)。配置未挂载宿主机目录或转发 SSH agent，容器运行时仅安装在该 VM 中。

需要逐步运行时，以下命令从 VM 内的 `p1-walking-skeleton/` 目录执行。以项目私有的 `.p1/runtime.env` 保存新生成的合成凭据。Compose 仅使用内部网络，并且没有对宿主机发布任何服务端口。测试 runner 以 UID 10101 执行。旧版插件的测试程序使用独立 Python 环境，避免同名 namespace 包从新版环境加载。

```bash
sh infra/new-run.sh
sh infra/accept.sh
sh infra/verify-backup.sh
sh infra/verify-temporal-restart.sh
sh infra/verify-rebuild.sh
```

`infra/accept.sh` 将测试证据复制到 `.p1/results/`。备份命令比较源库与新建恢复库的业务收据哈希和行数。Server 重启前后核对同一执行历史。重建命令创建另一套 Compose project 与命名空间、检查初始空库并重新运行冒烟。保留所需证据后，`sh infra/compose.sh down --volumes` 清理当前项目的合成数据库及容器。

如需单独复跑，先启动固定 Server 并执行命名空间初始化，再用同一 Compose runner 执行以下命令。

```bash
sh infra/compose.sh up -d --wait temporal
sh infra/compose.sh run --rm --no-deps namespace
sh infra/compose.sh build test
sh infra/compose.sh run --rm --no-deps -T test python -m pytest -q -s tests/test_at03_at05.py tests/test_at09_at10.py
```
