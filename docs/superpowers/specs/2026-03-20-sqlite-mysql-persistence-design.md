# SQLite/MySQL Persistence Design

**Goal**

Replace the API service's JSON-file persistence with a real database layer that can run on SQLite for local/test environments and MySQL for configured deployments.

**Current State**

The API currently stores mutable state in memory and optionally snapshots it into JSON files through `JsonFileStore`. The persistence boundary is duplicated across six services: auth, projects, tasks, providers, assets, and call logs. Startup wiring in `services/api/app/main.py` decides whether persistence exists at all by toggling a file store.

**Target Design**

The backend will use SQLAlchemy as the single persistence mechanism for all mutable API data. Configuration will expose `DB_BACKEND=sqlite|mysql`. SQLite will be the default backend for local and test usage. MySQL will be enabled through explicit host/user/password/database settings. The application will build one engine and one session factory during startup, create the schema if needed, and inject that session factory into all services.

**Database Layer**

- `packages/db/session.py` will own backend validation, SQLAlchemy URL construction, engine creation, and schema initialization.
- `packages/db/models.py` will define the SQLAlchemy ORM tables for users, projects, tasks, providers, assets, and call logs.
- JSON-like payloads already present in the contracts, such as provider models/routes, asset metadata/tags, and token usage, will be stored in SQL JSON columns so the service layer can round-trip existing shapes without redesigning the API contracts.

**Service Layer**

- Each API service will stop keeping mutable state in Python dictionaries.
- Services will open short-lived SQLAlchemy sessions per method call and translate between ORM rows and existing contract models.
- Built-in providers remain synthesized through the provider service logic, but they will now be refreshed and persisted in the database instead of a JSON file.

**Configuration**

- Remove the old `PERSIST_ENABLED` and `PERSIST_DIR` behavior from runtime logic.
- Add `db_backend`, `sqlite_path`, `mysql_host`, `mysql_port`, `mysql_user`, `mysql_password`, and `mysql_database` to settings.
- Settings will derive a concrete SQLAlchemy URL from those fields rather than consuming a raw `DATABASE_URL`.

**Testing Strategy**

- Add test coverage for backend configuration and URL building.
- Replace JSON persistence tests with database persistence tests using temporary SQLite files.
- Keep the existing API test suite as regression coverage for auth, projects, tasks, providers, assets, generations, and call logs.
- Test environments will use in-memory SQLite so each app lifespan gets an isolated database.

**Non-Goals**

- No migration of existing JSON files into SQLite or MySQL.
- No Alembic migration history in this change; schema creation is bootstrap-only for now.
- No changes to frontend behavior or external API shapes.
