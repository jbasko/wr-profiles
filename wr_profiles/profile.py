import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from .not_set import NotSet
from .props import AttributesList, Property

PROFILE_NAME_COMPONENT_REGEX = re.compile(r'^[a-z]([\d\w]*[a-z0-9])?$')


class ProfileLoader(ABC):
    """
    Base class for profile loaders.
    """

    @abstractmethod
    def load(self, profile):
        pass

    @abstractmethod
    def get_prop_value(self, profile: 'Profile', prop: Union[str, Property], default: Any=NotSet) -> Any:
        pass

    @abstractmethod
    def set_prop_value(self, profile: 'Profile', prop: Union[str, Property], value: Any):
        pass

    def to_dict(self, profile: 'Profile') -> Dict[Property, Any]:
        values = {}
        for prop in profile.props:
            try:
                values[prop] = profile.get_prop_value(prop)
            except Property.MissingValue:
                pass
        return values


class LiveProfileLoader(ProfileLoader):
    def set_prop_value(self, profile: 'Profile', prop: Union[str, Property], value: Any):
        if isinstance(prop, str):
            prop = profile.get_prop(prop)
        os.environ[prop.get_envvar(profile)] = prop.to_str(profile, value)

    def get_prop_value(self, profile: 'Profile', prop: Union[str, Property], default: Any = NotSet) -> Any:
        if isinstance(prop, str):
            prop = profile.get_prop(prop)

        for check_profile in profile.get_profile_tree():
            if prop.name in check_profile._const_values:
                return check_profile._const_values[prop.name]

        for check_profile in profile.get_profile_tree():
            prop_envvar = prop.get_envvar(check_profile)
            if prop_envvar in os.environ:
                return prop.from_str(check_profile, os.environ[prop_envvar])

        if default is not NotSet:
            return default

        if prop.has_default:
            return prop.default

        raise prop.missing_value()

    def load(self, profile):
        # Nothing to do -- live profile does not need to be reloaded.
        pass


class FrozenProfileLoader(ProfileLoader):
    def set_prop_value(self, profile: 'Profile', prop: Union[str, Property], value: Any):
        if isinstance(prop, str):
            prop = profile.get_prop(prop)
        profile._const_values[prop.name] = value

    def get_prop_value(self, profile: 'Profile', prop: Union[str, Property], default: Any = NotSet) -> Any:
        if isinstance(prop, str):
            prop = profile.get_prop(prop)

        for check_profile in profile.get_profile_tree():
            if prop.name in check_profile._const_values:
                return check_profile._const_values[prop.name]

        if default is not NotSet:
            return default

        if prop.has_default:
            return prop.default

        raise prop.missing_value()

    def load(self, profile):
        # Create a live clone of itself and load all props.
        live_clone = profile.__class__(
            name=profile.profile_name,
            parent_name=profile.parent_profile_name,
            is_live=True,
            values=profile._const_values,
        )

        values = {}
        for prop in profile.props:
            try:
                values[prop.name] = live_clone.get_prop_value(prop.name)
            except Property.MissingValue:
                continue

        profile._const_values = values


class Profile:
    """
    Represents a set of configuration values backed by environment variables.
    """

    profile_root = None

    props = AttributesList(Property)

    # shared loaders
    _profile_loaders = {}  # type: Dict[str, ProfileLoader]

    def __init__(self, *, name=None, parent_name=None, is_live=True, values=None, **kwargs):
        self._const_name = name
        self._const_parent_name = parent_name
        self._const_is_live = is_live

        self._const_values = {}
        if values is not None:
            self._const_values.update(values)

        if kwargs:
            raise ValueError(kwargs)

        if not self.profile_root:
            raise ValueError('{}.profile_root is required'.format(self.__class__.__name__))

        if not PROFILE_NAME_COMPONENT_REGEX.match(self.profile_root):
            raise ValueError('{}.profile_root {!r} is invalid'.format(self.__class__.__name__, self.profile_root))

    @classmethod
    def get_instance(cls, name=None, parent_name=None, is_live=False, values=None):
        """
        Get a loaded frozen instance of a specific profile.
        """
        instance = cls(name=name, parent_name=parent_name, is_live=is_live, values=values)
        instance.load()
        return instance

    @property
    def envvar_prefix(self):
        if self.profile_name:
            return '{}_{}_'.format(self.profile_root, self.profile_name).upper()
        return '{}_'.format(self.profile_root).upper()

    @property
    def parent_profile_name(self):
        if self._const_parent_name:
            return self._const_parent_name
        elif not self.is_live:
            return None
        elif self.profile_name:
            return os.environ.get('{}PARENT_PROFILE'.format(self.envvar_prefix), None)
        else:
            return None

    @property
    def profile_name(self):
        if self._const_name:
            return self._const_name
        elif not self.is_live:
            return None
        else:
            return self.active_profile_name

    @property
    def active_profile_name(self):
        return os.environ.get('{}_PROFILE'.format(self.profile_root).upper(), None) or None

    @active_profile_name.setter
    def active_profile_name(self, value):
        if value is None:
            value = ''
        os.environ['{}_PROFILE'.format(self.profile_root).upper()] = value

    @property
    def is_live(self):
        return self._const_is_live

    @property
    def is_active(self):
        return self.profile_name == self.active_profile_name

    @property
    def parent_profile(self):
        profile_name = self.parent_profile_name
        if profile_name is None:
            return None
        else:
            return self.__class__(name=self.parent_profile_name, parent_name=None, is_live=self.is_live)

    def get_prop(self, prop_name):
        prop = getattr(self.__class__, prop_name, None)
        if prop is None or not isinstance(prop, Property):
            raise KeyError(prop_name)
        return prop

    def get_profile_tree(self):
        yield self
        parent_profile = self.parent_profile
        while parent_profile:
            yield parent_profile
            parent_profile = parent_profile.parent_profile

    @property
    def loader(self):
        if self.is_live:
            if 'live' not in self._profile_loaders:
                self._profile_loaders['live'] = LiveProfileLoader()
            return self._profile_loaders['live']
        else:
            if 'frozen' not in self._profile_loaders:
                self._profile_loaders['frozen'] = FrozenProfileLoader()
            return self._profile_loaders['frozen']

    def get_prop_value(self, prop: Union[str, Property], default=NotSet):
        return self.loader.get_prop_value(self, prop, default=default)

    def set_prop_value(self, prop: Union[str, Property], value: Any):
        self.loader.set_prop_value(self, prop, value)

    def load(self):
        self.loader.load(self)

    def to_dict(self) -> Dict[Property, Any]:
        return self.loader.to_dict(self)

    def to_envvars(self):
        """
        Export property values to a dictionary with environment variable names as keys.
        """
        export = {}
        for prop, prop_value in self.to_dict().items():
            export[prop.get_envvar(self)] = prop.to_str(self, prop_value)
        if self.parent_profile_name:
            export['{}PARENT_PROFILE'.format(self.envvar_prefix).upper()] = self.parent_profile_name
        return export

    def activate(self, profile_name=NotSet):
        """
        Sets <PROFILE_ROOT>_PROFILE environment variable to the name of the current profile.
        """
        if profile_name is NotSet:
            profile_name = self.profile_name
        self.active_profile_name = profile_name
