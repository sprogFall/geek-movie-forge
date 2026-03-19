# 全局代码审查报告

日期：2026-03-19

审查范围：当前仓库 `HEAD` 版本，以及本次修复后的验证结果。

## 审查结论

本轮全局审查重点关注了以下高风险区域：

- Provider 外呼安全边界
- 内置 Provider 配置与持久化一致性
- API 测试覆盖的完整性

原先发现的两项重要问题已完成修复，并补充了对应回归测试。

## 已修复问题

### 1. Provider 外呼存在 DNS 级别的 SSRF 绕过风险

问题概述：

- 原实现只拦截字面量 IP 和 `localhost`
- 如果用户配置的是域名，而该域名实际解析到 `127.0.0.1`、私网地址或其他受限地址，原逻辑会直接放行
- 这意味着在非本地环境下，仍可能通过恶意域名把请求打到内网服务

修复方式：

- 在 `packages/provider_sdk/gateway.py` 中增加主机解析逻辑
- 对域名解析出的每个 IP 逐一执行与字面量 IP 相同的安全校验
- 保留已有的 `localhost`、私网、回环、链路本地、多播、未指定地址等限制

新增测试：

- 域名解析到回环地址时必须拦截
- 域名解析到公网地址时允许通过
- 原有 gateway 单测补齐了显式 DNS mock，避免测试依赖真实外部 DNS

### 2. 内置 Provider 配置会被持久化旧数据锁死

问题概述：

- 内置 Provider 首次写入持久化后，后续启动不会再从环境变量刷新
- 如果首次启动时密钥缺失、配置错误，或者后续做了密钥轮换，旧数据会一直留在持久化层
- 这会导致内置 Provider 看起来存在，但实际仍使用旧的错误配置

修复方式：

- 在 `services/api/app/services/provider_service.py` 中增加内置 Provider 对账刷新逻辑
- 每次启动时，如果发现已有 builtin 记录，就按当前 `_BUILTIN_PROVIDER_DEFS` 与环境变量重新生成并覆盖 builtin 配置
- 保留原有 `provider_id` 和 `created_at`，刷新 `name`、`base_url`、`api_key`、`models`、`routes`、`updated_at`

新增测试：

- 持久化后的 builtin API key 在环境变量变化后应自动刷新
- 持久化后的 builtin 定义在被人工改坏后，重启应恢复到内置标准配置

## 测试与验证

已执行：

- `pytest services/api/tests/test_provider_gateway_security.py services/api/tests/test_persistence.py -q`
- `pytest services/api/tests -q`
- `python3 -m compileall services packages workers`
- `npm run build:frontend`

本轮还额外补强了与 Provider 外呼安全相关的测试场景，使测试覆盖不再只依赖字面量 IP。

## 当前残余风险

- 当前持久化仍是本地 JSON 文件实现，适合本地开发，不适合作为生产级并发持久化方案
- 本次没有扩展到更大范围的 e2e 场景，例如真实 provider 配置变更后的整链路集成验证
