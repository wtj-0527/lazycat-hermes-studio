# lazycat-hermes-studio

Hermes AI 智能体 Web 管理界面 — 全 rootfs 持久化

## 解决什么问题

容器重启或镜像升级后，apt/pip/npm 安装的工具丢失。
通过 base+upper overlay 架构，rootfs 变更持久化到 btrfs 卷，装一次永远在。

## 原理

```
首次启动：snapshot 镜像 rootfs → /lzcapp/cache/rootfs/base/（持久化）
用户安装：apt install vim → 写入 /lzcapp/cache/rootfs/upper/（overlay copy-up）
镜像更新：检测 lowerdir hash 变化 → re-snapshot base → upper 用户包保留
```

## 安装

下载最新 LPK，通过懒猫 Web UI 安装。

当前包装将 Hermes Studio 普通附件上传上限配置为 500 MiB
（`HERMES_MAX_UPLOAD_SIZE=524288000`）。nginx 包装层不额外限制请求体大小。

说明：当前 `/home/agent` 的主持久化路径是 `document.private` 对应的
`/lzcapp/documents/{{ .S.DeployUID }}`。`setup_script` 里保留的
`/lzcapp/var/home -> /home/agent` 迁移逻辑仅用于兼容旧版本历史数据，
不是当前主持久化方案。

## 装工具

进容器后直接：
```bash
apt install vim git curl htop     # → /usr/bin/，重启不丢
pip install <package>              # → /usr/lib/python*/，重启不丢
npm install -g <package>           # → /usr/local/bin/，重启不丢
uv tool install <package>          # → ~/.local/bin/，重启不丢
```

重启不丢，镜像升级也不丢。

## 版本日志

见 [CHANGELOG.md](CHANGELOG.md)

## 自动化维护

本仓库包含两个 GitHub Actions workflow：

- `.github/workflows/check-hermes-studio-upgrade.yml`：每天北京时间 10:00 检查 Hermes Web UI 官方新版本，发现新版本后同步镜像到 ACR，并创建或更新升级 PR；不会自动合并。
- `.github/workflows/release-lpk.yml`：PR 合并到 `main` 后自动打包 LPK、创建/更新 GitHub Release、上传 LPK 资产。

自动检查 workflow 需要配置以下 GitHub Secrets：

- `ACR_REGISTRY`：例如 `registry.cn-shanghai.aliyuncs.com`
- `ACR_NAMESPACE`：例如 `wtjking`
- `ACR_USERNAME`：ACR 用户名
- `ACR_PASSWORD`：ACR 密码或访问令牌

本仓库自动升级 / 自动发布链路的真实修复记录见：

- [docs/automation-recovery-notes.md](docs/automation-recovery-notes.md)

## License

[AGPL-3.0](LICENSE)

## Rootfs 升级协调器（fail-closed）

普通启动可并行；镜像变化时的 rootfs 删除/复制必须先取得共享 playground
Docker 上的 `hermes-studio-rootfs-upgrade-lock`。所有实例必须挂载同一个
`/data/playground/docker.sock`（现有 compose override），不得改为各实例私有 Docker。
升级已有安装前应核对实际挂载，因为 compose override 不一定在升级时重新生成。

协调器使用独立的 `registry.cn-shanghai.aliyuncs.com/wtjking/nginx:alpine`
镜像作为仅运行 sleep 的标记容器；缺失时拉取，不要求 playground 中存在 Hermes
业务镜像。Docker、拉取或队列注册失败会停止 setup，绝不无锁重建。
离线部署需事先在共享 playground Docker 中准备该协调镜像。

安全优先：锁与排队标记不设自动过期，不使用 `--rm`，心跳只用于展示。
复制失败、setup 异常退出或宿主重启后可能留下锁/队列，需要人工恢复；
这比误判慢 I/O 已停止并放行另一个重建更安全。协调器状态存储必须持久化，
升级期间禁止删除标记、清理 playground 容器或重置 Docker 数据。

恢复步骤：先停止/禁止相关实例自动唤醒，确认所有对应 setup、rm、cp 进程已经退出
（尤其不能只检查 setup 父进程），再检查锁的 request/instance 标签，删除该失败任务
对应的 active/queue/progress 标记。不可按心跳时间盲删锁，也不可在复制仍运行时清理。
之后只启动一个实例观察取得锁、重建成功、释放锁，再允许其他实例恢复。
新旧脚本不能混跑：旧版会在协调器失败时无锁执行，也会按心跳清理锁。

测试：`uv run --with pytest --with pyyaml python -m pytest tests/test_serialized_snapshot.py tests/test_upgrade_coordinator_runtime.py -q`。
运行时测试执行 manifest 中的真实 shell，使用进程间加锁的模拟 Docker；
覆盖三实例互斥与 Docker/拉取/注册故障，不代替真实设备升级验收。
