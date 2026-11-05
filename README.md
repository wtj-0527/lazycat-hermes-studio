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

LazyCat MCP 的用户 Ticket 仅保存在当前 sidecar 进程内存中，不写入磁盘。
每个经过 Hermes Studio 的正常认证请求都会刷新该 Ticket；sidecar 重启后，
用户下一次访问页面、发送消息或调用 API 即可自动恢复 MCP 授权。

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

## 发布维护

当前主线不包含自动升级或 LPK 发布 workflow。发布时固定上游 `main` 的完整提交，
按锁文件重新构建 Studio，并将镜像推送至 ACR；两个 Studio 服务必须引用同一镜像摘要。
同时更新 `package.yml`、`content/release-provenance.json` 和版本日志，通过 PR 合并。

从合并后的包装仓提交运行 `lzc-cli project build -o <输出路径>`，校验包内 manifest、
版本、compose override 和 content 内容，再创建对应版本的 GitHub Release，上传 LPK、
SHA-256 校验文件及构建验证证据。发布不包含安装 LPK、升级设备或重启实例。

上游 Studio 镜像构建统一使用 `tools/Dockerfile.upstream-build`。该配方显式将
Node.js 下载源和 npm registry 设置为 `npmmirror.com`，不能依赖宿主机的 npm
配置自动传入 Docker；如需切换镜像，使用 `NPM_REGISTRY` 和 `NODE_MIRROR`
build args，并在构建证据中记录最终值。

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

## 持久化权限故障防护

启动前验证 overlay 挂载，任何目录挂载失败都会停止服务，避免持久化工具
被隐藏但应用继续运行。管理员 override 替换包内 override 时需要显式保留
SYS_ADMIN、fuse 和共享 Docker socket。详见 `content/ROOTFS-REPAIR.md`；
随包提供只生成候选配置、不自动修改宿主机的合并工具。

## 自定义域名与跨域来源

安装包不再设置 `CORS_ORIGINS`，沿用上游默认的同主机来源校验。反向代理应保留正确的外部 Host；如确需跨域访问，请由管理员配置精确的来源白名单，不默认放行任意来源。此变更不取消登录与权限校验。
