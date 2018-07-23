import os

import pytest


@pytest.fixture(autouse=True)
def reset_warehouse_profile_envvars(monkeypatch):
    """
    Reset any environment variables that could affect the WarehouseProfile used in tests.
    """
    for k in list(os.environ):
        if k.startswith('WAREHOUSE_'):
            del os.environ[k]
            monkeypatch.delenv(k, raising=False)
