"""Unit test fixtures — no real database connection required."""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def db():
    """Lightweight mock DB session for unit tests that need to instantiate classes."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    mock.rollback = AsyncMock()
    return mock
