import os

# Disable file persistence during tests to prevent cross-test contamination
os.environ["PERSIST_ENABLED"] = "false"

# Clear cached settings so they pick up the test env vars
from services.api.app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
