import pytest

from tests.warehouse_profile import WarehouseProfile


@pytest.mark.parametrize('profile_name', [
    'staging',
    None,
])
def test_const_values_set_on_frozen_profile_instance(profile_name, monkeypatch):
    wp = WarehouseProfile.get_instance(name=profile_name, values={
        'host': 'localhost.test',
        'username': 'test',
    })

    assert not wp.is_live
    assert wp.host == 'localhost.test'
    assert wp.username == 'test'
    assert wp.to_dict() == {
        WarehouseProfile.host: 'localhost.test',
        WarehouseProfile.username: 'test',
    }
