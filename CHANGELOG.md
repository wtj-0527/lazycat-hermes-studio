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
