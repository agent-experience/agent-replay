"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from agent_replay.store import Store


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "traces.db"


@pytest.fixture()
def store(db_path):
    s = Store(db_path)
    yield s
    s.close()
