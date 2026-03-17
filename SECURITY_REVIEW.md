# Security Review & Fix Notes (2026-03-17)

本文件记录对 `geek-movie-forge` 仓库做的安全巡检结果、已修复点位、以及上线/本地运行时的注意事项。

> 范围：`services/api`（FastAPI）、`packages/provider_sdk`（出站请求网关）、`apps/frontend`（Next.js 控制台）与基础运行脚本/配置。

## 已修复的高风险点

### 1) API CORS 配置不安全/不兼容

**问题**

- 原先 `services/api/app/main.py` 里使用 `allow_origins=["*"]` 且 `allow_credentials=True`：
  - 这在安全上属于“对所有来源开放 + 允许携带凭证”，非常危险；
  - 同时也与浏览器的 CORS 规则不兼容（携带凭证时不能使用 `*`）。

**修复**

- 改为由环境变量控制允许来源，默认仅放行本地前端：
  - 代码位置：`services/api/app/main.py`
  - 配置位置：`services/api/app/core/config.py`
  - `.env.example` 增加了 `CORS_ALLOW_ORIGINS` / `CORS_ALLOW_CREDENTIALS`

**注意事项**

- 生产环境必须设置 `CORS_ALLOW_ORIGINS` 为你的前端域名列表（逗号分隔），不要使用 `*`。
- 如果你使用的是 `Authorization: Bearer <token>`（当前前端实现），通常不需要开启 `CORS_ALLOW_CREDENTIALS=true`。

### 2) Provider 出站请求存在 SSRF 风险

**问题**

- Provider 的 `base_url` 与 `routes.*.path` 支持配置绝对 URL；若 API 对外可访问，攻击者可通过配置 Provider 诱导服务端请求内网/本机地址（SSRF）。

**修复**

- 在真正发起 httpx 请求前对 URL 做安全校验与策略拦截：
  - 代码位置：`packages/provider_sdk/gateway.py`（`_ensure_outbound_provider_url_is_allowed`）
  - 默认策略：
    - `APP_ENV` 为 `local/test`：允许私网/loopback 地址与 `http://`（便于本地对接 Ollama/LocalAI 等）。
    - 其他环境：默认禁止私网/loopback 地址、默认禁止 `http://`（要求 https）。
    - **始终禁止** link-local（如 `169.254.169.254` 元数据地址）、multicast、unspecified、reserved 等高风险/无意义地址。

**可配置开关（按需启用）**

- `GMF_ALLOW_PRIVATE_PROVIDER_URLS=true`：允许私网/loopback（非 local/test 环境默认禁用）。
- `GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS=true`：允许 `http://`（非 local/test 环境默认禁用）。

**注意事项**

- 若生产环境确实需要访问内网 Provider，请务必在网络层做额外隔离（egress allowlist / VPC / 防火墙），并监控请求目的地。
- 本仓库的 URL 校验不会做 DNS 解析级别的重绑定防护；要更强的 SSRF 防护建议使用“域名 allowlist + egress policy”。

### 3) API 日志中潜在敏感信息泄露 + 大请求内存 DoS 风险

**问题**

- `services/api/app/middleware/api_logging.py` 之前会把整个 request body 读入内存再回放：
  - 大 body 会造成不必要的内存占用（DoS 风险）。
- 同时会原样记录 query params（若把 token 放 query 里会被写入日志）。

**修复**

- 改为“流式读取 + 只截取前 N 字节用于预览”，不再完整缓存整个 body。
- 对 query params 也做敏感字段脱敏（与 JSON body 的敏感 key 规则保持一致）。
- 增加请求体大小上限（超出返回 413）：
  - 配置项：`API_MAX_REQUEST_BYTES`（0 表示不限制）
  - 代码位置：
    - `services/api/app/middleware/api_logging.py`
    - `services/api/app/main.py`（把配置传入中间件）
    - `services/api/app/core/config.py`（读取环境变量）

**注意事项**

- 若需要上传较大的 base64（不推荐），请调整 `API_MAX_REQUEST_BYTES` 或改用对象存储 + URL 引用的方式。
- `GMF_LOG_PROVIDER_BODY=true` 会记录 provider 请求/响应 body（已做摘要处理，但仍可能包含敏感内容），生产环境谨慎开启。

### 4) 非本地环境误用默认 JWT_SECRET 的风险

**问题**

- 以前如果未设置 `JWT_SECRET`，会使用默认值；这在生产环境属于高危误配置。

**修复**

- `APP_ENV` 不为 `local/test` 时，禁止使用默认 `_DEFAULT_JWT_SECRET`：
  - 代码位置：`services/api/app/core/config.py`

## 关联的功能性修正（降低误配置概率）

- 前端 API Base 环境变量命名不一致：
  - Docker Compose 使用 `NEXT_PUBLIC_API_BASE_URL`，前端代码以前读取 `NEXT_PUBLIC_API_URL`。
  - 已修复为优先读取 `NEXT_PUBLIC_API_BASE_URL`，并兼容旧变量。
  - 代码位置：`apps/frontend/lib/api.ts`

## 验证方式

本次变更已在本地执行：

- `pytest services/api/tests -q`
- `python3 -m compileall services workers packages -q`

新增/更新的测试用例：

- `services/api/tests/test_provider_gateway_security.py`（SSRF/URL 策略拦截）
- `services/api/tests/test_api_logging_middleware_security.py`（413 限制 + query 脱敏）

## 仍需你在部署/上线时关注的事项

- `docker-compose.yml` 已将常用端口默认绑定到 `127.0.0.1`（避免无意暴露到局域网/公网），但 Postgres/MinIO 仍使用示例账号密码：生产环境务必更换强密码、使用私有网络与安全组，并避免把 `.env` 提交到仓库。
- 认证缺少速率限制/防爆破：建议在网关层（Nginx/Traefik/Cloud WAF）添加 rate limit，并对登录/注册加审计与告警。
- 前端 token 使用 localStorage：一旦发生 XSS 会导致 token 泄露；生产级建议迁移到 httpOnly Cookie + CSRF 防护方案。
