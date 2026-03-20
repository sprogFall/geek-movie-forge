import os

# Use isolated in-memory SQLite for tests
os.environ["APP_ENV"] = "test"
os.environ["DB_BACKEND"] = "sqlite"
os.environ["SQLITE_PATH"] = ":memory:"

# Clear cached settings so they pick up the test env vars
from services.api.app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
