# Geek Movie Forge

Same-repo monorepo for the Geek Movie Forge platform.

## Structure

```text
apps/
  frontend/            # Next.js frontend
  remotion_renderer/   # Node render service placeholder
services/
  api/                 # FastAPI API
  orchestrator/        # LangGraph orchestration service
workers/
  text/
  image/
  voice/
  render/
packages/
  shared/
  db/
  provider_sdk/
  storage/
  standards/
  skill_runtime/
  testkit/
infra/
docs/
```

## Commands

Python backend:

```bash
pytest services/api/tests -q
```

Frontend workspace:

```bash
npm install
npm run dev:frontend
```

Compose:

```bash
cp .env.example .env
docker compose up --build
```
