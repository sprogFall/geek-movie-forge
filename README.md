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
当前仓库以工程骨架为主：前端控制台 + 后端 API + 编排服务 + Worker + 共享 contracts/packages，便于你在此基础上快速迭代真实业务。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 认证与会话 | 注册/登录/JWT Token，401 自动登出 |
| Provider 管理 | 可配置 Provider 基础信息、模型能力与路由 |
| 资产库 | 统一存储与查询生成/手工资产（image/video/text） |
| 生成接口 | 支持 image/video/text 生成，并可选保存到资产库 |
| 编排与 Worker | LangGraph 编排服务 + Celery worker 队列（text/image/voice/render） |
| 本地一键启动 | Linux/macOS/Windows 一键启动脚本，默认拉起前后端与依赖 |

## 架构概览

```text
Browser (Next.js Console)
  └─ HTTP -> FastAPI (services/api)
              ├─ Provider 管理 / 资产库 / 生成接口
              ├─ 调用 Provider Gateway (packages/provider_sdk)
              ├─ 编排服务 (services/orchestrator, LangGraph)
              └─ 异步任务 (workers/*, Celery + Redis)
                     ├─ DB: Postgres
                     ├─ Storage: MinIO
                     └─ Render: Remotion Renderer
```

## 项目结构

```text
apps/
  frontend/            # Next.js 前端控制台
  remotion_renderer/   # Node 渲染服务（占位/容器化）
services/
  api/                 # FastAPI API 服务
  orchestrator/        # LangGraph 编排服务
workers/
  text/                # 文本任务 worker
  image/               # 图片任务 worker
  voice/               # 配音/音频任务 worker
  render/              # 渲染任务 worker
packages/
  shared/              # 共享 contracts/enums（Python）
  provider_sdk/        # Provider 网关与适配层
  db/ storage/ ...     # 共享基础设施包（持续补齐中）
infra/docker/          # Dockerfile 与容器运行配置
e2e/                   # 端到端测试目录（预留）
scripts/               # 本地一键启动脚本
```

## 快速开始（推荐：Docker 一键启动）

### 前置要求

- Docker Desktop / Docker Engine（需支持 `docker compose`）

首次启动会自动从 `.env.example` 生成 `.env`。注意：`.env` 不会被提交到仓库。

### Linux/macOS

最小启动（仅前端 + API + 依赖）：

```bash
./scripts/dev-up.sh --detach
```

全量启动（workers/orchestrator/minio/remotion 等）：

```bash
./scripts/dev-up.sh --full --detach
```

停止：

```bash
./scripts/dev-down.sh
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

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-down.ps1
```

### 常用地址

| 服务 | 地址 |
| --- | --- |
| 前端控制台 | http://localhost:3000 |
| API | http://localhost:8000 |
| API 健康检查 | http://localhost:8000/healthz |
| API 文档（Swagger UI） | http://localhost:8000/docs |
| Remotion Renderer | http://localhost:3100/healthz |
| MinIO | http://localhost:9001 |
| n8n（可选 profile） | http://localhost:5678 |

## 本地开发（不使用 Docker）

如果你更偏好本地直接跑进程：

### 前端

```bash
npm install
npm run dev:frontend
```

### 后端 API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn services.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 测试与构建

后端测试：

```bash
pytest services/api/tests -q
```

前端构建：

```bash
npm run build:frontend
```

## 环境变量说明（摘录）

`.env.example` 提供了完整模板。你至少需要保证：

- `JWT_SECRET`：至少 32 字符（项目会在启动时校验）
- `OPENAI_API_KEY`：接入真实 provider 时需要（当前骨架可先留空）

## 贡献约定

- 不要提交 `.env`、`node_modules/`、缓存目录等（仓库已在 `.gitignore` 中屏蔽）
- 建议使用 Conventional Commits：`feat:`、`fix:`、`refactor:`、`test:`、`docs:`
