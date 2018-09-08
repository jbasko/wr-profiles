import pytest

from tests.warehouse_profile import WarehouseProfile as WP
from wr_profiles.envvar_profile import EnvvarProfile

case_matrix = [
    [(None, None, True), {"parent_profile": None}],
    [(None, None, False), {"parent_profile": None}],
    [("staging", None, True), {"parent_profile": None}],
    [("staging", None, False), {"parent_profile": None}],
    [(None, "production", True), {"parent_profile": ("production", None, True)}],
    [(None, "production", False), {"parent_profile": ("production", None, False)}],
    [("staging", "production", True), {"parent_profile": ("production", None, True)}],
    [("staging", "production", False), {"parent_profile": ("production", None, False)}],
]


@pytest.mark.parametrize("case", case_matrix)
def test_parent_profile_initialisation(case):
    profile_name, parent_profile_name, profile_is_live = case[0]
    profile = WP(name=profile_name, parent_name=parent_profile_name, profile_is_live=profile_is_live)
    if case[1]["parent_profile"] is None:
        assert profile._profile_parent is None
    else:
        parent_profile_sig = (
            profile._profile_parent.profile_name,
            profile._profile_parent._profile_parent_name,
            profile._profile_parent.profile_is_live,
        )
        assert parent_profile_sig == case[1]["parent_profile"]


def test_profile_name(monkeypatch):
    monkeypatch.setenv("WAREHOUSE_PROFILE", "production")
    assert WP().profile_name == "production"
    assert WP(name="production").profile_name == "production"
    assert WP(profile_is_live=False).profile_name is None
    assert WP(parent_name="staging").profile_name == "production"
    assert WP(name="staging", profile_is_live=False).profile_name == "staging"


def test_parent_profile_name(monkeypatch):
    # this should be ignored by all because the base profile cannot have a parent profile
    monkeypatch.setenv("WAREHOUSE_PARENT_PROFILE", "illegal")

    monkeypatch.setenv("WAREHOUSE_STAGING_PARENT_PROFILE", "production")

    assert WP()._profile_parent_name is None
    assert WP()._profile_parent is None

    assert WP(name="production")._profile_parent_name is None
    assert WP(name="production")._profile_parent is None

    assert WP(name="production", profile_is_live=False)._profile_parent_name is None
    assert WP(name="production", profile_is_live=False)._profile_parent is None

    assert WP(name="staging")._profile_parent_name == "production"
    assert WP(name="staging")._profile_parent.profile_name == "production"

    assert WP(name="staging", profile_is_live=False)._profile_parent_name is None
    assert WP(name="staging", profile_is_live=False)._profile_parent is None


def test_loaders():
    assert WP()._loader is EnvvarProfile._profile_loaders["live"]
    assert WP(profile_is_live=False)._loader is EnvvarProfile._profile_loaders["frozen"]


def test_to_dict():
    assert WP().to_dict() == {"host": "localhost", "username": None, "password": None}
    assert WP(profile_is_live=False).to_dict() == {"host": "localhost", "username": None, "password": None}
