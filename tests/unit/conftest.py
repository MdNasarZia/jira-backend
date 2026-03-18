import pytest


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """No-op override — unit tests use mocks, no database connection needed."""
    yield
