# SQLite/MySQL Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace JSON-file persistence with a real SQL database layer that supports SQLite locally and MySQL through configuration.

**Architecture:** The API will create one SQLAlchemy engine/session factory from structured settings, create all schema objects on startup, and pass the session factory into each service. Service methods keep the current business behavior but load and persist state through ORM rows instead of in-memory dictionaries or JSON files.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.x, SQLite, MySQL via PyMySQL, pytest

---

### Task 1: Add Backend Configuration And Database Bootstrap

**Files:**
- Create: `packages/db/models.py`
- Modify: `packages/db/session.py`
- Modify: `services/api/app/core/config.py`
- Test: `services/api/tests/test_database_config.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_get_settings_defaults_to_sqlite_backend(...):
    ...

def test_get_settings_builds_mysql_url_from_structured_fields(...):
    ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest services/api/tests/test_database_config.py -q`
Expected: FAIL because SQLite/MySQL settings and URL derivation do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement backend-aware settings and SQLAlchemy engine/session helpers.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest services/api/tests/test_database_config.py -q`
Expected: PASS.

### Task 2: Replace JSON Persistence In Services With Database Persistence

**Files:**
- Modify: `services/api/app/services/auth_service.py`
- Modify: `services/api/app/services/project_service.py`
- Modify: `services/api/app/services/task_service.py`
- Modify: `services/api/app/services/provider_service.py`
- Modify: `services/api/app/services/asset_service.py`
- Modify: `services/api/app/services/call_log_service.py`
- Test: `services/api/tests/test_persistence.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_domain_data_survives_restart_with_sqlite(...):
    ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest services/api/tests/test_persistence.py -q`
Expected: FAIL because services still depend on `JsonFileStore`/in-memory state.

- [ ] **Step 3: Write the minimal implementation**

Implement ORM-backed CRUD and persistence for all six services.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest services/api/tests/test_persistence.py -q`
Expected: PASS.

### Task 3: Rewire Application Startup, Test Defaults, And Deployment Config

**Files:**
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/dependencies/auth.py`
- Modify: `services/api/app/dependencies/services.py`
- Modify: `services/api/tests/conftest.py` or repository `conftest.py`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `pyproject.toml`
- Test: `pytest services/api/tests -q`
- Test: `python3 -m compileall services packages`

- [ ] **Step 1: Write the failing tests**

Use the updated persistence/config tests first so startup wiring is forced to use the new database layer.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest services/api/tests/test_database_config.py services/api/tests/test_persistence.py -q`
Expected: FAIL until app wiring and test defaults use the SQL layer.

- [ ] **Step 3: Write the minimal implementation**

Wire the new session factory into app startup, make tests default to isolated SQLite, and align env/docker/dependencies with MySQL support.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest services/api/tests -q`
Expected: PASS.

- [ ] **Step 5: Run final verification**

Run: `python3 -m compileall services packages`
Expected: no syntax errors.
