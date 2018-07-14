import os

import pytest


@pytest.fixture(autouse=True)
def reset_warehouse_profile(monkeypatch):
    for k in list(os.environ):
        if k.startswith('WAREHOUSE_'):
            del os.environ[k]
            monkeypatch.delenv(k, raising=False)
