import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from .not_set import NotSet
from .props import AttributesList, Property

PROFILE_NAME_COMPONENT_REGEX = re.compile(r"^[a-z]([\d\w]*[a-z0-9])?$")


class ProfileLoader(ABC):
    """
    Base class for profile loaders.
    """

    @abstractmethod
    def load(self, profile):
        pass

    @abstractmethod
    def has_prop_value(self, profile: "Profile", prop: Union[str, Property]) -> bool:
        pass

    @abstractmethod
    def get_prop_value(
        self, profile: "Profile", prop: Union[str, Property], default: Any = NotSet
    ) -> Any:
        pass

    @abstractmethod
    def set_prop_value(
        self, profile: "Profile", prop: Union[str, Property], value: Any
    ):
        pass

    def to_dict(self, profile: "Profile") -> Dict[Property, Any]:
        values = {}
        for prop in profile.profile_props:
            try:
                values[prop] = profile._get_prop_value(prop)
            except Property.MissingValue:
                pass
        return values


class LiveProfileLoader(ProfileLoader):
    def set_prop_value(
        self, profile: "Profile", prop: Union[str, Property], value: Any
    ):
        if isinstance(prop, str):
            prop = profile.get_prop(prop)
        os.environ[prop.get_envvar(profile)] = prop.to_str(profile, value)

    def has_prop_value(self, profile: "Profile", prop: Union[str, Property]) -> bool:
        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return True
            prop_envvar = prop.get_envvar(check_profile)
            if prop_envvar in os.environ:
                return True

        return False

    def get_prop_value(
        self, profile: "Profile", prop: Union[str, Property], default: Any = NotSet
    ) -> Any:
        if isinstance(prop, str):
            prop = profile.get_prop(prop)

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

        if prop.has_default:
            return prop.default

        raise prop.missing_value()

    def load(self, profile):
        # Nothing to do -- live profile does not need to be reloaded.
        pass


class FrozenProfileLoader(ProfileLoader):
    def set_prop_value(
        self, profile: "Profile", prop: Union[str, Property], value: Any
    ):
        if isinstance(prop, str):
            prop = profile.get_prop(prop)
        profile._const_values[prop.name] = value

    def has_prop_value(self, profile: "Profile", prop: Union[str, Property]) -> bool:
        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return True

        return False

    def get_prop_value(
        self, profile: "Profile", prop: Union[str, Property], default: Any = NotSet
    ) -> Any:
        if isinstance(prop, str):
            prop = profile.get_prop(prop)

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_values:
                return check_profile._const_values[prop.name]

        for check_profile in profile._get_profile_tree():
            if prop.name in check_profile._const_defaults:
                return check_profile._const_defaults[prop.name]

        if default is not NotSet:
            return default

        if prop.has_default:
            return prop.default

        raise prop.missing_value()

    def load(self, profile):
        # Create a live clone of itself and load all props.
        live_clone = profile.__class__(
            name=profile.profile_name,
            parent_name=profile._profile_parent_name,
            is_live=True,
            values=profile._const_values,
        )

        values = {}
        for prop in profile.profile_props:
            if live_clone.has_prop_value(prop):
                values[prop.name] = live_clone._get_prop_value(prop)

        profile._const_values = values


class Profile:
    """
    Represents a set of configuration values backed by environment variables.
    """

    profile_root = None

    # Defaults to "<profile_root>_PROFILE".
    # You should set this only when you extend your own Profile classes to customise them
    # and you want to activate the extended profile with an envvar that does not conflict
    # with the parent profile.
    profile_activating_envvar = None

    profile_props = AttributesList(Property)

    # shared loaders
    _profile_loaders = {}  # type: Dict[str, ProfileLoader]

    def __init__(
        self,
        *,
        name=None,
        parent_name=None,
        is_live=True,
        values=None,
        defaults=None,
        **kwargs,
    ):
        self._const_name = name
        self._const_parent_name = parent_name
        self._const_is_live = is_live

        self._const_values = {}
        if values is not None:
            self._const_values.update(values)

        self._const_defaults = {}
        if defaults is not None:
            self._const_defaults.update(defaults)

        if kwargs:
            raise ValueError(kwargs)

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
        cls, name=None, parent_name=None, is_live=False, values=None, defaults=None
    ):
        """
        Get a loaded frozen instance of a specific profile.
        """
        instance = cls(
            name=name,
            parent_name=parent_name,
            is_live=is_live,
            values=values,
            defaults=defaults,
        )
        instance._do_load()
        return instance

    @property
    def _envvar_prefix(self):
        if self.profile_name:
            return f"{self.profile_root}_{self.profile_name}_".upper()
        return f"{self.profile_root}_".upper()

    @property
    def _profile_parent_name(self):
        if self._const_parent_name:
            return self._const_parent_name
        elif not self.is_live:
            return None
        elif self.profile_name:
            return os.environ.get(f"{self._envvar_prefix}PARENT_PROFILE", None)
        else:
            return None

    @property
    def profile_name(self):
        if self._const_name:
            return self._const_name
        elif not self.is_live:
            return None
        else:
            return self._active_profile_name

    @property
    def _active_profile_name_envvar(self):
        if self.profile_activating_envvar:
            return self.profile_activating_envvar
        else:
            return f"{self.profile_root}_PROFILE".upper()

    @property
    def _active_profile_name(self):
        return (
            os.environ.get(self._active_profile_name_envvar, None) or None
        )

    @_active_profile_name.setter
    def _active_profile_name(self, value):
        if value is None:
            value = ""
        os.environ[self._active_profile_name_envvar] = value

    @property
    def is_live(self):
        return self._const_is_live

    @property
    def is_active(self):
        return self.profile_name == self._active_profile_name

    @property
    def _profile_parent(self):
        profile_name = self._profile_parent_name
        if profile_name is None:
            return None
        else:
            return self.__class__(
                name=self._profile_parent_name, parent_name=None, is_live=self.is_live
            )

    def get_prop(self, prop_name):
        prop = getattr(self.__class__, prop_name, None)
        if prop is None or not isinstance(prop, Property):
            raise KeyError(prop_name)
        return prop

    def _get_profile_tree(self):
        yield self
        parent_profile = self._profile_parent
        while parent_profile:
            yield parent_profile
            parent_profile = parent_profile._profile_parent

    @property
    def _loader(self):
        if self.is_live:
            if "live" not in self._profile_loaders:
                self._profile_loaders["live"] = LiveProfileLoader()
            return self._profile_loaders["live"]
        else:
            if "frozen" not in self._profile_loaders:
                self._profile_loaders["frozen"] = FrozenProfileLoader()
            return self._profile_loaders["frozen"]

    def has_prop_value(self, prop: Union[str, Property]) -> bool:
        """
        Returns True if the property has a concrete value set either via environment
        variables or on the froze profile instance.
        If a property only has a default value set, this returns False.
        """
        return self._loader.has_prop_value(self, prop)

    def _get_prop_value(self, prop: Union[str, Property], default=NotSet):
        return self._loader.get_prop_value(self, prop, default=default)

    def _set_prop_value(self, prop: Union[str, Property], value: Any):
        self._loader.set_prop_value(self, prop, value)

    def _do_load(self):
        self._loader.load(self)

    def to_dict(self) -> Dict[Property, Any]:
        return self._loader.to_dict(self)

    def to_envvars(self):
        """
        Export property values to a dictionary with environment variable names as keys.
        """
        export = {}
        for prop, prop_value in self.to_dict().items():
            export[prop.get_envvar(self)] = prop.to_str(self, prop_value)
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
