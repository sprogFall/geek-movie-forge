# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

Geek Movie Forge 是一个 AI 驱动的短视频生产平台，采用前后端同仓 monorepo 结构。后端为 Python (FastAPI + Celery + LangGraph)，前端为 Next.js 15 + React 19，纯 CSS 设计系统，无第三方 UI 库。

## 常用命令

### 前端

```bash
npm install                        # 安装前端和渲染服务依赖（根目录执行）
npm run dev:frontend               # 启动 Next.js 开发服务器
npm run build:frontend             # 生产构建
cd apps/frontend && npx tsc --noEmit  # 前端类型检查
```

### Python 后端

```bash
pytest services/api/tests -q       # 运行 API 测试
pytest services/api/tests/test_generations.py -q  # 运行单个测试文件
python3 -m compileall services workers packages   # 快速语法检查
ruff check services workers packages              # lint
ruff format services workers packages             # 格式化
pyright                            # 类型检查（配置在 pyproject.toml）
```

### Docker 全栈

```bash
cp .env.example .env
docker compose up --build          # 启动所有服务（API:8000, Web:3000, Postgres, Redis, MinIO）
docker compose up --build --profile automation  # 额外启动 n8n 自动化
```

## 架构设计

### 请求流转

```
前端 (Next.js :3000)
  → FastAPI API (:8000)
    → Service 层（业务逻辑）
      → ProviderGateway（调用外部 AI 服务）
      → AssetService（保存生成结果）
    → Celery Workers（异步任务，经 Redis 队列分发）
    → LangGraph Orchestrator（多步骤编排，尚未实现）
```

### 后端分层

- **路由层** (`services/api/app/api/routes/`)：只做协议转换和参数校验，通过 `Depends` 注入 Service。
- **服务层** (`services/api/app/services/`)：所有业务逻辑在此。当前为 `InMemory*Service` 内存实现，后续切换为 DB 实现。错误通过 `ServiceError` 子类（`NotFoundServiceError` → 404, `ConflictServiceError` → 409, `ValidationServiceError` → 422, `UpstreamServiceError` → 502）统一抛出，由 `main.py` 全局异常处理器转为 JSON 响应。
- **共享层** (`packages/shared/`)：`contracts/` 存放 Pydantic 请求/响应模型，`enums/` 存放领域枚举。路由和服务层共用这些类型。
- **Provider SDK** (`packages/provider_sdk/`)：`ProviderGateway` Protocol 定义外部 AI 服务调用接口，`HttpProviderGateway` 为 httpx 实现。

### 服务依赖注入

FastAPI 应用通过 `lifespan` 上下文管理器在启动时实例化所有 Service，挂载到 `app.state`。路由通过 `services/api/app/dependencies/services.py` 中的 `Depends` 函数获取服务实例。

### API 端点（/api/v1）

| 路由前缀 | 能力 |
|---------|------|
| `/tasks` | 任务创建与查询 |
| `/providers` | AI 供应商 CRUD，模型能力校验 |
| `/assets` | 素材 CRUD，支持按 type/category/origin/provider 过滤 |
| `/generations/images` | 图片生成（校验模型 IMAGE 能力） |
| `/generations/videos` | 视频生成（支持参考图和场景描述输入） |
| `/generations/texts` | 文本生成（脚本、字幕、翻译等） |

### 前端架构

- **App Router** (`apps/frontend/app/`)：每个功能独立页面，页面组件为 Server Component，内部引用 `"use client"` 的交互表单组件。
- **组件** (`apps/frontend/components/`)：按功能域分目录（`generations/`, `providers/`, `assets/`, `shell/`, `dashboard/`）。
- **API 客户端** (`apps/frontend/lib/api.ts`)：统一 fetch 封装，所有后端调用经此。`NEXT_PUBLIC_API_URL` 环境变量控制后端地址。
- **类型** (`apps/frontend/types/api.ts`)：与后端 Pydantic contracts 一一对应的 TypeScript 类型。
- **导航** (`apps/frontend/lib/navigation.ts`)：分 Section 的导航配置，驱动侧边栏渲染。
- **设计系统**：纯 CSS 变量（`globals.css`），暖米色调 + 毛玻璃面板风格，`--accent: #be5b2d`，圆角 24px，无 CSS-in-JS。

### 后台任务（占位）

- Workers 在 `workers/text|image|voice|render`，使用 Celery，队列名 `queue:text|image|voice|render`。
- Orchestrator 在 `services/orchestrator`，计划使用 LangGraph 做多步骤编排。
- `packages/skill_runtime` 用于技能加载与执行，均为占位结构。

## 测试约定

- 默认 TDD 流程：先写失败测试，再写实现。
- 测试使用 `TestClient(app)` 创建同步客户端，通过替换 `app.state` 上的服务实例注入 mock（如 `FakeProviderGateway`）。
- 每个功能至少覆盖：正常路径、非法输入、边界场景、失败场景。
- 测试路径配置在 `pyproject.toml [tool.pytest.ini_options]`，覆盖 `services/`, `workers/`, `packages/`, `e2e/`。

## 编码规范

- **Python**：4 空格，`snake_case` 模块/函数，`PascalCase` 类，`UPPER_SNAKE_CASE` 常量。Ruff lint + format，Pyright 类型检查，`line-length = 100`。
- **TypeScript/React**：2 空格，组件 `PascalCase`，文件 `kebab-case.tsx`。严格模式，`@/*` 路径别名。
- 公共领域逻辑优先放 `packages/`，路由层只处理协议与校验。

## Git 约定

- Conventional Commits：`feat:`, `fix:`, `refactor:`, `test:`, `docs:`。
- 远端统一使用 SSH（`git@github.com:sprogFall/geek-movie-forge.git`），不使用 HTTPS token。若发现远端被改回 HTTPS，先修正再 push。
