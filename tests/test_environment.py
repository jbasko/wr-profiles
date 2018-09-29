import os
from typing import Union

from tests.warehouse_profile import WarehouseProfile
from wr_profiles import EnvvarProfile


def test_create_environment_with_and_without_activation():
    wp: Union[WarehouseProfile, EnvvarProfile] = WarehouseProfile(name='for_this_test')

    original_values = wp.to_dict()

    env_with_activation = wp.create_env(username='example.username', password=None)

    assert env_with_activation == {
        'WAREHOUSE_PROFILE': 'for_this_test',
        'WAREHOUSE_FOR_THIS_TEST_HOST': 'localhost',
        'WAREHOUSE_FOR_THIS_TEST_USERNAME': 'example.username',
        'WAREHOUSE_FOR_THIS_TEST_PASSWORD': None,
    }

    env_without_activation = wp.create_env(username='example.username', password=None, include_activation=False)
    assert env_without_activation == {
        'WAREHOUSE_FOR_THIS_TEST_HOST': 'localhost',
        'WAREHOUSE_FOR_THIS_TEST_USERNAME': 'example.username',
        'WAREHOUSE_FOR_THIS_TEST_PASSWORD': None,
    }

    # The profile remains unchanged
    assert original_values == wp.to_dict()


def test_environment_content_is_determined_at_creation_time():
    wp: Union[WarehouseProfile, EnvvarProfile] = WarehouseProfile(name='creation')

    first = wp.create_env(username='first_username')
    second = wp.create_env(password='second_password')

    assert first['WAREHOUSE_CREATION_USERNAME'] == 'first_username'
    assert second['WAREHOUSE_CREATION_USERNAME'] is None

    assert first['WAREHOUSE_CREATION_PASSWORD'] is None
    assert second['WAREHOUSE_CREATION_PASSWORD'] == 'second_password'


def test_environment_applied(monkeypatch):
    wp: Union[WarehouseProfile, EnvvarProfile] = WarehouseProfile(name='env_test')

    outer_env = wp.create_env(username='outer_username', password=None)

    # Environment content is determined at the time of the creation.
    inner_env = wp.create_env(password='inner_password')

    assert wp.host == 'localhost'
    assert wp.username is None
    assert wp.password is None

    with outer_env.applied(monkeypatch):
        assert os.environ['WAREHOUSE_ENV_TEST_HOST'] == 'localhost'
        assert os.environ['WAREHOUSE_ENV_TEST_USERNAME'] == 'outer_username'
        assert 'WAREHOUSE_ENV_TEST_PASSWORD' not in os.environ

        assert wp.host == 'localhost'
        assert wp.username == 'outer_username'
        assert wp.password is None

        with inner_env.applied(monkeypatch):
            assert os.environ['WAREHOUSE_ENV_TEST_HOST'] == 'localhost'
            assert 'WAREHOUSE_ENV_TEST_USERNAME' not in os.environ
            assert os.environ['WAREHOUSE_ENV_TEST_PASSWORD'] == 'inner_password'

            assert wp.host == 'localhost'
            assert wp.username is None
            assert wp.password == 'inner_password'

        assert wp.host == 'localhost'
        assert wp.username == 'outer_username'
        assert wp.password is None

    assert wp.host == 'localhost'
    assert wp.username is None
    assert wp.password is None
