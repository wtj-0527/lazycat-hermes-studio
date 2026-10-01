# Rootfs 持久化挂载检查与管理员 override 修复

本包需要包内 compose.override.yml 的 SYS_ADMIN、/dev/fuse 和共享
playground Docker socket。宿主机管理员 override 会替换包内 override，
不会自动合并。LPK 不会、也不能偷偷修改管理员配置。

修复版启动前用独立临时目录验证 overlay；失败立即停止，不重建 base，
不修改 upper，避免出现“0 dirs overlay”却继续启动的假持久化状态。
实际挂载失败也立即停止。探测目录在 /lzcapp/cache 下，不触碰已有数据。

若现有管理员 override 存在，管理员应备份后合并包内要求，保留原端口等配置。
随包 content/merge-admin-override.py 可生成候选文件（需要 Python3/PyYAML），
不会写入宿主机配置，也不会重建服务。例：

```sh
python3 merge-admin-override.py admin.before.yml compose.override.yml candidate.yml
```

检查候选文件并使用 lzc-docker-compose config 验证后，再由管理员替换
持久管理员 override，按平台流程重建 hermes-webui。不要删除 upper，
不要在线强行挂载 /usr，也不要把重装工具作为挂载失败的解决方法。

验收：容器 CapAdd 包含 SYS_ADMIN；findmnt -T /usr 的 TARGET 为 /usr；
启动日志为 6 dirs overlay；gh --version 可用（若此前已安装）；/livez 正常。
本包不是对任意宿主机 override 的自动修复：宿主机缺少权限时会明确阻止启动。
