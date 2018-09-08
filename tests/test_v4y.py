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
        "WAREHOUSE_TEST_HOST": "test.localhost"
    }


def test_initialisation():
    class Original:
        a: str = "a_default"
        b: str = None
        c: str

    assert get_type_hints(Original) == {"a": str, "b": str, "c": str}
    assert Original.a == "a_default"
    assert Original.b is None
    assert not hasattr(Original, "c")

    DecoratedOriginal = envvar_profile(Original)

    assert issubclass(DecoratedOriginal, SimpleProfile)
    assert DecoratedOriginal.profile_properties == ["a", "b", "c"]
    assert DecoratedOriginal.a == SimpleProfileProperty("a", "a_default", str)
    assert DecoratedOriginal.b == SimpleProfileProperty("b", None, str)
    assert DecoratedOriginal.c == SimpleProfileProperty("c", None, str)

    class Derived(DecoratedOriginal):
        b: str = "b_default"
        d: str = None
        e: str

    assert Derived.profile_properties == ["a", "b", "c"]
    assert Derived.b == "b_default"
    assert Derived.d is None
    assert not hasattr(Derived, "e")

    DecoratedDerived = envvar_profile(Derived)

    assert DecoratedDerived.profile_properties == ["a", "b", "c", "d", "e"]

    assert DecoratedDerived.a == SimpleProfileProperty("a", "a_default", str)
    assert DecoratedDerived.b == SimpleProfileProperty("b", "b_default", str)
    assert DecoratedDerived.c == SimpleProfileProperty("c", None, str)
    assert DecoratedDerived.d == SimpleProfileProperty("d", None, str)
    assert DecoratedDerived.e == SimpleProfileProperty("e", None, str)

    assert isinstance(DecoratedDerived.c, SimpleProfileProperty)
    assert DecoratedDerived.c.name == "c"
    assert DecoratedDerived.c.default is None
    assert DecoratedDerived.c.type_ is str

    assert isinstance(DecoratedDerived.a, SimpleProfileProperty)
    assert DecoratedDerived.a.name == "a"
    assert DecoratedDerived.a.default == "a_default"
    assert DecoratedDerived.a.type_ is str

    class DoubleDerived(DecoratedDerived):
        f: str = None

    assert DoubleDerived.profile_properties == ["a", "b", "c", "d", "e"]

    DecoratedDoubleDerived = envvar_profile(DoubleDerived)
    assert DecoratedDoubleDerived.profile_properties == ["a", "b", "c", "d", "e", "f"]

    assert DecoratedDoubleDerived.a == SimpleProfileProperty("a", "a_default", str)
    assert DecoratedDoubleDerived.b == SimpleProfileProperty("b", "b_default", str)
    assert DecoratedDoubleDerived.c == SimpleProfileProperty("c", None, str)
    assert DecoratedDoubleDerived.d == SimpleProfileProperty("d", None, str)
    assert DecoratedDoubleDerived.e == SimpleProfileProperty("e", None, str)
    assert DecoratedDoubleDerived.f == SimpleProfileProperty("f", None, str)
