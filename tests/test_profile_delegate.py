from tests.warehouse_profile import WarehouseProfile


def test_profile_delegate_as_property(monkeypatch):
    the_profile = WarehouseProfile(name="p1")

    class WarehouseConfig(WarehouseProfile):
        @property
        def profile_delegate(self):
            return the_profile

        # NB! In this case when the profile object is available at class declaration time
        # the above could also be expressed with just:
        # profile_delegate = the_profile

        @property
        def profile(self):
            return the_profile

        @property
        def username(self):
            return self.profile.username or "root"

    config = WarehouseConfig()
    assert config.profile_name == "p1"
    assert config.username == "root"
    assert config.host == "localhost"

    monkeypatch.setenv("WAREHOUSE_P1_HOST", "p1.host")
    assert config.host == "p1.host"
    assert config["host"] == "p1.host"
