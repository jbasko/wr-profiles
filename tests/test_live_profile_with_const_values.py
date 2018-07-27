import pytest

from tests.warehouse_profile import WarehouseProfile


@pytest.mark.parametrize('profile_name', [
    'staging',
    None,
])
def test_const_values_set_on_live_profile_instance_override_envvars(profile_name, monkeypatch):
    wp = WarehouseProfile(name=profile_name, is_live=True, values={
        'host': 'localhost.test',
        'username': 'test',
    })

    assert wp.is_live
    assert wp.host == 'localhost.test'
    assert wp.username == 'test'
    assert wp.to_dict() == {
        WarehouseProfile.host: 'localhost.test',
        WarehouseProfile.username: 'test',
    }

    monkeypatch.setenv(WarehouseProfile.host.get_envvar(wp), 'ignored-host')
    monkeypatch.setenv(WarehouseProfile.password.get_envvar(wp), 'not-ignored-password')

    assert wp.host == 'localhost.test'
    assert wp.password == 'not-ignored-password'
