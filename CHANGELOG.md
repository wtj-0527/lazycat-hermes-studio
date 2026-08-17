# 2026.08.16.2029

## History GROUP 折叠与键盘分页

- Hermes Studio 运行镜像升级至 `v0.6.43-pr2581-30580ce3-202608162029`，严格构建自已验收的 PR #2581 commit `30580ce3b7d22bd5a0c795008d16754529f60d9a`。
- History 的 `GROUP` 分组支持持久化折叠/展开、键盘操作与当前 Room 自动展开；“加载更多会话”继续仅在 `hasMore=true` 时显示，并可用键盘 Enter 加载下一批。
- 未合并 Studio PR #2581，未安装或部署本 LPK。

---

# 2026.08.16.1608

## 动态接入全部 LazyCat MCP Provider

- 按官方 `lazycat-local-resource.skill` 规范扫描 `/lzcapp/run/resources/mcp-providers/<package-id>/<resource-id>/mcp.yml`，从 `package-id + endpoint` 动态生成每个独立 MCP 的 canonical `http://app.<package-id>.lzcx<endpoint>` allowlist。
- 删除 `wtj`、Browser package、`manager` service 与 `8080` 端口特例；单实例和多实例均由 LazyCat 在 ticket 语义下通过 `.lzcx` 选择正确目标实例。
- WebUI 容器只将实际发现的精确 canonical host 动态映射到 `127.0.0.1:80`；ticket lease sidecar 不共享该 hosts 覆盖，继续访问真实 LazyCat gateway，避免 relay 递归。
- relay 仍仅允许 catalog 中精确 host、默认 HTTP 端口和精确 endpoint，拒绝未知 host、错误 endpoint/port、HTTPS、普通 HTTP 转发与 CONNECT，并双层剥离调用方提供的所有 `X-HC-*`。
- MCP 配置继续由用户手动创建、编辑、禁用和删除；不会自动恢复条目，也不执行 Studio MCP CRUD/reload。

---

# 2026.08.16.1516（测试包）

## 修复 LazyCat 安装校验失败

- `2026.08.16.1409` 在目标测试环境安装时被 LazyCat 拒绝，原因为 `hermes-webui` 同时包含 `setup_script` 与自定义 `entrypoint`，平台报错 `cannot define both init and entrypoint/command`；该版本撤回，不应继续安装。
- 保留原有 rootfs 持久化 `setup_script`，删除冲突的 WebUI `entrypoint`。
- 使用 Node 原生 `NODE_OPTIONS=--import=/lzcapp/pkg/content/lazycat-original-url-proxy.mjs` 在原启动进程内加载 scoped loopback relay；原始主机映射并入现有 `setup_script`。relay 仅在 Hermes WebUI 主 Entrypoint 或直接测试时启动，无关 Node 子进程不会重复绑定端口。
- 新增安装结构回归：任何包含 `setup_script` 的服务禁止同时定义 `entrypoint` 或 `command`；完整 Node 测试4/4、Python测试33/33及目标镜像原Entrypoint运行验收通过。

---

# 2026.08.16.1409（撤回：安装失败）

## 原始独立 MCP URL 的透明 Ticket 注入

### 行为边界
- Hermes Studio 不再自动添加、更新、删除或恢复任何 MCP 条目，也不自动调用 MCP reload；所有 MCP 由用户手动配置和管理。
- 本测试包只透明接管已经从目标 LazyCat 实机 manifest 核验的浏览器 MCP 原始多实例 URL：`http://<user>.manager.cloud.lazycat.app.lazycat-agent-browser-skill.lzcapp:8080/mcp`。该 MCP 在 Studio 中仍是独立 Server，不聚合工具或会话。
- Hermes WebUI 容器仅将已核验的浏览器 MCP 原始主机名映射到 `127.0.0.1`，并在原始端口 `8080` 启动专用 loopback relay；不设置全局 `HTTP_PROXY`，不影响 Provider、OAuth 或其他集成流量。relay 必须同时精确匹配单标签用户前缀、Catalog service host suffix、port 和 endpoint，才转换到对应 `app.<package-id>.lzcx<endpoint>`，并通过私有 UDS relay 自动附加当前用户内存 Ticket。
- 未知 Provider、错误 service、port 或 endpoint 全部失败关闭；代理拒绝普通 HTTP 与所有 CONNECT，不具备通用转发或 SSRF 能力。其他 MCP 在没有可信 service/port 元数据前不进入透明接管 allowlist。
- 两层 relay 均剥离调用方提供的全部 `X-HC-*` 身份头，仅由最内层 lease 注入当前内存 Ticket。
- Ticket 继续仅存在当前多实例 sidecar 内存，页面仅执行捕获与五分钟续租；不写入配置、磁盘、Catalog、日志或响应。

### 已执行门禁
- TDD RED→GREEN 覆盖原始多实例URL映射、direct origin-form 请求、严格单标签用户前缀、未知Provider、错误service/port/endpoint拒绝、普通HTTP与CONNECT拒绝、双层 `X-HC-*` 剥离和loopback绑定。
- Node bootstrap测试4/4通过；Python包装层、安全、TOCTOU及透明代理测试31/31通过。
- Preview Nginx、runtime lease、静态安全契约、Node/Shell语法与 `git diff --check` 通过；未修改Hermes Studio运行镜像。
- `lzc-cli project lint` 退出0，保留6条既有策略警告。
- 安装后的真实浏览器原始URL MCP initialize/tools/list仍需在用户安装本测试包后验证。

---

# 2026.08.16.1326（测试包）

## Hermes Studio MCP 自动注册诊断日志

### 修复与可观测性
- 沿用 Hermes Studio 正式 MCP 管理接口认证修复，不直接修改 `config.yaml`。
- 统一受管项所有权判断与生成器的 package ID 字符集，正确识别包含下划线的合法投影，避免旧注册项无法更新或清理。
- 浏览器控制台以固定前缀 `[lazycat-mcp]` 输出分阶段日志：bootstrap加载、认证等待/重试、ticket capture、Provider Catalog、Studio MCP列表、add/update/remove、reload和最终完成。
- 日志仅包含阶段名、计数、HTTP状态、错误类别、重试次数与延迟；不打印Studio token、LazyCat ticket、用户ID、服务URL、Provider完整配置或响应正文。
- ticket续租单独记录成功状态或受限错误类别，便于区分初始化完成后续租失败。

### 已执行门禁
- Node bootstrap单元测试6/6通过，覆盖固定阶段、计数、凭据/配置不泄漏、Studio认证、用户配置保护与下划线package ID回归。
- Python包装层、安全与TOCTOU回归18/18通过。
- LazyCat MCP、preview Nginx与runtime验收通过；`git diff --check`及Node语法检查通过。

---

# 2026.08.16.1313（测试包）

## Hermes Studio MCP 自动注册认证修复

### 版本信息
- **Hermes Studio 运行镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.42-pr2572-pr2573-be14355f-20260816015154`（未修改 Studio 源码或镜像）
- **范围**: 仅 `lazycat-hermes-studio` 包装层

### 修复内容
- 修复 `2026.08.16.1231` 实装后 bootstrap 调用 Hermes Studio MCP 管理 API 未携带 Bearer 认证、导致受管 MCP 数量为 0 的缺陷。
- 自动注册仍使用 Hermes Studio 正式控制面：`/api/hermes/mcp/servers` 与 `/api/hermes/mcp/reload`，由 Studio Agent Bridge 完成添加、删除和重载；不直接修改 `config.yaml`。
- 复用 Studio 当前页面已存在的 `hermes_api_key` 与 `hermes_active_profile_name`，仅对 Studio MCP API附加 `Authorization` 和 `X-Hermes-Profile`；认证信息不转发到票据捕获或Provider Catalog接口。
- 页面认证尚未就绪时最多重试约10秒，不发送未认证的Studio MCP管理请求。
- MCP配置仍只保存固定、无票据的 `http://nginx/lazycat-mcp/...` URL；LazyCat用户票据仅保存在当前多实例sidecar内存租约。

### 已执行门禁
- Node bootstrap 单元测试4/4通过，覆盖Studio认证、Profile Header、凭据不外泄与同名用户配置保护。
- Python包装层、安全与TOCTOU回归18/18通过。
- LazyCat MCP、preview Nginx与真实流式代理运行验收通过。

---

# 2026.08.16.1231（测试包）

## LazyCat MCP 自动发现与短期票据租约

### 版本信息
- **Hermes Studio 运行镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.42-pr2572-pr2573-be14355f-20260816015154`（未修改 Studio 源码或镜像）
- **包装基线**: `2e66584bb9424fb47a42132a0137f8481f46bfcd`
- **范围**: 仅 `lazycat-hermes-studio` 包装层

### 测试目标
- 用户正常打开 Hermes Studio 后，由 LazyCat ingress 在同源 capture 请求上提供 `X-HC-USER-TICKET`；包装层仅在当前多实例容器组内存中保存 15 分钟短期租约。
- 自动读取导入的 `mcp-providers` 投影，为 Hermes Profile 添加无凭据、使用保留名称与固定内部 URL 的 MCP 条目；仅对名称和 URL 均严格匹配的条目执行更新或孤儿清理，不覆盖用户配置。
- Nginx 与租约 sidecar 仅通过当前实例私有 Unix socket 通信；socket 使用目标 Nginx worker 组 `root:101` 与 `0660` 权限，运行目录为 `0750`；后台 MCP 请求只允许生成 Catalog 中的精确 `.lzcx` 目标；无租约、租约过期、用户不一致或上游认证失败时失败关闭。
- 用户票据不写入配置、磁盘、数据库、Catalog、Nginx生成文件、日志或响应。

### 已执行门禁
- Node bootstrap 单元测试 3/3 通过。
- Python包装层、安全与TOCTOU回归 18/18 通过。
- 既有 LazyCat MCP 和 preview Nginx集成契约通过。
- 真实流式代理运行验收通过；现有 Studio镜像可用覆盖 entrypoint启动租约服务并返回健康状态。

---

# 2026.08.08.0132

## 正式发布：全局审批提示音

### 版本信息
- **Hermes Studio**: v0.6.39 + upstream PR #2406
- **源码 HEAD**: `f5535a41dfdefa4f7e6bc3e6b701454a4f49c05d`
- **源码 Tree**: `8b5fedc10324a16d28273ff5547fda1ef361095a`
- **Patch SHA-256**: `35d2b274b850e9007c4b8c819272f54b8a0d10201ac8eb5ffbc867445c006ded`
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.39-pr2406-f5535a41-202608080111`
- **镜像摘要**: `sha256:ed9279ffd97a7d08196ff4e294e8d2a1319220c57c7925add1455d8fdc2088ff`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.08.0132.lpk`

### 发布说明
- 新增与完成提示音独立控制的审批提示音设置。
- Direct Chat、Group Chat 与 Workflow 的新审批请求在相关 Profile 的已连接浏览器中播放一次提示音。
- 当前页面仅抑制重复的全局通知 UI，不抑制提示音；恢复、重复、重渲染、重新进入或已解决请求不重复播放。
- 发送动作会在任一提示音启用时预热共享 Web Audio context，以满足浏览器自动播放策略；两项提示音均关闭时不预热。
- 保留包装仓库当前 LazyCat 预览入口、持久化、多实例隔离、权限及健康检查契约。
- replacement 测试 LPK `2026.08.08.0111` 已完成安装验收；本正式版本从最新包装 `main` 通过 PR 合并后重建。

---

# 2026.08.07.1813（测试包）

## 收敛版本预览为唯一端口前缀入口

### 版本信息
- **Hermes Studio**: v0.6.39（沿用已验证的正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.39-main-202608062012`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.07.1813-test.lpk`

### 版本说明
- 懒猫浏览器实测确认 `https://8651-hermesstudio.<设备域名>/` 能正常加载预览，而同 Origin 的 `/preview/` 因 Vite HTML 使用根绝对 `@vite/client` 与 `src/main.ts` 路径，资源落到正式 `8648` 并返回 HTML，页面会永久停在加载状态。
- 删除不可用的 `/preview/` nginx 路由，只保留端口前缀这一套完整入口；不使用 `sub_filter` 或全局劫持 Vite 根路径。
- 保留 `8651` 的 `Host: localhost:8651`、Docker DNS 上游、其他动态端口及 WebSocket/HMR 行为。

### 变更文件
- `content/nginx.conf`：删除不可用的 `/preview/` 路由
- `tests/check-preview-nginx.py`：禁止 `/preview/` 路由回归
- `package.yml`：测试包版本号 → 2026.08.07.1813
- `CHANGELOG.md`：记录真实浏览器验收结论

---

# 2026.08.07.1749（测试包）

## 修复版本预览 Host 白名单目标

### 版本信息
- **Hermes Studio**: v0.6.39（沿用已验证的正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.39-main-202608062012`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.07.1749-test.lpk`

### 版本说明
- 根据已安装 `2026.08.07.1726` 测试包的懒猫浏览器实测，将 Vite `8651` 请求的上游 Host 从仍被拒绝的 `hermes-webui:8651` 收敛为 Vite 默认信任的 `localhost:8651`。
- `proxy_pass` 网络目标仍为 `hermes-webui:8651`，真实外部地址继续保留在 `X-Forwarded-Host`；正式 `8648` 和其他动态端口行为不变。
- 保留 `/preview/` 的 Vite HMR WebSocket 转发。

### 变更文件
- `content/nginx.conf`：将预览 Host 改写目标改为 `localhost:8651`
- `tests/check-preview-nginx.py`：锁定 localhost Host 契约
- `package.yml`：测试包版本号 → 2026.08.07.1749
- `CHANGELOG.md`：记录测试包范围

---

# 2026.08.07.1726（测试包）

## 修复版本预览的 LazyCat 外部访问

### 版本信息
- **Hermes Studio**: v0.6.39（沿用已验证的正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.39-main-202608062012`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.07.1726.lpk`

### 版本说明
- 仅在 LazyCat nginx 包装层将 `8651` 预览流量的上游 `Host` 改写为内部服务地址，避免 Vite `allowedHosts` 拒绝端口前缀域名。
- 保留真实外部地址于 `X-Forwarded-Host`；正式 `8648` 和其他动态端口继续沿用原 Host。
- 为 `/preview/` 路径补齐 Vite HMR WebSocket 转发。

### 变更文件
- `content/nginx.conf`：预览 Host 改写与 HMR 转发
- `package.yml`：测试包版本号 → 2026.08.07.1726
- `CHANGELOG.md`：记录测试包范围

---

# 2026.08.06.2012

## 正式发布：同步 EKKOLearnAI/hermes-studio main

### 版本信息
- **Hermes Studio**: v0.6.39（基于冻结上游 `main` `405cde9f6090e69104d0b365d9fef60d571ef9b6`）
- **源码树**: `7accd0874f1d71d8c68d8e8d3dd06142f4a16a05`
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.39-main-202608062012`
- **镜像摘要**: `sha256:2137ab4a96c74701ff27dbe0b62abe5e27c4221b8f58918e324c1ee5d3c71198`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.06.2012.lpk`

### 说明
- 严格使用执行时冻结的 `EKKOLearnAI/hermes-studio:main`。
- 不包含 Draft PR #2391 或其他未合并改动。
- 保持现有 LazyCat 多实例隔离、持久化和健康检查配置不变。

---

## v2026.08.05.1531（测试包）

### 版本信息
- **Hermes Studio**: v0.6.38（沿用正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.38-main-202608042316`
- **镜像摘要**: `sha256:1776fec94204ca85bf7177b785ab8232bc94624b328e10226df1447812957865`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.05.1531.lpk`

### 版本说明
- nginx Docker DNS resolver 增加 `ipv6=off`，避免解析到仅分配但未监听的 Hermes Web UI IPv6 upstream。
- 仅包含上述 resolver 调整；Runtime 镜像、healthcheck、应用权限、挂载、持久化及多实例配置均保持不变。

### 变更文件
- package.yml：测试包版本号 → 2026.08.05.1531
- content/nginx.conf：`resolver 127.0.0.11 valid=30s ipv6=off;`
- CHANGELOG.md：记录测试包范围

---

## v2026.08.05.1033（测试包）

### 版本信息
- **Hermes Studio**: v0.6.38（沿用正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.38-main-202608042316`
- **镜像摘要**: `sha256:1776fec94204ca85bf7177b785ab8232bc94624b328e10226df1447812957865`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.05.1033.lpk`

### 版本说明
- 包装层 healthcheck 改用显式 loopback 地址与 `/health` 路径。
- 容器 healthcheck 调整为 `interval: 15s`、`timeout: 10s`、`retries: 5`，在覆盖当前约 2.1–2.9 秒实测延迟的同时保留故障感知能力。
- 平台级 healthcheck timeout 同步调整为 `10s`。
- Runtime 镜像和应用权限、挂载、持久化及多实例配置均保持不变。
- 本测试包仅用于验证包装层止血效果，不代表已修复 Hermes Studio 上游性能热点。

### 变更文件
- package.yml：测试包版本号 → 2026.08.05.1033
- lzc-manifest.yml：调整平台级与容器级 healthcheck 容错参数
- CHANGELOG.md：记录测试包范围和验证边界

---

## v2026.08.04.2316

### 版本信息
- **Hermes Studio**: v0.6.38（基于冻结上游 `main` `5092cb2b2a143d3bc49c32be6b429df4b77faf57`）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.38-main-202608042316`
- **镜像摘要**: `sha256:1776fec94204ca85bf7177b785ab8232bc94624b328e10226df1447812957865`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.2316.lpk`

### 版本说明
- 包含群聊运行卡片隐藏 Agent 描述信息的改进（#2352）。
- 包含 Runtime 激活失败提示及 Web UI 切换收敛（#2353）。
- Coding Agent prompt 改为通过 stdin 传递（#2354）。
- 移除 Group Chat 对 Codex、Claude Code、Ekko 的固定 120 秒整轮 deadline，由各 Coding Agent runtime 负责运行时控制；显式 Stop/Room interrupt 仍保留（#2357）。
- 保留包装主线已更新的 `HERMES_WRITE_SAFE_ROOT=/tmp:/opt/data:/home/agent/.hermes/workspace/`。

### 变更文件
- package.yml：版本号 → 2026.08.04.2316
- lzc-manifest.yml：Hermes Studio 运行镜像 → `v0.6.38-main-202608042316`

---

## v2026.07.20.0050

### 版本信息
- **Hermes Studio**: v0.6.31（沿用已验证的正式运行镜像）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.31-carry1-202607191930`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.20.0050.lpk`

### 版本说明
- 为 Hermes 文件写入安全策略显式配置 `/opt/data` 与 `/home/agent/.hermes/workspace/` 两个允许根目录。
- 两个根目录通过 Linux 路径分隔符 `:` 写入 `HERMES_WRITE_SAFE_ROOT`。

### 变更文件
- package.yml：测试包版本号 → 2026.07.20.0050
- lzc-manifest.yml：新增 `HERMES_WRITE_SAFE_ROOT=/opt/data:/home/agent/.hermes/workspace/`

---

## v2026.07.19.1930

### 版本信息
- **Hermes Studio**: v0.6.31（冻结上游发布基线并叠加 1 个已验证 Carry）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.31-carry1-202607191930`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.19.1930.lpk`

### 版本说明
- 本次组合镜像包含已通过质量门的 workflow bridge readiness 修复。
- 运行镜像使用本次唯一 tag，并已回读 linux/amd64 manifest 与 config digest。

### 变更文件
- package.yml：版本号 → 2026.07.19.1930
- lzc-manifest.yml：镜像 → `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.31-carry1-202607191930`

---

## v2026.07.19.0958

### 版本信息
- **Hermes Studio**: v0.6.31（冻结集成源码）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.31-carry1-202607190958`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.19.0958.lpk`

### 版本说明
- 基于冻结集成源码构建，包含 workflow bridge handoff readiness 修复。
- 已完成 TypeScript 检查、相关 Vitest 测试与生产构建；运行镜像为本次唯一 linux/amd64 tag，并已回读 manifest。

### 变更文件
- package.yml：版本号 → 2026.07.19.0958
- lzc-manifest.yml：镜像 → `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.31-carry1-202607190958`

---

## v2026.07.19.0311

### 版本信息
- **Hermes Studio**: v0.6.30（冻结上游 main 构建）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry0-202607190311`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.19.0311.lpk`

### 版本说明
- 本次无 Carry；基于冻结源码完成隔离质量门、镜像构建与 LPK 验证。
- 运行镜像使用本次唯一 tag，并已回读 linux/amd64 manifest 与 config digest。

### 变更文件
- package.yml：版本号 → 2026.07.19.0311
- lzc-manifest.yml：镜像 → `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry0-202607190311`

---

## v2026.07.18.0355

### 版本信息
- **Hermes Studio**: v0.6.30（构建基线按冻结输入与 Carry 契约确定）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry1-202607180355`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.18.0355.lpk`

### 版本说明
- 发布输入通过 REST/GraphQL 双投影冻结；源码组合、隔离 Node 24 质量门、镜像与 LPK 均按不可变证据回读。
- 本次 Carry：
  - `wtj-0527/hermes-studio#13` @ `9a3227523a6c5bf13559c5895a0db6b9dab5f68e`

### 变更文件
- package.yml：版本号 → 2026.07.18.0355
- lzc-manifest.yml：镜像 → `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry1-202607180355`

---

## v2026.07.16.1946

### 版本信息
- **Hermes Studio**: v0.6.30（基于上游正式发布）
- **镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry3-202607161946`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.07.16.1946.lpk`

### 版本说明
- 基于上游 v0.6.30，叠加冻结的开放 carry PR：
  - PR #1924
  - PR #2011
  - PR #2082
- 已在隔离 Node 24 环境完成依赖安装、carry 声明测试、harness、全量覆盖率与生产构建；LPK 内嵌镜像引用为本次唯一 tag。

### 变更文件
- package.yml：版本号 → 2026.07.16.1946
- lzc-manifest.yml：镜像 tag → `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.30-carry3-202607161946`

---

## v2026.07.11.0823

### 版本信息
- **Hermes Studio**: v0.6.28（基于上游 EKKOLearnAI/hermes-studio v0.6.28）
- **镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.28-carry3-202607110823
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.11.0823.lpk

### 版本说明
- 基于上游官方 v0.6.28 源码构建，叠加我们 fork 中仍需携带的 3 个未合并 PR 修复后，重新组合构建并推送至阿里云容器镜像服务唯一组合 tag；经 `docker manifest inspect` 回读验证，镜像 config digest 为 `sha256:1aaa9d47ee4dfac3e0247bb6e7ab16ab254b46c49083b92ac816b23281eef2c8`，等效证明 3 个未合并修复真实落地（完整 TypeScript/Vite 构建通过，修复代码全部编译进镜像）。
- 本次 carry 集合与上一版一致，共 3 个未合并 PR 的真实修复文件（已剔除各分支自带的污染提交）：
  - PR #2023：workflow 节点 toolset/capability 策略强制收敛（enforce exact node capability policies），避免节点能力面被回宽
  - PR #2011：抑制 workspace diff 中的零行变更（zero-line diffs），避免 +0/-0 噪音卡片
  - PR #1924：文件面板跟随 session workspace（规范化 session workspace 文件路径，非侵入式方案）
- 相对上一版 v2026.07.10.2357：PR #2023 在当前发布时刻新增 1 个收敛提交（preserve policy during final context refresh），故采用全新唯一组合 tag `v0.6.28-carry3-202607110823`（时间取自本次实际发布时间 2026.07.11.0823）。

### 变更文件
- package.yml：版本号 → 2026.07.11.0823
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.28-carry3-202607110823

---

## v2026.07.10.2357

### 版本信息
- **Hermes Studio**: v0.6.28（基于上游 EKKOLearnAI/hermes-studio v0.6.28）
- **镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.28-carry3-202607102357
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.10.2357.lpk

### 版本说明
- 基于上游官方 v0.6.28 源码构建，叠加我们 fork 中仍需携带的 3 个未合并 PR 修复后，重新组合构建并推送至阿里云 ACR 唯一组合 tag；经 manifest 回读验证，镜像 config digest 为 sha256:c368e1c849690c99637f3cc25f868919bf6e24549479f55bdb340a6acafc458f，等效证明 3 个未合并修复真实落地（完整构建通过，修复代码全部编译进镜像）。
- 本次 carry 集合由上一版 2 个扩展为 3 个（新增 #2023）；仅叠加未合并 PR 的真实修复文件、剔除污染提交：
  - PR #2023：workflow 节点 toolset/capability 策略强制收敛（enforce exact node capability policies），避免节点能力面被回宽
  - PR #2011：抑制 workspace diff 中的零行变更（zero-line diffs），避免 +0/-0 噪音卡片
  - PR #1924：文件面板跟随 session workspace（规范化 session workspace 文件路径，非侵入式方案）
- 移除说明：#2003（隐藏 SQLite sidecar）、#1918（定时任务 model 选择）、#1903（导出 coding agent session）已并入上游 v0.6.28，故从 carry 集合移除。

> 注：按唯一组合 tag 规则，未合并 carry PR 非空时不得使用官方 v0.6.28、不得复用/覆盖旧组合 tag，故本次采用全新唯一组合 tag v0.6.28-carry3-202607102357（时间取自本次实际发布时间 2026.07.10.2357）。

### 变更文件
- package.yml：版本号 → 2026.07.10.2357
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.28-carry3-202607102357

---

## v2026.07.10.1343

### 版本信息
- **Hermes Studio**: v0.6.28（基于上游 EKKOLearnAI/hermes-studio v0.6.28）
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.28-carry2-202607101256
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.10.1343.lpk

### 版本说明
- 基于上游官方 v0.6.28 源码构建，叠加我们 fork 中仍需携带的 2 个未合并 PR 修复后，重新组合构建并推送至阿里云 ACR 唯一组合 tag；经 `docker manifest inspect` 回读验证，镜像 config digest 为 `sha256:a3bc61a2e451a2cc826464f1347793194563f3238ecfaf5b524f9e685d7efa31`，等效证明 2 个未合并修复真实落地（完整 TypeScript/Vite 构建通过，修复代码全部编译进镜像）。
- 本次仅叠加 2 个仍未合并的 carry 修复（已从上游分支 cherry-pick 真实修复文件、剔除污染提交——#2011 分支自带的 ESP32 firmware.bin/main.cpp 与 MCU speech segmenter 改动、#1924 分支自带的版本号回退与 jobs.ts/model&provider 删除均未带入）：
  - PR #2011：抑制 workspace diff 中的零行变更（zero-line diffs），避免 +0/-0 噪音卡片
  - PR #1924：文件面板跟随 session workspace（规范化 session workspace 文件路径，非侵入式方案）
- 移除说明：#2003（隐藏 SQLite sidecar）、#1918（定时任务 model 选择）、#1903（导出 coding agent session）已并入上游 v0.6.28，故从 carry 集合移除，计数由上一版 4 降为 2。

> 注：按唯一组合 tag 规则，未合并 carry PR 非空时不得使用官方 `v0.6.28`、不得复用/覆盖旧组合 tag，故本次采用全新唯一组合 tag `v0.6.28-carry2-202607101256`（时间取自本次实际发布时间 2026.07.10.1343）。

### 变更文件
- package.yml：版本号 → 2026.07.10.1343
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.28-carry2-202607101256
- Dockerfile：基于官方上游 EKKOLearnAI/hermes-studio v0.6.28 源码（对应上游 Web UI 镜像 ekkoye8888/hermes-web-ui:v0.6.28）+ 仅叠加 2 个未合并 PR 的真实修复组合构建；构建基础镜像为 nousresearch/hermes-agent:latest（仅作为运行底座，并非 Web UI 镜像 tag 证据）

---

## v2026.07.09.1152

### 版本信息
- **Hermes Studio**: v0.6.27（基于上游 EKKOLearnAI/hermes-studio v0.6.27）
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.27-carry4-202607091149
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.09.1152.lpk

### 版本说明
- 基于上游官方 v0.6.27 源码构建，叠加我们 fork 中仍需携带的 4 个未合并 PR 修复后，重新组合构建并推送至阿里云 ACR 唯一组合 tag；经 `docker manifest inspect` 回读验证，镜像 config digest 为 `sha256:d5cf1a93cbe25701290d0c4f785e55850033dfc691ef62df862bc841ecacabf4`，等效证明 4 个未合并修复真实落地（完整 TypeScript/Vite 构建通过，修复代码全部编译进镜像）。
- 包含仍需携带的兼容性修复/补丁（4 个上游未合并 PR，已叠加进源码并经代码标记验证）：
  - PR #2003：隐藏 workspace diff 中的 SQLite sidecar 文件
  - PR #1924：文件面板跟随 session workspace（非侵入式方案）
  - PR #1918：定时任务支持选择 model
  - PR #1903：导出已完成的 coding agent session
- 注：#1995（workflow coding agent abort 路由）与 #1983（scoped coding agent 继承外部 MCP）已并入上游 v0.6.27，故从 carry 集合移除，计数由 5 降为 4。

> 注：按唯一组合 tag 规则，未合并 carry PR 非空时不得使用官方 `v0.6.27`、不得复用/覆盖旧组合 tag，故本次采用全新唯一组合 tag `v0.6.27-carry4-202607091149`（时间取自本次实际发布时间 2026.07.09.1152）。

### 变更文件
- package.yml：版本号 → 2026.07.09.1152
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.27-carry4-202607091149
- Dockerfile：基于官方上游 EKKOLearnAI/hermes-studio v0.6.27 源码（对应上游 Web UI 镜像 ekkoye8888/hermes-web-ui:v0.6.27）+ 叠加 4 个未合并 PR 组合构建；构建基础镜像为 nousresearch/hermes-agent:latest（仅作为运行底座，并非 Web UI 镜像 tag 证据）

---

## v2026.07.08.2246

### 版本信息
- **Hermes Studio**: v0.6.27（基于上游 EKKOLearnAI/hermes-studio v0.6.27）
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.27-carry5-202607082246
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.08.2246.lpk

### 版本说明
- 基于上游官方 v0.6.27 源码构建，叠加我们 fork 中仍需携带的 5 个未合并 PR 修复后，重新组合构建并推送至阿里云 ACR 唯一组合 tag；经 `docker manifest inspect` 回读验证，镜像 config digest 与上一步已验证组合镜像一致（`sha256:2529c41aa89c…`），等效证明 5 个未合并修复真实落地。
- 包含仍需携带的兼容性修复/补丁（5 个上游未合并 PR，已叠加进源码并经代码标记验证）：
  - PR #1995：workflow coding agent 中止（abort）正确路由
  - PR #1983：scoped coding agent 继承外部 MCP
  - PR #1924：文件面板跟随 session workspace（非侵入式方案）
  - PR #1918：定时任务支持选择 model
  - PR #1903：导出已完成的 coding agent session

> 注：本版本替换今日旧时间戳版本 v2026.07.08.0958。按唯一组合 tag 规则，未合并 carry PR 非空时不得使用官方 `v0.6.27`、不得复用/覆盖旧组合 tag `v0.6.27-carry5-202607082021`，故本次采用全新唯一组合 tag `v0.6.27-carry5-202607082246`（时间取自本次实际发布时间）。

### 变更文件
- package.yml：版本号 → 2026.07.08.2246
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.27-carry5-202607082246
- Dockerfile：基于官方上游 EKKOLearnAI/hermes-studio v0.6.27 源码（对应上游 Web UI 镜像 ekkoye8888/hermes-web-ui:v0.6.27）+ 叠加 5 个未合并 PR 组合构建；构建基础镜像为 nousresearch/hermes-agent:latest（仅作为运行底座，并非 Web UI 镜像 tag 证据）

---

## v2026.07.08.0958

### 版本信息
- **Hermes Studio**: v0.6.27（基于上游 EKKOLearnAI/hermes-studio v0.6.27）
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.27-carry5-202607082021
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.08.0958.lpk

### 版本说明
- 基于上游官方 v0.6.27 源码构建
- 包含仍需携带的兼容性修复/补丁（5 个未合并 PR，已叠加进源码并经代码标记验证）：
  - PR #1995：workflow coding agent 中止（abort）正确路由
  - PR #1983：scoped coding agent 继承外部 MCP
  - PR #1924：文件面板跟随 session workspace（非侵入式方案）
  - PR #1918：定时任务支持选择 model
  - PR #1903：导出已完成的 coding agent session

> 注：此前已发布测试镜像 v0.6.27 仅叠加其中 4 个 PR（缺 #1995）；本次改用唯一组合 tag `v0.6.27-carry5-202607082021`，不再覆盖官方 `v0.6.27`，并纳入全部 5 个未合并修复。

### 变更文件
- package.yml：版本号 → 2026.07.08.0958
- lzc-manifest.yml：镜像 tag → wtjking/hermes-web-ui:v0.6.27-carry5-202607082021
- Dockerfile：基于官方上游 EKKOLearnAI/hermes-studio v0.6.27 源码（对应上游 Web UI 镜像 ekkoye8888/hermes-web-ui:v0.6.27）+ 叠加 5 个未合并 PR 组合构建；构建基础镜像为 nousresearch/hermes-agent:latest（仅作为运行底座，并非 Web UI 镜像 tag 证据）

---

## v2026.07.07

- **多实例隔离**：rootfs cache 从 compose_override 全局挂载改为 binds per-instance appvar（/lzcapp/var/cache），消除多实例共享 cache 冲突
- 清理 compose_override 中冗余的 rootfs 缓存挂载

## v2026.07.06

### 版本信息
- **Hermes Studio**: v0.6.26（基于上游 EKKOLearnAI/hermes-studio v0.6.26）
- **Hermes CLI**: v0.18.0 (2026.7.1)，支持 journey 命令
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:2026.07.06
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.06.lpk

### 上游合并
- 🔄 基于上游 v0.6.26 官方发布版
- 🆕 新增 Ekko Agent runtime（本地 agent 运行时）
- 🆕 新增 group chat baseline/approval/streaming 测试
- 🛠️ ChatInput 高度设置、Codex 上下文稳定性改进

### LPK 增强
- 🚀 启动优化：指纹改为 package.yml+manifest.yml，正常重启跳过 cp（~30秒 → 瞬间）
- 🔧 rootfs 缓存绑定到高速 NVMe 缓存盘，首次安装快照时间从 50+ 分钟降到 ~30 秒
- 🔧 setup_script `set -e` 安全修复：`for` 循环补 `done`，`&&` 链改为 `if/fi`
- 🔗 setup_script 自动维护 `/etc/hosts` 和 SSH config 软链接
- 📊 `cp -a /usr` 进度条显示（百分比 + 进度条 + 已拷贝/总量）
- 🌐 环境变量 LANG=C.UTF-8（移除无效 localedef）
- 🔑 多密钥 SSH 免密体系（不同服务使用独立 ED25519 密钥）

### 保留修复
- 🧩 包含上游未合并 PR：
  - PR #1903：coding agent session 导出
  - PR #1918：定时任务 model 选择修复
  - PR #1924：文件面板 session workspace 支持

### 变更文件
- Fork: KingBoyAndGirl/hermes-studio main（merge upstream v0.6.26）
- Dockerfile：BASE_IMAGE=nousresearch/hermes-agent:latest
- lzc-build.yml：compose_override volumes 绑定 NVMe 缓存
- setup_script：进度条、locale、hosts/SSH 自动化
- lzc-manifest.yml：binds 合规路径 + 镜像 tag → wtjking/hermes-web-ui:2026.07.06
- package.yml：版本号 → 2026.07.06

## v2026.07.05

### 版本信息
- **Hermes Studio**: v0.6.25（基于上游 EKKOLearnAI/hermes-studio v0.6.25）
- **Hermes CLI**: v0.18.0 (2026.7.1)，支持 journey 命令
- **Docker 镜像**: registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:2026.07.05
- **LPK 包**: community.lazycat.app.hermes-studio-v2026.07.05.lpk

### 核心修复
- 🔼 **Hermes CLI 升级**：基础镜像 nousresearch/hermes-agent:latest 自动解析至 v0.18.0，新增 journey 子命令支持，修复学习轨迹 API 500 错误
- 🧩 **包含上游未合并 PR**：
  - PR #1903：coding agent session 导出
  - PR #1918：定时任务 model 选择修复  
  - PR #1924：文件面板 session workspace 支持

### 变更文件
- Dockerfile：BASE_IMAGE 重新拉取（Hermes v0.17.0 → v0.18.0）
- lzc-manifest.yml：binds 合规路径 + 镜像 tag → wtjking/hermes-web-ui:2026.07.05
- package.yml：版本号 → 2026.07.05

### 构建信息
- 源码：KingBoyAndGirl/hermes-studio main 分支（HEAD: 21ec9e87）
- 构建时间：2026-07-05 12:42 UTC

## v2026.07.04

### 变更
- 测试包：Hermes Web UI 镜像切到 `v0.6.25-pr1903-1918-1921-20260704`
- 测试镜像 = 官方 `v0.6.25` base + PR #1903 / #1918 / #1921 源码组合构建的头部分
- PR #1918 新增：定时任务编辑时 provider/model 持久化修复 + 卡片显示 provider/与中文模型标签
- 构建时间：2026-07-04 03:12:19
- 仅用于安装验证，不代表上游正式发布版本

---

## v2026.07.04

### 变更
- 测试包：Hermes Web UI 镜像切到 `v0.6.25-pr1903-1918-1921-20260703`
- 该测试镜像包含上游未合并 PR #1903 / #1918 / #1921 的组合构建
- 仅用于安装验证，不代表上游正式发布版本

---

## v2026.07.03

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.25`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.25`
- 同步 `package.yml` 包版本到 `2026.07.03`
- 显式设置 `WORKSPACE_BASE=/home/agent`，让工作区目录选择器可在安全边界内选择 `.hermes`、`.config`、`.codex` 等目录

---

## v2026.07.01

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.23`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.23`
- 同步 `package.yml` 包版本到 `2026.07.01`

---

## v2026.06.29

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.22`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.22`
- 同步 `package.yml` 包版本到 `2026.06.29`

---

## v2026.06.25

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.21`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.21`

---

## v2026.06.24

### 变更
- 在 `setup_script` 中补写 `/home/agent/.profile` 与 `/home/agent/.bash_profile` 的 PATH 导出
- 让登录 shell 快照稳定包含 `/home/agent/.local/bin`，避免 `lzc-cli` 等用户级 CLI 在部分终端上下文中丢失

---

## v2026.06.23

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.19`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.19`

---

## v2026.06.22

### 变更
- 延长平台级与 `hermes-webui` 容器级健康检查宽限期到 600 秒，避免首次启动 / overlay snapshot / bootstrap 阶段被过早判失败

---

# Hermes Studio 懒猫微服版 更新日志

## v2026.06.21

### 变更
- Hermes Web UI 镜像升级到官方 `v0.6.18`
- LazyCat 入口镜像改为 `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:v0.6.18`
- 移除上传文件大小限制（nginx + hermes-webui）
- nginx: `client_max_body_size 0`（无限制）
- hermes-webui: `MAX_UPLOAD_SIZE` 默认 0（无限制），可通过环境变量 `MAX_UPLOAD_SIZE` 覆盖

---

## v2026.06.20

### 子域名端口路由
- Nginx 动态端口前缀路由：`9090-hermesstudio → hermes-webui:9090`
- WebSocket 代理支持
- `/preview/*` → hermes-webui:8651
- `/xai-oauth/*` → hermes-webui:56121

### 平台级健康检查
- `application.health_check.test_url: http://hermes-webui:8648`
- 消除启动 502 错误

### document.private + 应用文稿
- `/home/agent` 在懒猫文件管理器"应用文稿"中可见

### 核心
- 全 rootfs 持久化（base+upper overlay 分离）
- 镜像切换到阿里云 ACR
- AGPL-3.0 许可证

---

## v2026.06.19

### 首次正式发布
- Hermes Agent Web UI 部署到懒猫微服
- 全家目录持久化 (`/lzcapp/var/home:/home/agent`)
- rootfs overlay 持久化（base+upper 分离）
- document.private 支持
- AGPL-3.0 许可证
