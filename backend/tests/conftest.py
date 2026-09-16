import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A real (temp) file DB rather than :memory: — an in-memory sqlite DB is
# scoped to a single connection, but SQLAlchemy's async pool opens more than
# one, which would make tables "disappear" between requests in the e2e test.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_sentinelai.db")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def _init_test_db(event_loop):
    from app.database import init_db

    db_path = "./test_sentinelai.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    event_loop.run_until_complete(init_db())
    yield
    if os.path.exists(db_path):
        os.remove(db_path)
