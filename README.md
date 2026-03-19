# Geek Movie Forge

> AI 原生短视频生产控制台与平台骨架（monorepo）。

![Next.js](https://img.shields.io/badge/Next.js-15-black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-0.4-1f6feb)
![Celery](https://img.shields.io/badge/Celery-5.4-37814a)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Redis](https://img.shields.io/badge/Redis-7-dc382d)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ed)

Geek Movie Forge 旨在把 “剧本 → 生成素材 → 任务编排 → 渲染出片” 的链路做成一个可扩展的平台。
当前仓库已经具备可登录的前端控制台、FastAPI API、Provider 网关、文本/图片/视频生成接口、素材库、项目/任务、调用日志等基础能力；LangGraph 编排、Celery Worker、Remotion 渲染链路也已完成容器接线与服务骨架，便于你在此基础上继续演进真实业务。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 认证与会话 | 注册 / 登录 / JWT Token / `/api/v1/auth/me`，前端 401 自动登出 |
| 项目与任务 | 项目创建与查询，任务创建与按项目/状态过滤 |
| Provider 管理 | 内置 ModelScope、Volcengine Ark 供应商模板，也支持新增自定义 Provider、模型能力、路由和超时配置 |
| 资产库 | 统一管理手工与生成素材，支持 `image` / `video` / `text`，支持分类、标签、来源和 Provider 过滤 |
| 生成接口 | 支持文本、图片、视频生成，结果可直接保存到素材库 |
| 多段视频生成 | 支持先用文本模型规划分段，再批量生成视频，并对单段结果执行重生成 |
| 调用日志 | 记录 Provider 调用状态、请求摘要、耗时和 token usage，便于排查 |
| 本地持久化与安全 | 本地 `.data/*.json` 持久化、请求体大小限制、敏感字段脱敏日志、Provider URL 安全校验 |
| 本地一键启动 | `docker compose` + 跨平台脚本启动前端、API、依赖，以及可选的 orchestrator / workers / n8n |

## 架构概览

```text
Browser (Next.js Console, apps/frontend)
  └─ HTTP -> FastAPI (services/api)
              ├─ Auth / Projects / Tasks / Providers / Assets / Generations / Call Logs
              ├─ Local persistence (.data/*.json, dev default)
              ├─ Provider Gateway (packages/provider_sdk)
              │    ├─ generic_json
              │    ├─ ModelScope
              │    └─ Volcengine Ark
              └─ Pipeline skeleton
                   ├─ Orchestrator (services/orchestrator, LangGraph)
                   ├─ Workers (workers/*, Celery + Redis)
                   └─ Infra (Docker Compose)
                        ├─ PostgreSQL
                        ├─ Redis
                        ├─ MinIO
                        └─ Remotion Renderer
```

说明：当前 API 默认使用本地 `JsonFileStore` 持久化到 `.data/`；PostgreSQL、Redis、MinIO、Remotion Renderer 主要通过 Docker Compose 为后续编排、渲染和异步链路提供基础设施。

## 项目结构

```text
apps/
  frontend/            # Next.js 前端控制台
  remotion_renderer/   # Node 渲染服务（占位）
services/
  api/                 # FastAPI API 服务
  orchestrator/        # LangGraph 编排服务骨架
workers/
  text/                # 文本任务 worker
  image/               # 图片任务 worker
  voice/               # 配音/音频任务 worker
  render/              # 渲染任务 worker
packages/
  shared/              # 共享 contracts/enums
  provider_sdk/        # Provider 网关与适配层
  db/                  # 数据库基础设施占位
  storage/             # 存储基础设施占位
  skill_runtime/       # 技能运行时占位
  standards/           # 标准与约定占位
infra/docker/          # Dockerfile 与容器运行配置
e2e/                   # 端到端测试目录（预留）
scripts/               # 本地一键启动/停止脚本
```

## 快速开始（推荐：Docker 一键启动）

### 前置要求

- Docker Desktop / Docker Engine（需支持 `docker compose`）
- 使用脚本启动时，若 `.env` 不存在会自动由 `.env.example` 生成
- 直接执行 `docker compose` 前，请先手动复制 `.env.example` 为 `.env`
- `JWT_SECRET` 至少 32 字符；示例值仅适用于本地开发

### Linux/macOS

最小启动（`web + api + postgres + redis`）：

```bash
./scripts/dev-up.sh --detach
```

全量启动（包含 `orchestrator`、`worker_*`、`minio`、`remotion_renderer`）：

```bash
./scripts/dev-up.sh --full --detach
```

全量启动并启用自动化 profile（额外启动 `n8n`）：

```bash
./scripts/dev-up.sh --full --automation --detach
```

停止：

```bash
./scripts/dev-down.sh
```

停止并删除 volumes：

```bash
./scripts/dev-down.sh --volumes
```

### Windows（PowerShell）

最小启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 -Detach
```

全量启动：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 -Full -Detach
```

全量启动并启用自动化 profile：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-up.ps1 -Full -Automation -Detach
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-down.ps1
```

### 直接使用 Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

说明：前端容器现在会在镜像构建阶段执行静态导出，并由 Nginx 直接托管 `dist`。如果 API 不是通过 `http://localhost:8000` 对浏览器暴露，请先在 `.env` 中设置 `NEXT_PUBLIC_API_BASE_URL`，再执行 `docker compose up --build`。

如只想拉起最小链路：

```bash
docker compose up --build api web
```

如需额外启用 `n8n`：

```bash
docker compose --profile automation up --build
```

### 常用地址

| 服务 | 地址 |
| --- | --- |
| 前端控制台 | http://localhost:3000 |
| API | http://localhost:8000 |
| API 健康检查 | http://localhost:8000/healthz |
| API 文档（Swagger UI） | http://localhost:8000/docs |
| Remotion Renderer | http://localhost:3100/healthz |
| MinIO API | http://localhost:9000 |
| MinIO Console | http://localhost:9001 |
| n8n（可选 profile） | http://localhost:5678 |

## 本地开发（不使用 Docker）

如果你更偏好本地直接跑进程，建议准备 Node.js 20+ 与 Python 3.11+。

### 前端

```bash
npm install
npm run dev:frontend
```

### Remotion Renderer（占位服务）

```bash
npm run dev:remotion
```

### 后端 API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 编排与 Worker（骨架）

以下命令假设你已自行准备可用的 Redis / 相关依赖：

```bash
python -m services.orchestrator.app.runner
celery -A workers.text.app.celery_app worker -Q queue:text --loglevel=INFO
celery -A workers.image.app.celery_app worker -Q queue:image --loglevel=INFO
celery -A workers.voice.app.celery_app worker -Q queue:voice --loglevel=INFO
celery -A workers.render.app.celery_app worker -Q queue:render --loglevel=INFO
```

## 测试与构建

后端测试：

```bash
pytest services/api/tests -q
```

Python 语法快速检查：

```bash
python3 -m compileall services workers packages
```

前端构建：

```bash
npm run build:frontend
```

构建完成后，静态站点产物位于 `apps/frontend/dist/`。

## 环境变量说明（摘录）

`.env.example` 提供了基础模板。你至少需要关注：

- `APP_ENV`：运行环境，默认 `local`
- `NEXT_PUBLIC_API_BASE_URL`：前端静态构建时写入的 API 基地址，默认 `http://localhost:8000`
- `JWT_SECRET`：至少 32 字符；非 `local/test` 环境禁止使用默认值
- `JWT_EXPIRE_MINUTES`：JWT 过期时间，默认 `1440`
- `PERSIST_ENABLED` / `PERSIST_DIR`：是否启用本地 JSON 持久化，以及持久化目录（默认 `.data`）
- `VOLCENGINE_ARK_API_KEY`：内置 Volcengine Ark Provider 使用
- `OPENAI_API_KEY`：预留给自定义/后续 Provider 接入
- `CORS_ALLOW_ORIGINS` / `CORS_ALLOW_CREDENTIALS`：API 跨域策略
- `API_MAX_REQUEST_BYTES`：API 请求体大小上限，默认 `10485760`
- `GMF_ALLOW_PRIVATE_PROVIDER_URLS` / `GMF_ALLOW_INSECURE_HTTP_PROVIDER_URLS`：仅建议在本地测试时放宽 Provider URL 安全限制

## 贡献约定

- 不要提交 `.env`、`node_modules/`、缓存目录等（仓库已在 `.gitignore` 中屏蔽）
- 建议使用 Conventional Commits：`feat:`、`fix:`、`refactor:`、`test:`、`docs:`
