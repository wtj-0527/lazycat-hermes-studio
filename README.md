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
