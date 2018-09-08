import collections.abc
import os
import re
import typing
from abc import ABC, abstractmethod

P = typing.TypeVar("P")
PROFILE_NAME_COMPONENT_REGEX = re.compile(r"^[a-z]([\d\w]*[a-z0-9])?$")


NotSet = object()


class EnvvarProfileProperty:
    def __init__(self, name, default=None, type_=None):
        self.name = name
        self.default = default
        self.type_ = type_

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance._get_prop_value(self)

    def __set__(self, instance, value):
        instance._set_prop_value(self, value)

    def __str__(self):
        return "{}({!r})".format(self.__class__.__name__, self.name)

    def __repr__(self):
        return "{}({!r})".format(self.__class__.__name__, self.name)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def get_envvar(self, profile):
        assert self.name
        return "{}{}".format(profile._envvar_prefix, self.name.upper())

    def from_str(self, profile: "EnvvarProfile", value: str):
        return value

    def to_str(self, profile: "EnvvarProfile", value: typing.Any) -> typing.Union[str, None]:
        if value is None:
            return None
        else:
            return str(value)


class ProfileLoader(ABC):
    """
    Base class for profile loaders.
    """

    @abstractmethod
    def load(self, profile):
        pass

    @abstractmethod
    def has_prop_value(self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty]) -> bool:
        pass

    @abstractmethod
    def get_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], default: typing.Any = NotSet
    ) -> typing.Any:
        pass

    @abstractmethod
    def set_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], value: typing.Any
    ):
        pass


class LiveProfileLoader(ProfileLoader):
    def set_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], value: typing.Any
    ):
        prop = profile._get_prop(prop)
        os.environ[prop.get_envvar(profile)] = prop.to_str(profile, value)

    def has_prop_value(self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty]) -> bool:
        prop = profile._get_prop(prop)
        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return True
            prop_envvar = prop.get_envvar(check_profile)
            if prop_envvar in os.environ:
                return True

        return False

    def get_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], default: typing.Any = NotSet
    ) -> typing.Any:
        prop = profile._get_prop(prop)

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return check_profile._const_values[prop.name]

        for check_profile in profile._get_profile_tree():
            prop_envvar = prop.get_envvar(check_profile)
            if prop_envvar in os.environ:
                return prop.from_str(check_profile, os.environ[prop_envvar])

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_defaults:
                return check_profile._const_defaults[prop.name]

        if default is not NotSet:
            return default

        return prop.default

    def load(self, profile):
        # Nothing to do -- live profile does not need to be reloaded.
        pass


class FrozenProfileLoader(ProfileLoader):
    def set_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], value: typing.Any
    ):
        prop = profile._get_prop(prop)
        profile._const_values[prop.name] = value

    def has_prop_value(self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty]) -> bool:
        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return True

        return False

    def get_prop_value(
        self, profile: "EnvvarProfile", prop: typing.Union[str, EnvvarProfileProperty], default: typing.Any = NotSet
    ) -> typing.Any:
        prop = profile._get_prop(prop)

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return check_profile._const_values[prop.name]

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_defaults:
                return check_profile._const_defaults[prop.name]

        if default is not NotSet:
            return default

        return prop.default

    def load(self, profile):
        # Create a live clone of itself and load all props.
        live_clone = profile.__class__(
            name=profile.profile_name,
            parent_name=profile._profile_parent_name,
            profile_is_live=True,
            values=profile._const_values,
        )

        values = {}
        for prop_name in profile.profile_properties:
            prop = profile._get_prop(prop_name)
            if live_clone.has_prop_value(prop):
                values[prop.name] = live_clone._get_prop_value(prop_name)

        profile._const_values = values


class EnvvarProfile(collections.abc.Mapping):
    """
    Represents a set of configuration values backed by environment variables.
    """

    profile_root: str = None

    # Defaults to "<profile_root>_PROFILE".
    # You should set this only when you extend your own Profile classes to customise them
    # and you want to activate the extended profile with an envvar that does not conflict
    # with the parent profile.
    profile_activating_envvar: str = None

    # List of profile property names
    profile_properties: typing.List[str] = None

    # shared loaders
    _profile_loaders: typing.Dict[str, ProfileLoader] = {}

    def __init__(
        self,
        *,
        name=None,
        parent_name=None,
        profile_is_live=True,
        values=None,
        defaults=None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self._const_name = name
        self._const_parent_name = parent_name
        self._const_is_live = profile_is_live

        self._const_values = {}
        if values is not None:
            self._const_values.update(values)

        self._const_defaults = {}
        if defaults is not None:
            self._const_defaults.update(defaults)

        if not self.profile_root:
            raise ValueError(
                f"{self.__class__.__name__}.profile_root is required"
            )

        if not PROFILE_NAME_COMPONENT_REGEX.match(self.profile_root):
            raise ValueError(
                f"{self.__class__.__name__}.profile_root {self.profile_root!r} is invalid"
            )

    @classmethod
    def load(
        cls, name=None, parent_name=None, profile_is_live=False, values=None, defaults=None
    ) -> "EnvvarProfile":
        """
        Get a loaded frozen instance of a specific profile.
        """
        instance = cls(
            name=name,
            parent_name=parent_name,
            profile_is_live=profile_is_live,
            values=values,
            defaults=defaults,
        )
        instance._do_load()
        return instance

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self.profile_properties)

    def __getitem__(self, name):
        return self._get_prop_value(name)

    def __len__(self):
        return len(self.profile_properties)

    @property
    def _envvar_prefix(self):
        if self.profile_name:
            return f"{self.profile_root}_{self.profile_name}_".upper()
        return f"{self.profile_root}_".upper()

    @property
    def _profile_parent_name(self) -> typing.Optional[str]:
        if self._const_parent_name:
            return self._const_parent_name
        elif not self.profile_is_live:
            return None
        elif self.profile_name:
            return os.environ.get(f"{self._envvar_prefix}PARENT_PROFILE", None)
        else:
            return None

    @property
    def profile_name(self) -> typing.Optional[str]:
        if self._const_name:
            return self._const_name
        elif not self.profile_is_live:
            return None
        else:
            return self._active_profile_name

    @property
    def _active_profile_name_envvar(self) -> str:
        if self.profile_activating_envvar:
            return self.profile_activating_envvar
        else:
            return f"{self.profile_root}_PROFILE".upper()

    @property
    def _active_profile_name(self) -> typing.Optional[str]:
        return (
            os.environ.get(self._active_profile_name_envvar, None) or None
        )

    @_active_profile_name.setter
    def _active_profile_name(self, value):
        if value is None:
            value = ""
        os.environ[self._active_profile_name_envvar] = value

    @property
    def profile_is_live(self) -> bool:
        return self._const_is_live

    @property
    def profile_is_active(self) -> bool:
        return self.profile_name == self._active_profile_name

    @property
    def _profile_parent(self) -> typing.Optional["EnvvarProfile"]:
        profile_name = self._profile_parent_name
        if profile_name is None:
            return None
        else:
            return self.__class__(
                name=self._profile_parent_name, parent_name=None, profile_is_live=self.profile_is_live
            )

    def _get_prop(self, prop: typing.Union[str, EnvvarProfileProperty]) -> EnvvarProfileProperty:
        if isinstance(prop, EnvvarProfileProperty):
            return prop
        prop = getattr(self.__class__, prop, None)
        if prop is None or not isinstance(prop, EnvvarProfileProperty):
            raise KeyError(prop)
        return prop

    def _get_profile_tree(self) -> typing.Generator["EnvvarProfile", None, None]:
        yield self
        parent_profile = self._profile_parent
        while parent_profile:
            yield parent_profile
            parent_profile = parent_profile._profile_parent

    @property
    def _loader(self) -> ProfileLoader:
        if self.profile_is_live:
            if "live" not in self._profile_loaders:
                self._profile_loaders["live"] = LiveProfileLoader()
            return self._profile_loaders["live"]
        else:
            if "frozen" not in self._profile_loaders:
                self._profile_loaders["frozen"] = FrozenProfileLoader()
            return self._profile_loaders["frozen"]

    def has_prop_value(self, prop: typing.Union[str, EnvvarProfileProperty]) -> bool:
        """
        Returns True if the property has a concrete value set either via environment
        variables or on the froze profile instance.
        If a property only has a default value set, this returns False.
        """
        return self._loader.has_prop_value(self, prop)

    def _get_prop_value(self, prop: typing.Union[str, EnvvarProfileProperty], default=NotSet):
        return self._loader.get_prop_value(self, prop, default=default)

    def _set_prop_value(self, prop: typing.Union[str, EnvvarProfileProperty], value: typing.Any):
        self._loader.set_prop_value(self, prop, value)

    def _do_load(self):
        self._loader.load(self)

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return dict(self)

    def to_envvars(self):
        """
        Export property values to a dictionary with environment variable names as keys.
        """
        export = {}
        for prop_name in self.profile_properties:
            prop = self._get_prop(prop_name)
            value = self[prop_name]
            if value is not None:
                export[prop.get_envvar(self)] = prop.to_str(self, value)
        if self._profile_parent_name:
            export[
                f"{self._envvar_prefix}PARENT_PROFILE".upper()
            ] = self._profile_parent_name
        return export

    def activate(self, profile_name=NotSet):
        """
        Sets <PROFILE_ROOT>_PROFILE environment variable to the name of the current profile.
        """
        if profile_name is NotSet:
            profile_name = self.profile_name
        self._active_profile_name = profile_name


def to_snake_case(camel_case: str) -> str:
    # https://stackoverflow.com/a/1176023/38611
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_case)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def envvar_profile_cls(profile_cls=None, **profile_cls_options):
    """
    A class decorator that makes the decorated class a sub-class of EnvvarProfile and transforms
    its type annotations into envvar profile properties.
    """

    def decorator(profile_cls):
        profile_option_names = ["profile_root", "profile_activating_envvar"]
        profile_option_defaults = {
            "profile_root": to_snake_case(profile_cls.__name__)
        }

        dct = {}
        for option_name in profile_option_names:
            if option_name in profile_cls_options:
                dct[option_name] = profile_cls_options[option_name]
            elif option_name in profile_cls.__dict__:
                dct[option_name] = getattr(profile_cls, option_name)
            elif option_name in profile_option_defaults:
                dct[option_name] = profile_option_defaults[option_name]

        property_names = []

        for cls in reversed(profile_cls.__mro__[:-1]):
            # Exclude base classes that aren't SimpleProfile sub-classes or aren't the class being decorated.
            if not issubclass(cls, EnvvarProfile) and cls is not profile_cls:
                continue

            for k, v in typing.get_type_hints(cls).items():
                if k.startswith("_") or k.startswith("profile_"):
                    continue

                if k not in property_names:
                    property_names.append(k)

                default = getattr(cls, k, None)
                if isinstance(default, EnvvarProfileProperty):
                    default = default.default

                dct[k] = EnvvarProfileProperty(name=k, default=default, type_=v)

        dct["profile_properties"] = property_names

        bases = []
        if not issubclass(profile_cls, EnvvarProfile):
            bases.append(EnvvarProfile)
        bases.append(profile_cls)

        return type(profile_cls.__name__, tuple(bases), dct)

    if profile_cls is None:
        return decorator
    else:
        return decorator(profile_cls)


def envvar_profile(
    profile_root: str,
    profile_properties: typing.Dict[str, typing.Optional[str]] = None,
    **profile_properties_as_kwargs,
) -> typing.Type[EnvvarProfile]:
    """
    Creates an EnvvarProfile instance without the need for an explicit declaration of the envvar profile class.
    """
    if profile_properties:
        profile_properties_as_kwargs.update(profile_properties)
    return type(f"{profile_root}Profile", (EnvvarProfile,), {
        "profile_root": profile_root.lower(),
        "profile_properties": list(profile_properties_as_kwargs.keys()),
        **{
            k: EnvvarProfileProperty(name=k, default=v, type_=str)
            for k, v in profile_properties_as_kwargs.items()
        },
    })()
