from pathlib import Path

import pytest

from tests.warehouse_profile import WarehouseProfile
from wr_profiles import Profile, Property


class UploaderProfile(Profile):
    profile_root = 'uploader'

    root_dir = Property('root_dir', default=Path('/'))
    user = Property('user')

    enabled = Property('enabled', default=False)

    @enabled.deserializer
    def enabled(self, value):
        if isinstance(value, bool):
            return value
        return value and value[0].lower()[0] in ('y', 't', '1')

    @enabled.serializer
    def enabled(self, value):
        if value:
            return str(value).lower()[0]
        return '0'


uploader_profile = UploaderProfile()


def test_all(monkeypatch):
    assert isinstance(UploaderProfile.root_dir, Property)
    assert UploaderProfile.root_dir.name == 'root_dir'

    assert uploader_profile.root_dir == Path('/')

    with pytest.raises(Property.MissingValue):
        assert not uploader_profile.user

    monkeypatch.setenv('UPLOADER_USER', 'uploader')
    assert uploader_profile.user == 'uploader'

    assert uploader_profile.enabled is False
    assert uploader_profile.to_envvars() == {
        'UPLOADER_USER': 'uploader',
        'UPLOADER_ROOT_DIR': '/',
        'UPLOADER_ENABLED': '0',
    }

    monkeypatch.setenv('UPLOADER_ENABLED', 'yes')
    assert uploader_profile.enabled is True
    assert uploader_profile.to_envvars() == {
        'UPLOADER_USER': 'uploader',
        'UPLOADER_ROOT_DIR': '/',
        'UPLOADER_ENABLED': 't',
    }


def test_integers_are_converted_to_strings():
    staging = WarehouseProfile(name='staging')
    staging.username = 5555
    assert staging.to_envvars() == {
        'WAREHOUSE_STAGING_HOST': 'localhost',
        'WAREHOUSE_STAGING_USERNAME': '5555',
    }


@pytest.mark.parametrize('is_live', [
    True,
    False,
])
def test_to_envvars_includes_parent_profile_setting(is_live):
    staging = WarehouseProfile(name='staging', parent_name='production', is_live=is_live, values={
        'username': 'hard-coded-staging-username',
    })

    assert staging.to_envvars() == {
        'WAREHOUSE_STAGING_PARENT_PROFILE': 'production',
        'WAREHOUSE_STAGING_HOST': 'localhost',
        'WAREHOUSE_STAGING_USERNAME': 'hard-coded-staging-username',
    }
