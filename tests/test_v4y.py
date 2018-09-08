from typing import get_type_hints

from wr_profiles.envvar_profile import envvar_profile, SimpleProfile, SimpleProfileProperty


@envvar_profile
class Warehouse:
    host: str = "localhost"
    username: str
    password: str


@envvar_profile
class WarehouseTest(Warehouse):
    report_email: str
    host: str = "test.localhost"


def test_end_to_end(monkeypatch):
    warehouse = Warehouse()

    assert isinstance(warehouse, SimpleProfile)
    assert Warehouse.profile_root == "warehouse"
    assert Warehouse.profile_properties == ["host", "username", "password"]

    assert Warehouse.host.default == "localhost"
    assert Warehouse.host.type_ is str
    assert Warehouse.username.default is None
    assert Warehouse.username.type_ is str
    assert Warehouse.password.default is None
    assert Warehouse.password.type_ is str

    assert warehouse.host == "localhost"
    assert warehouse.username is None
    assert warehouse.password is None

    assert list(warehouse) == ["host", "username", "password"]
    assert dict(warehouse) == {"host": "localhost", "username": None, "password": None}

    assert warehouse.profile_is_active
    assert warehouse.profile_is_live

    assert warehouse.to_envvars() == {
        "WAREHOUSE_HOST": "localhost",
    }

    monkeypatch.setenv("WAREHOUSE_USERNAME", "root")
    assert warehouse.username == "root"
    assert warehouse.to_envvars() == {
        "WAREHOUSE_HOST": "localhost",
        "WAREHOUSE_USERNAME": "root",
    }

    monkeypatch.setenv("WAREHOUSE_SANDBOX_USERNAME", "sandbox-user")
    monkeypatch.setenv("WAREHOUSE_PROFILE", "int")
    monkeypatch.setenv("WAREHOUSE_INT_PASSWORD", "int-password")
    assert warehouse.to_dict() == {
        "host": "localhost", "username": None, "password": "int-password",
    }

    monkeypatch.setenv("WAREHOUSE_INT_PARENT_PROFILE", "sandbox")
    assert warehouse.to_dict() == {
        "host": "localhost", "username": "sandbox-user", "password": "int-password",
    }

    sandbox = warehouse.load("sandbox")
    assert sandbox.username == "sandbox-user"
    assert sandbox.host == "localhost"


def test_inheritance():
    assert WarehouseTest.profile_properties == ["host", "username", "password", "report_email"]
    assert WarehouseTest.host.default == "test.localhost"
    assert WarehouseTest.host.type_ is str
    assert WarehouseTest.username.default is None
    assert WarehouseTest.username.type_ is str
    assert WarehouseTest.password.default is None
    assert WarehouseTest.password.type_ is str

    warehouse = WarehouseTest()
    assert warehouse.host == "test.localhost"

    assert warehouse.profile_is_active
    assert warehouse.profile_is_live

    assert warehouse.to_envvars() == {
        "WAREHOUSE_HOST": "test.localhost"
    }


def test_initialisation():
    class Original:
        a: str = "a_default"
        b: str = None

    assert get_type_hints(Original) == {"a": str, "b": str}

    DecoratedOriginal = envvar_profile(Original)

    assert issubclass(DecoratedOriginal, SimpleProfile)
    assert DecoratedOriginal.profile_properties == ["a", "b"]
    assert DecoratedOriginal.a.default == "a_default"
    assert DecoratedOriginal.a.type_ is str
    assert DecoratedOriginal.b.default is None
    assert DecoratedOriginal.a.type_ is str

    class Derived(DecoratedOriginal):
        b: str = "b_default"
        c: str = None

    assert Derived.profile_properties == ["a", "b"]
    assert Derived.b == "b_default"
    assert Derived.c is None

    DecoratedDerived = envvar_profile(Derived)

    assert DecoratedDerived.profile_properties == ["a", "b", "c"]

    assert isinstance(DecoratedDerived.b, SimpleProfileProperty)
    assert DecoratedDerived.b.name == "b"
    assert DecoratedDerived.b.default == "b_default"
    assert DecoratedDerived.b.type_ is str

    assert isinstance(DecoratedDerived.c, SimpleProfileProperty)
    assert DecoratedDerived.c.name == "c"
    assert DecoratedDerived.c.default is None
    assert DecoratedDerived.c.type_ is str

    assert isinstance(DecoratedDerived.a, SimpleProfileProperty)
    assert DecoratedDerived.a.name == "a"
    assert DecoratedDerived.a.default == "a_default"
    assert DecoratedDerived.a.type_ is str

    class DoubleDerived(DecoratedDerived):
        d: str = None

    assert DoubleDerived.profile_properties == ["a", "b", "c"]

    DecoratedDoubleDerived = envvar_profile(DoubleDerived)
    assert DecoratedDoubleDerived.profile_properties == ["a", "b", "c", "d"]

    assert DecoratedDoubleDerived.a.default == "a_default"
    assert DecoratedDoubleDerived.b.default == "b_default"
    assert DecoratedDoubleDerived.c.default is None
    assert DecoratedDoubleDerived.d.default is None
