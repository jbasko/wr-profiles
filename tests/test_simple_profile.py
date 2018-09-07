from typing import TypeVar, Type, get_type_hints

from wr_profiles import Profile, Property


P = TypeVar('P')


def envvar_profile(profile_cls: Type[P]) -> Type[P]:
    dct = {
        "profile_root": profile_cls.profile_root,
    }

    property_names = []

    for cls in reversed(profile_cls.__mro__[:-1]):
        for k, v in get_type_hints(cls).items():
            dct[k] = Property(name=k, default=None)
            if k not in property_names:
                property_names.append(k)

    dct["_profile_property_names"] = property_names

    bases = []
    if not issubclass(profile_cls, Profile):
        bases.append(Profile)
    bases.append(profile_cls)

    return type("New" + profile_cls.__name__, tuple(bases), dct)


@envvar_profile
class WarehouseProfile:
    profile_root = "warehouse"

    host: str
    username: str
    password: str


print(WarehouseProfile._profile_property_names)


@envvar_profile
class WarehouseTestProfile(WarehouseProfile):
    report_email: str
    host: str = "localhost"


print(WarehouseTestProfile._profile_property_names)
print(WarehouseTestProfile.host)
