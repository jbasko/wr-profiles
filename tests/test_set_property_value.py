import pytest

from tests.warehouse_profile import WarehouseProfile


@pytest.mark.parametrize(
    "name,profile_is_live", [["staging", True], ["staging", False], [None, True], [None, False]]
)
def test_sets_profile_property_value(name, profile_is_live):
    profile = WarehouseProfile(name=name, profile_is_live=profile_is_live)

    assert profile.username is None

    profile.username = "the-new-username"
    assert profile.username == "the-new-username"

    assert "username" not in profile.__dict__
