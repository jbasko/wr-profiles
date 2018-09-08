from typing import get_type_hints

from wr_profiles.envvar_profile import EnvvarProfile, EnvvarProfileProperty, envvar_profile, envvar_profile_cls


@envvar_profile_cls
class Warehouse:
    host: str = "localhost"
    username: str
    password: str


@envvar_profile_cls
class WarehouseTest(Warehouse):
    report_email: str
    host: str = "test.localhost"


def test_initialisation():
    class Original:
        a: str = "a_default"
        b: str = None
        c: str

    assert get_type_hints(Original) == {"a": str, "b": str, "c": str}
    assert Original.a == "a_default"
    assert Original.b is None
    assert not hasattr(Original, "c")

    DecoratedOriginal = envvar_profile_cls(Original)

    assert issubclass(DecoratedOriginal, EnvvarProfile)
    assert DecoratedOriginal.profile_root == "original"
    assert DecoratedOriginal.profile_properties == ["a", "b", "c"]
    assert DecoratedOriginal.a == EnvvarProfileProperty("a", "a_default", str)
    assert DecoratedOriginal.b == EnvvarProfileProperty("b", None, str)
    assert DecoratedOriginal.c == EnvvarProfileProperty("c", None, str)

    class Derived(DecoratedOriginal):
        b: str = "b_default"
        d: str = None
        e: str

    assert Derived.profile_properties == ["a", "b", "c"]
    assert Derived.b == "b_default"
    assert Derived.d is None
    assert not hasattr(Derived, "e")

    DecoratedDerived = envvar_profile_cls(Derived)
    assert DecoratedDerived.profile_root == "derived"
    assert DecoratedDerived.profile_properties == ["a", "b", "c", "d", "e"]

    assert DecoratedDerived.a == EnvvarProfileProperty("a", "a_default", str)
    assert DecoratedDerived.b == EnvvarProfileProperty("b", "b_default", str)
    assert DecoratedDerived.c == EnvvarProfileProperty("c", None, str)
    assert DecoratedDerived.d == EnvvarProfileProperty("d", None, str)
    assert DecoratedDerived.e == EnvvarProfileProperty("e", None, str)

    assert isinstance(DecoratedDerived.c, EnvvarProfileProperty)
    assert DecoratedDerived.c.name == "c"
    assert DecoratedDerived.c.default is None
    assert DecoratedDerived.c.type_ is str

    assert isinstance(DecoratedDerived.a, EnvvarProfileProperty)
    assert DecoratedDerived.a.name == "a"
    assert DecoratedDerived.a.default == "a_default"
    assert DecoratedDerived.a.type_ is str

    class DoubleDerived(DecoratedDerived):
        f: str = None

    assert DoubleDerived.profile_properties == ["a", "b", "c", "d", "e"]

    DecoratedDoubleDerived = envvar_profile_cls(DoubleDerived)
    assert DecoratedDoubleDerived.profile_root == "double_derived"
    assert DecoratedDoubleDerived.profile_properties == ["a", "b", "c", "d", "e", "f"]

    assert DecoratedDoubleDerived.a == EnvvarProfileProperty("a", "a_default", str)
    assert DecoratedDoubleDerived.b == EnvvarProfileProperty("b", "b_default", str)
    assert DecoratedDoubleDerived.c == EnvvarProfileProperty("c", None, str)
    assert DecoratedDoubleDerived.d == EnvvarProfileProperty("d", None, str)
    assert DecoratedDoubleDerived.e == EnvvarProfileProperty("e", None, str)
    assert DecoratedDoubleDerived.f == EnvvarProfileProperty("f", None, str)


def test_profile_activating_envvar():
    @envvar_profile_cls
    class Letters:
        profile_activating_envvar = "THE_PROFILE"

        a: str = None
        b: str = None

    assert Letters()._active_profile_name_envvar == "THE_PROFILE"


def test_end_to_end(monkeypatch):
    warehouse = Warehouse()

    assert isinstance(warehouse, EnvvarProfile)
    assert warehouse.profile_is_active
    assert warehouse.profile_is_live

    assert warehouse.host == "localhost"
    assert warehouse.username is None
    assert warehouse.password is None

    assert list(warehouse) == ["host", "username", "password"]
    assert dict(warehouse) == {"host": "localhost", "username": None, "password": None}

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
    warehouse = WarehouseTest()
    assert warehouse.host == "test.localhost"

    assert warehouse.profile_is_active
    assert warehouse.profile_is_live

    assert warehouse.to_envvars() == {
        "WAREHOUSE_TEST_HOST": "test.localhost"
    }


def test_create_inline_envvar_profile():
    profile = envvar_profile(
        profile_root="letters",
        profile_properties={
            "a": "A",
            "b": None,
        },
    )
    assert isinstance(profile, EnvvarProfile)
    assert profile.a == "A"
    assert profile.b is None
    assert profile.profile_properties == ["a", "b"]
    assert profile.profile_root == "letters"
    assert profile.to_dict() == {
        "a": "A",
        "b": None,
    }
    assert profile.to_envvars() == {
        "LETTERS_A": "A",
    }


def test_create_inline_envvar_profile_with_properties_as_kwargs():
    profile = envvar_profile("warehouse", host="localhost", username=None, password=None)
    assert profile.profile_root == "warehouse"
    assert profile._active_profile_name_envvar == "WAREHOUSE_PROFILE"
    assert profile.profile_properties == ["host", "username", "password"]
    assert profile.host == "localhost"
    assert profile.username is None
    assert profile.password is None


def test_pass_profile_params_to_class_decorator():
    @envvar_profile_cls(profile_root="the_letters", profile_activating_envvar="LETTERS_PROFILE")
    class Letters:
        a: str = "A"
        b: str

    assert issubclass(Letters, EnvvarProfile)
    assert Letters.profile_root == "the_letters"
    assert Letters.profile_properties == ["a", "b"]
    assert Letters()._active_profile_name_envvar == "LETTERS_PROFILE"
