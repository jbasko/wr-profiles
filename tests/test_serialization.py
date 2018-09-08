import pytest

from tests.warehouse_profile import WarehouseProfile


def test_integers_are_converted_to_strings():
    staging = WarehouseProfile(name="staging")
    staging.username = 5555
    assert staging.to_envvars() == {
        "WAREHOUSE_STAGING_HOST": "localhost",
        "WAREHOUSE_STAGING_USERNAME": "5555",
    }


@pytest.mark.parametrize("profile_is_live", [True, False])
def test_to_envvars_includes_parent_profile_setting(profile_is_live):
    staging = WarehouseProfile(
        name="staging",
        parent_name="production",
        profile_is_live=profile_is_live,
        values={"username": "hard-coded-staging-username"},
    )

    assert staging.to_envvars() == {
        "WAREHOUSE_STAGING_PARENT_PROFILE": "production",
        "WAREHOUSE_STAGING_HOST": "localhost",
        "WAREHOUSE_STAGING_USERNAME": "hard-coded-staging-username",
    }
