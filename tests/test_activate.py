import pytest

from tests.warehouse_profile import WarehouseProfile


@pytest.mark.parametrize('profile_name', [
    'staging',
    None,
])
def test_activates_live_profile(profile_name):
    wp = WarehouseProfile()

    instance = WarehouseProfile(name=profile_name)
    instance.activate()

    assert wp.active_profile_name == profile_name
    assert instance.is_active


@pytest.mark.parametrize('profile_name', [
    'staging',
    None,
])
def test_activates_frozen_profile(profile_name):
    wp = WarehouseProfile()

    instance = WarehouseProfile(name=profile_name, is_live=False)
    instance.activate()

    assert instance.is_active
    assert wp.active_profile_name == profile_name


def test_activates_named_profile():
    wp = WarehouseProfile()

    wp.activate('staging')
    assert wp.active_profile_name == 'staging'

    wp.activate('production')
    assert wp.active_profile_name == 'production'

    wp.activate(None)
    assert wp.active_profile_name is None
