import os

import pytest

from wr_profiles import Profile, Property


class WarehouseProfile(Profile):
    profile_root = 'warehouse'
    host = Property('host', default='<unknown>')
    user = Property('user')


warehouse_profile = WarehouseProfile()


def test_property_with_default_value(monkeypatch):
    monkeypatch.delenv('WAREHOUSE_PROFILE', raising=False)

    assert warehouse_profile.profile_name is None
    assert warehouse_profile.host == '<unknown>'

    monkeypatch.setenv('WAREHOUSE_HOST', 'host.example')
    assert warehouse_profile.host == 'host.example'

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'dummy')
    assert warehouse_profile.profile_name == 'dummy'
    assert warehouse_profile.host == '<unknown>'

    monkeypatch.setenv('WAREHOUSE_DUMMY_HOST', 'dummy.example')
    assert warehouse_profile.host == 'dummy.example'

    monkeypatch.setenv('WAREHOUSE_PROFILE', '')
    assert warehouse_profile.profile_name is None
    assert warehouse_profile.host == 'host.example'


def test_property_without_default_value(monkeypatch):
    monkeypatch.delenv('WAREHOUSE_USER', raising=False)

    with pytest.raises(KeyError):
        assert not warehouse_profile.user

    monkeypatch.setenv('WAREHOUSE_USER', 'root')
    assert warehouse_profile.user == 'root'

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'dummy')
    with pytest.raises(KeyError):
        assert not warehouse_profile.user

    monkeypatch.setenv('WAREHOUSE_DUMMY_USER', 'dummy')
    assert warehouse_profile.user == 'dummy'


def test_has_prop():
    assert warehouse_profile.has_prop('host')
    assert warehouse_profile.has_prop('user')
    assert not warehouse_profile.has_prop('USER')
    assert not warehouse_profile.has_prop('something_else')


def test_props():
    class ExpiringWarehouseProfile(WarehouseProfile):
        time_to_live = Property('time_to_live', default=7)

    expiring_profile = ExpiringWarehouseProfile()
    props = set(expiring_profile.props)
    assert len(props) == 3
    assert props == {
        ExpiringWarehouseProfile.host, ExpiringWarehouseProfile.user, ExpiringWarehouseProfile.time_to_live
    }


def test_load_custom(monkeypatch):
    monkeypatch.setenv('WAREHOUSE_USER', 'default-user')
    monkeypatch.setenv('WAREHOUSE_DUMMY_USER', 'dummy-user')

    assert warehouse_profile.user == 'default-user'

    dummy_warehouse = warehouse_profile.load_custom('dummy')
    assert isinstance(dummy_warehouse, WarehouseProfile)
    assert dummy_warehouse is not warehouse_profile
    assert dummy_warehouse.profile_name == 'dummy'
    assert dummy_warehouse.is_frozen
    assert dummy_warehouse.host == '<unknown>'
    assert dummy_warehouse.user == 'dummy-user'

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'dummy')
    monkeypatch.setenv('WAREHOUSE_DUMMY_USER', 'dummy-user-updated')

    assert warehouse_profile.user == 'dummy-user-updated'  # live profile
    assert dummy_warehouse.user == 'dummy-user'  # frozen profile

    another_warehouse = warehouse_profile.load_custom('another')
    assert another_warehouse._values == {
        'host': '<unknown>',
    }


def test_to_dict(monkeypatch):
    assert warehouse_profile.to_dict(include_defaults=False) == {}
    assert warehouse_profile.to_dict() == {'host': '<unknown>'}

    monkeypatch.setenv('WAREHOUSE_USER', 'johnny')
    assert warehouse_profile.to_dict(include_defaults=False) == {'user': 'johnny'}
    assert warehouse_profile.to_dict() == {'host': '<unknown>', 'user': 'johnny'}

    monkeypatch.setenv('WAREHOUSE_HOST', 'j.example')
    assert warehouse_profile.to_dict(include_defaults=False) == {'user': 'johnny', 'host': 'j.example'}
    assert warehouse_profile.to_dict() == {'host': 'j.example', 'user': 'johnny'}

    monkeypatch.setenv('WAREHOUSE_DUMMY_USER', 'dummy')
    dummy = warehouse_profile.load_custom('dummy')
    # host '<unknown>' is no longer just a default
    assert dummy.to_dict(include_defaults=False) == {'host': '<unknown>', 'user': 'dummy'}

    monkeypatch.setenv('WAREHOUSE_DUMMY_USER', 'remy')
    assert dummy.to_dict(include_defaults=False) == {'host': '<unknown>', 'user': 'dummy'}  # unchanged


def test_is_frozen_and_is_active(monkeypatch):
    dummy_profile = warehouse_profile.load_custom('dummy')

    assert not warehouse_profile.is_frozen
    assert warehouse_profile.is_active

    assert dummy_profile.is_frozen
    assert not dummy_profile.is_active

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'dummy')
    assert not warehouse_profile.is_frozen
    assert dummy_profile.is_frozen
    assert warehouse_profile.is_active
    assert dummy_profile.is_active

    monkeypatch.setenv('WAREHOUSE_PROFILE', '')
    assert not warehouse_profile.is_frozen
    assert dummy_profile.is_frozen
    assert warehouse_profile.is_active
    assert not dummy_profile.is_active


def test_custom_profile_can_load_another_custom_profile(monkeypatch):
    monkeypatch.setenv('WAREHOUSE_DUMMY_HOST', 'dummy-host')
    monkeypatch.setenv('WAREHOUSE_NEW_USER', 'new-user')

    dummy = warehouse_profile.load_custom('dummy')
    new = warehouse_profile.load_custom('new')

    assert not dummy.is_active
    assert dummy.host == 'dummy-host'

    assert not new.is_active
    assert new.host == '<unknown>'
    assert new.user == 'new-user'

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'new')
    assert not dummy.is_active
    assert new.is_active


@pytest.mark.parametrize('profile_cls', [
    type('WithoutRoot', (Profile,), {}),
    type('EmptyRoot', (Profile,), {'profile_root': ''}),
    type('UnderscoreRoot', (Profile,), {'profile_root': '_'}),
    type('DoubleUnderscoreRoot', (Profile,), {'profile_root': '__'}),
    type('BadUnderscoresRoot', (Profile,), {'profile_root': '_a_'}),
    type('AsSpace', (Profile,), {'profile_root': ' '}),
    type('WithSpaces', (Profile,), {'profile_root': 'a b'}),
])
def test_raises_value_error_on_invalid_profile_root(profile_cls):
    with pytest.raises(ValueError) as exc_info:
        profile_cls()

    assert 'profile_root' in str(exc_info.value)


@pytest.mark.parametrize('profile_name', [
    '_',
    '_a_',
    '__',
    '__a',
    'a__',
    ' ',
    '  ',
    'a b',
])
def test_raises_value_error_on_invalid_profile_name(profile_name):
    with pytest.raises(ValueError) as exc_info:
        WarehouseProfile(_frozen_name=profile_name, _active_profile=warehouse_profile)

    assert 'name' in str(exc_info.value)


def test_export(monkeypatch):
    assert warehouse_profile.export() == {'WAREHOUSE_HOST': '<unknown>'}
    assert warehouse_profile.export(include_defaults=False) == {}

    monkeypatch.setenv('WAREHOUSE_USER', 'root')
    monkeypatch.setenv('WAREHOUSE_DUMMY_HOST', 'dummy.example')

    dummy = warehouse_profile.load_custom('dummy')

    assert warehouse_profile.export() == {'WAREHOUSE_HOST': '<unknown>', 'WAREHOUSE_USER': 'root'}
    assert dummy.export() == {'WAREHOUSE_DUMMY_HOST': 'dummy.example'}


def test_set_prop_value_on_frozen_profile(monkeypatch):
    # Create a new instance because set_prop_value has long-lasting effect
    warehouse_profile = WarehouseProfile()

    dummy = warehouse_profile.load_custom('dummy')

    with pytest.raises(KeyError) as exc_info:
        dummy.set_prop_value('nonexistent', 'does not matter')
    assert str(exc_info.value) == "'nonexistent'"

    dummy.set_prop_value('host', 'dummy.example')
    assert dummy.host == 'dummy.example'

    assert warehouse_profile.host == '<unknown>'

    monkeypatch.setenv('WAREHOUSE_PROFILE', 'dummy')
    assert warehouse_profile.host == '<unknown>'  # because the prop value was set in the frozen profile

    os.environ.update(dummy.export())
    assert warehouse_profile.host == 'dummy.example'


def test_set_prop_value_on_non_frozen_profile(monkeypatch):
    # Create a new instance because set_prop_value has long-lasting effect
    warehouse_profile = WarehouseProfile()

    assert not warehouse_profile.is_frozen

    warehouse_profile.set_prop_value('host', 'test.localhost')
    assert warehouse_profile.host == 'test.localhost'

    monkeypatch.setenv('WAREHOUSE_HOST', 'ignored.localhost')
    assert warehouse_profile.host == 'test.localhost'

    assert warehouse_profile.to_dict() == {'host': 'test.localhost'}
