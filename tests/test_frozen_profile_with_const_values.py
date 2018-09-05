import pytest

from tests.warehouse_profile import WarehouseProfile


@pytest.mark.parametrize("profile_name", ["staging", None])
def test_const_values_set_on_frozen_profile_instance(profile_name, monkeypatch):
    wp = WarehouseProfile.load(
        name=profile_name, values={"host": "localhost.test", "username": "test"}
    )

    assert not wp.is_live
    assert wp.host == "localhost.test"
    assert wp.username == "test"
    assert wp.to_dict() == {
        WarehouseProfile.host: "localhost.test",
        WarehouseProfile.username: "test",
    }


def test_frozen_profile_with_defaults(monkeypatch):
    wp = WarehouseProfile.load(
        name="staging",
        defaults={"host": "default-host", "username": "default-username"},
    )

    assert wp._const_defaults == {
        "host": "default-host",
        "username": "default-username",
    }

    assert wp._const_values == {}

    assert wp.host == "default-host"
    assert wp.username == "default-username"

    monkeypatch.setenv("WAREHOUSE_STAGING_HOST", "custom-host")
    assert wp.host == "default-host"
    assert wp.username == "default-username"

    wp._do_load()
    assert wp.host == "custom-host"
    assert wp.username == "default-username"
