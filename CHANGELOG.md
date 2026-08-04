## v2026.08.04.2031

### 版本信息
- **Hermes Studio upstream base**: `67e2cbf9b6e00400dcc8418fd3e2ec5b00154fb1`（v0.6.38 线）
- **Hermes Studio Source**: `eefbe130a2e90a94c0b71cd6027af69c1fe6268a`
- **Studio tree**: `6172fdebff8aca96f15310e5dcda4fde87450c1f`
- **Studio candidate diff**: `2a84515bd556165e7bd741ce5ab5550c2dafc31a4b2cc49e50050dab39d80489`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608042031-eefbe130`
- **Browser Runtime API**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-api:202608041511-e5eaefd6`
- **Browser Runtime UI**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-ui:202608041511`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.2031.lpk`

### 版本说明
- 修复 BrowserPanel 使用 `object-fit: contain` 时未扣除上下或左右留白造成的人控坐标错位；画面留白不再转发点击，拖动进入留白后仍会在最后有效位置释放鼠标。
- live-view 预览降至最多 1280×720、JPEG quality 70，并依据 CDP screencast metadata 将输入映射回完整远端 viewport，兼顾低带宽和精确点击。
- 高频 `mousemove` 现在每个 animation frame 只转发最新位置；JPEG 解码只保留最新待绘制帧，不再追赶已过期帧。
- 基于执行时最新 upstream `main` 重放现有 Browser commits；Browser 聚焦测试、双端 TypeScript、production build、Harness、镜像 push/pull-back 与 LPK 深验作为交付门禁。
- 测试包不合并、不创建正式 Git tag/GitHub Release，也不代安装；由用户安装后继续验收百度登录入口坐标、验证码交互和人控延迟。

### 变更文件
- `CHANGELOG.md`
- `lzc-manifest.yml`
- `package.yml`

---

## v2026.08.04.1741

### 版本信息
- **Hermes Studio upstream base**: `1a78e89574440404e2f7e21bca69aac142df2197`（v0.6.38 线）
- **Hermes Studio Source**: `64059e4c42bbbaf1e57444fa2517769c0f3e56e1`
- **Studio tree**: `2aee7bc6f279991950cda1bff58b2e4118da2383`
- **Studio candidate diff**: `7dcb6adeaa35cd0a9480b81b3667c2054f3ad5d152cebea4d399b338c551f0e6`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608041741-64059e4c`
- **Browser Runtime API**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-api:202608041511-e5eaefd6`
- **Browser Runtime UI**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-ui:202608041511`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.1741.lpk`

### 版本说明
- 修复 BrowserPanel 冷启动在 Runtime Session 尚未建立时反复 `POST /api/browser/viewport` 返回 409；无 Session 的 viewport 同步现在为幂等空状态，且不会隐式占用 Runtime。
- 修复 LazyCat TLS 反向代理后的 live-view WebSocket 同源校验；仅在包装层显式信任代理时读取单值 forwarded host/proto，默认上游行为仍 fail closed。
- 畸形或缺失 WebSocket `Host` 现在仅销毁当前 upgrade socket，不消费一次性 capability，也不会让 URL 解析异常逃出并终止 Studio 服务。
- 为一次性 Browser view capability 增加独立 nginx WebSocket location：Studio upstream 只使用 IPv4 解析并禁用普通 upstream retry；隔离 reverse-proxy gate 已验证 HTTP 101、仅一次 upgrade 和 forwarded headers 回读。
- 修复 Browser iframe 边界上的 Panel resize 粘住：resize handle 使用 Pointer Capture，并在 pointerup、pointercancel、lostpointercapture、window blur 和 unmount 时幂等清理。
- 补齐 EDNS OPT literal-root、reserved flags 和完整 option TLV 校验。
- 基于执行时最新 upstream `main` 重放原 Browser commits，10/10 patch-id 一致；Browser 聚焦测试、双端 TypeScript、production build、Harness、nginx config、LPK lint 均通过。
- 测试包不合并、不创建正式 Git tag/GitHub Release，也不代安装；由用户安装后继续验收 BrowserPanel 首帧、接管、同页交互和 exact release。

### 变更文件
- `CHANGELOG.md`
- `lzc-manifest.yml`
- `package.yml`

---

## v2026.08.04.1511

### 版本信息
- **Hermes Studio Source**: `04623c86670f90013b89305d8fee1a6f2a7f7960`
- **Studio tree**: `8a4ef8fb9ef73cad23612c11cf5d4b57faaf39b0`
- **Studio candidate diff**: `acafbfb8330d572accb62d658fe7b7529595a5290af13897ba797784ed25ca59`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608041511-04623c86`
- **Browser Runtime upstream base**: `5880b48c1af107219ff3d904edbb8f6b76bea9b6`
- **Browser Runtime carry**: `e5eaefd6437dcef0b049e44992f811eb0f4e380a`
- **Runtime tree**: `fe3df8b47ebd31568ad9c1f2cc81c88298db06c9`
- **Runtime candidate diff**: `cb1fb5c4fe73f7e13c6071e80f6e69ff2b0de8b423bb8313648a43a69c265276`
- **Browser Runtime API**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-api:202608041511-e5eaefd6`
- **Browser Runtime UI**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-browser-runtime-ui:202608041511`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.1511.lpk`

### 版本说明
- 修复 LazyCat Fake-IP DNS 环境下 Browser egress 无法访问公网的问题：仅在系统 DNS 返回明确 benchmark Fake-IP 且没有其他禁止地址时，使用默认关闭、显式配置的 RFC 8484 DoH fallback；解析器固定连接已验证公网 bootstrap IP，同时保留 resolver Host/SNI/CA 校验，并对全部返回地址重新执行 SSRF policy。
- Fake-IP、loopback、RFC1918、link-local、metadata、reserved、transition、rebinding 和 mixed-private 答案仍 fail closed；socket 只连接经过批准的确切公网 IP，不直接放行 `198.18.0.0/15`。
- 修复 Browser Runtime exact release 与异步 target setup 的竞态：停止接收新任务、推进 generation、有限排空 target setup 后再关闭 Browser；仅抑制 intentional shutdown 已取消任务产生的 Target/Session closed 错误，其他错误继续上报。
- 隔离 A/B canary 以相同的 20 次 Session/CDP/12-page/exact-release 负载验证：未修版出现 3115 条 Target-close 日志，新 exact 候选 20/20 健康且日志匹配为 0；Runtime full API 测试 83 passed / 2 skipped，build 通过。
- Hermes Studio Browser 聚焦测试 187/187、Server TypeScript、production build、Harness 均通过；DNS parser 边界回归 78/78 通过，生产 `dist` 从锁定 commit 独立重建并冻结 434 文件 SHA-256 map。
- 测试包使用唯一 ACR Studio/Runtime API/Runtime UI tag；不依赖 floating `latest`。保留 `HERMES_WRITE_SAFE_ROOT=/tmp:/opt/data:/home/agent/.hermes/workspace/`，并保持 `content/nginx.conf` 字节不变。
- 这是待用户安装验收的测试候选；尚未合并、创建正式 Git tag、GitHub Release 或正式发布。上游后续漂移不改变本候选字节，验收通过后再同步当时最新 upstream `main`。
- 已知依赖风险未因功能测试而消除：Runtime `npm audit --omit=dev` 在本次锁定依赖上报告 1 critical、19 high、4 moderate、2 low；需在正式发布决策前单独处置或接受风险。

### 变更文件
- `CHANGELOG.md`
- `lzc-manifest.yml`
- `package.yml`

---

## v2026.08.04.0959

### 版本信息
- **Hermes Studio Source**: `8e9dd75b56e007277e5580e59524be55c40240d2`
- **Studio tree**: `a88fb4e13ddf54e429c8975891d5e822a3f6062d`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608040959-8e9dd75b`
- **Browser Runtime API**: `ghcr.io/steel-dev/steel-browser-api:latest`
- **Browser Runtime UI**: `ghcr.io/steel-dev/steel-browser-ui:latest`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.0959.lpk`

### 版本说明
- 修复 Browser egress `CONNECT` tunnel 在客户端或上游断开时的生命周期收敛，避免 `write EPIPE` / `ECONNRESET` 冒泡至进程级 `uncaughtException` 并终止 Studio。
- 在异步目标 DNS 解析开始前安装客户端 `error` / `close` guard，并在建立 upstream 后无监听空窗地交接给双向 tunnel guard。
- 任一端 `error`、`close` 或已销毁状态都会幂等地停止双向 pipe 并销毁两端；正常 CONNECT 200、head 转发和双向数据流保持不变。
- Source PR exact-head 的 Build、Playwright、Website、NPM Lockfile 与 Socket Security 检查全部成功；Browser 聚焦测试 129/129、生产构建、Server typecheck 与 Harness 均通过，exact baseline 无 candidate-only failure。
- 保留 Packaging PR #64 最新提交中的 `HERMES_WRITE_SAFE_ROOT=/tmp:/opt/data:/home/agent/.hermes/workspace/`，并保持既有 nginx 路由配置字节不变。

### 变更文件
- `CHANGELOG.md`
- `lzc-manifest.yml`
- `package.yml`

---

## v2026.08.04.0701

### 版本信息
- **Hermes Studio Source**: `4e3442008492809ea17dad8df7e0c2a668cbf3d9`
- **Studio tree**: `2bb6d0ff0e6ceb84cfaf68934d0a2901bcbe0784`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608040701-4e344200`
- **Browser Runtime API**: `ghcr.io/steel-dev/steel-browser-api:latest`
- **Browser Runtime UI**: `ghcr.io/steel-dev/steel-browser-ui:latest`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.0701.lpk`

### 版本说明
- 修复 Browser Runtime 页面状态读取永久挂起时 `tabs.list` 无法收敛的问题；超时后释放 single-flight，并使用 owner-scoped 最近验证状态继续响应。
- 修复 Agent 控制、用户接管、页面消失与 deactivation 的生命周期竞态；先撤销 view/control generation，再取消 Runtime 操作、排空 page queue，最后执行 exact Runtime release。
- Runtime 返回页面消失时支持窄范围幂等收敛；其他取消或 release 错误继续 fail-closed，不重新开放 viewer input 或 Agent 控制。
- 增加 `steel-hermesstudio.*` 诊断域名分流，并将诊断响应中的 Runtime HTTP/CDP 地址改写为同源 HTTPS/WSS；诊断 UI 不参与 Studio 健康依赖。
- 保持原数字端口域名规则不变：`<数字>-hermesstudio.*` 继续转发至 `hermes-webui:<数字端口>`。
- exact baseline 全量 Vitest 对账无 candidate-only failure；Browser 聚焦测试 177/177、生命周期测试 43/43、生产构建、Client/Server typecheck 和 Harness 均通过。

### 变更文件
- `CHANGELOG.md`
- `content/nginx.conf`
- `lzc-manifest.yml`
- `package.yml`

---

## v2026.08.04.0055

### 版本信息
- **Hermes Studio Source**: `4dd54e3b1b1ef9c9ca7576b1e5eb4125c7c9e16d`
- **Studio tree**: `ca6db4256f6086f01eaa042db520b0a110238ec3`
- **Studio 镜像**: `registry.cn-shanghai.aliyuncs.com/wtjking/hermes-web-ui:browser-runtime-202608040008-4dd54e3b`
- **Browser Runtime API**: `ghcr.io/steel-dev/steel-browser-api:latest`
- **Browser Runtime UI**: `ghcr.io/steel-dev/steel-browser-ui:latest`
- **LPK 包**: `community.lazycat.app.hermes-studio-v2026.08.04.0055.lpk`

### 版本说明
- 增加 Hermes Studio 内置统一 Browser 工作区；BrowserPanel、Agent 控制、用户接管和 live view 均由 Studio 提供。
- 部署私网 Browser Runtime API；Studio 通过通用 Session API/CDP 接入，API 不配置外部 route。
- 保留私网 Runtime UI 作为诊断控制台；它不是 BrowserPanel、不参与产品链路，也不作为 Studio 健康依赖。
- 修复首次安装时 nginx 与 `hermes-webui` 并发启动导致上游服务名尚未注册、nginx 以 `host not found in upstream` 退出的问题；nginx 现在显式等待 `hermes-webui` 启动。
- Studio 镜像已通过 production-pruned 依赖、Server bundle、BrowserPanel 产物和 HTTP 200 启动验证，并携带 exact revision/tree OCI provenance；镜像引用使用唯一 tag，digest 仅作旁路审计。
- 许可证元数据按当前上游纠正为 BSL-1.1；Browser Runtime 为 Apache-2.0。Hermes Studio 在 2029-05-10 Change Date 前的商业使用需按 EKKOLearnAI 的 BSL 条款另行确认，之后 Change License 为 Apache-2.0。

### 变更文件
- `CHANGELOG.md`
- `lzc-manifest.yml`
- `package.yml`

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
