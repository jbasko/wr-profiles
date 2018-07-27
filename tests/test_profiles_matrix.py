import pytest

from tests.warehouse_profile import WarehouseProfile as WP
from wr_profiles import Profile

case_matrix = [
    [
        (None, None, True),
        {
            'parent_profile': None,
        },
    ],
    [
        (None, None, False),
        {
            'parent_profile': None,
        },
    ],
    [
        ('staging', None, True),
        {
            'parent_profile': None,
        },
    ],
    [
        ('staging', None, False),
        {
            'parent_profile': None,
        },
    ],
    [
        (None, 'production', True),
        {
            'parent_profile': ('production', None, True),
        },
    ],
    [
        (None, 'production', False),
        {
            'parent_profile': ('production', None, False),
        },
    ],
    [
        ('staging', 'production', True),
        {
            'parent_profile': ('production', None, True),
        },
    ],
    [
        ('staging', 'production', False),
        {
            'parent_profile': ('production', None, False),
        },
    ],
]


@pytest.mark.parametrize('case', case_matrix)
def test_parent_profile_initialisation(case):
    profile_name, parent_profile_name, is_live = case[0]
    profile = WP(name=profile_name, parent_name=parent_profile_name, is_live=is_live)
    if case[1]['parent_profile'] is None:
        assert profile.parent_profile is None
    else:
        parent_profile_sig = (
            profile.parent_profile.profile_name,
            profile.parent_profile.parent_profile_name,
            profile.parent_profile.is_live,
        )
        assert parent_profile_sig == case[1]['parent_profile']


def test_profile_name(monkeypatch):
    monkeypatch.setenv('WAREHOUSE_PROFILE', 'production')
    assert WP().profile_name == 'production'
    assert WP(name='production').profile_name == 'production'
    assert WP(is_live=False).profile_name is None
    assert WP(parent_name='staging').profile_name == 'production'
    assert WP(name='staging', is_live=False).profile_name == 'staging'


def test_parent_profile_name(monkeypatch):
    # this should be ignored by all because the base profile cannot have a parent profile
    monkeypatch.setenv('WAREHOUSE_PARENT_PROFILE', 'illegal')

    monkeypatch.setenv('WAREHOUSE_STAGING_PARENT_PROFILE', 'production')

    assert WP().parent_profile_name is None
    assert WP().parent_profile is None

    assert WP(name='production').parent_profile_name is None
    assert WP(name='production').parent_profile is None

    assert WP(name='production', is_live=False).parent_profile_name is None
    assert WP(name='production', is_live=False).parent_profile is None

    assert WP(name='staging').parent_profile_name == 'production'
    assert WP(name='staging').parent_profile.profile_name == 'production'

    assert WP(name='staging', is_live=False).parent_profile_name is None
    assert WP(name='staging', is_live=False).parent_profile is None


def test_loaders():
    assert WP().loader is Profile._profile_loaders['live']
    assert WP(is_live=False).loader is Profile._profile_loaders['frozen']


def test_to_dict():
    assert WP().to_dict() == {WP.host: 'localhost'}
    assert WP(is_live=False).to_dict() == {WP.host: 'localhost'}
