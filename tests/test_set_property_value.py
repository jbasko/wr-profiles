import pytest

from tests.warehouse_profile import WarehouseProfile
from wr_profiles import Property


@pytest.mark.parametrize('name,is_live', [
    ['staging', True],
    ['staging', False],
    [None, True],
    [None, False],
])
def test_sets_profile_property_value(name, is_live):
    profile = WarehouseProfile(name=name, is_live=is_live)

    with pytest.raises(Property.MissingValue):
        _ = profile.username  # noqa

    profile.username = 'the-new-username'
    assert profile.username == 'the-new-username'

    assert 'username' not in profile.__dict__
