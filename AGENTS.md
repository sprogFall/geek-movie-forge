# Repository Guidelines

## 项目结构与模块划分

本仓库采用前后端同仓 monorepo 结构。

- `apps/frontend`：Next.js 前端控制台。
- `apps/remotion_renderer`：Node 渲染服务占位。
- `services/api`：FastAPI 接口服务。
- `services/orchestrator`：LangGraph 编排服务。
- `workers/text`、`workers/image`、`workers/voice`、`workers/render`：后台任务执行器。
- `packages/*`：共享 Python 包，如 `shared`、`db`、`provider_sdk`、`storage`。
- `infra/docker`：Dockerfile 与容器运行配置。
- `e2e`：端到端测试目录。

路由层只处理协议与校验，公共领域逻辑优先放到 `packages/` 或服务层。

## 构建、测试与开发命令

- `npm install`：安装前端与渲染服务依赖。
- `npm run dev:frontend`：启动前端开发环境。
- `npm run build:frontend`：构建前端生产包。
- `pytest services/api/tests -q`：运行当前 FastAPI 测试。
- `python3 -m compileall services workers packages`：快速检查 Python 语法。
- `docker compose up --build`：按 `.env` 配置启动整套本地服务。

## 编码风格与命名规范

- Python 使用 4 空格缩进，模块名用 `snake_case`，类名用 `PascalCase`，常量用 `UPPER_SNAKE_CASE`。
- TypeScript/React 使用 2 空格缩进，组件名用 `PascalCase`，文件名建议 `kebab-case`，如 `task-card.tsx`。
- Python 使用 `ruff` 做格式与 lint，使用 `pyright` 做类型检查。
- 前端使用严格 TypeScript，并通过 `@/*` 别名引用本地模块。

## 测试要求

默认采用 TDD：先写测试，确认失败，再写实现。

- Python 测试文件命名为 `test_*.py`，例如 `services/api/tests/test_tasks.py`。
- 每个功能至少覆盖正常路径、非法输入、边界场景和失败场景。
- 核心编排、worker、provider 适配层应保持高覆盖率，核心域代码建议不低于 85%。

## 提交与合并请求

当前分支尚无历史提交，建议统一采用 Conventional Commits：`feat:`、`fix:`、`refactor:`、`test:`、`docs:`。

Git 推送统一使用 SSH 远端，不使用 HTTPS token。当前仓库 `origin` 应保持为 `git@github.com:sprogFall/geek-movie-forge.git`；如发现远端被改回 HTTPS，请先修正再执行 `git push`。

PR 至少应包含：

- 变更目的与实现摘要；
- 关联任务或 issue；
- 测试结果，必要时附界面截图；
- 若涉及配置、Schema、Docker 变更，需单独说明影响范围。

## 安全与配置提示

- 从 `.env.example` 复制生成 `.env`，不要提交密钥。
- 不要修改或提交 `node_modules`、`.pytest_cache`、`.gh-helper-cache` 等缓存目录。
- 测试优先使用本地假数据与 mock，避免硬编码外部凭据或真实 provider 地址。
