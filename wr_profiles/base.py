import os
import re
from typing import Any, Optional, Type


class _NotSet:
    """
    Not set value marker.
    Do not use directly, instead use the NotSet instance.
    """
    def __bool__(self):
        return False


NotSet = _NotSet()


class Property:
    """
    Represents a profile property -- a value backed by an environment variable.
    The exact environment variable depends on what profile the property belongs to.
    """

    def __init__(self, name, default: Any=NotSet, deserializer=None, serializer=None):
        self.name = name
        self.default = default
        self._deserializer = deserializer
        self._serializer = serializer

    def __get__(self, instance: Optional['Profile'], owner: Type['Profile']):
        if instance is None:
            return self
        if self._deserializer is None:
            return instance.get_prop_value(self.name)
        else:
            return self.from_str(instance, instance.get_prop_value(self.name))

    def __str__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.name)

    @property
    def has_default(self):
        """
        Returns True if this property has a default value set in its declaration.
        """
        return self.default is not NotSet

    def serializer(self, func):
        """
        Register a serializer for this profile property.
        Serializer is a function that takes property value and returns a string.
        The function name must be either `<lambda>` or `{prop_name}`
        """
        if callable(func):
            if not (func.__name__ == '<lambda>' or func.__name__ == self.name):
                raise RuntimeError('Invalid {!r} property serializer name {!r} -- should be called {!r}'.format(
                    self.name, func.__name__, self.name
                ))
        else:
            assert func is None
        self._serializer = func
        return self

    def deserializer(self, func):
        """
        Register a deserializer for this profile property.
        The function name must be either `<lambda>` or `{prop_name}`.
        """
        if callable(func):
            if not (func.__name__ == '<lambda>' or func.__name__ == self.name):
                raise RuntimeError('Invalid {!r} property deserializer name {!r} -- should be called {!r}'.format(
                    self.name, func.__name__, self.name
                ))
        else:
            assert func is None
        self._deserializer = func
        return self

    def from_str(self, profile, value):
        if self._deserializer is not None:
            return self._deserializer(profile, value)
        else:
            return value

    def to_str(self, profile, value):
        if self._serializer is not None:
            return self._serializer(profile, value)
        else:
            return str(value)


class _ProfileProps:
    """
    Generator of all profile properties (not values of properties).
    """

    def __get__(self, instance, owner):
        for name in dir(owner):
            if name.startswith('__'):
                continue
            try:
                yield owner.get_prop(name)
            except KeyError:
                pass


class Profile:
    """
    Represents a set of configuration values backed by environment variables with common profile root.

    The set of environment variables to use is determined by the current profile_name which is
    used to build the prefix of environment variables by appending that to the profile root.
    """

    # Identifies the type of profile.
    # Profiles with the same root are interchangeable.
    profile_root = None  # type: str

    props = _ProfileProps()

    _name_component_re = re.compile(r'^[a-z]([\d\w]*[a-z0-9])?$')

    @classmethod
    def autoload(cls, profile_root, profile_names=None) -> 'Profile':
        """
        Given a profile root and all potential profile names, inspects current environment variables
        and generates a Profile class and returns the active instance of it.
        """

        root_prefix = '{}_'.format(profile_root).upper()
        profile_prefixes = {n: '{}{}_'.format(root_prefix, n).upper() for n in profile_names or ()}

        prop_names = set()

        for k, v in os.environ.items():
            if k.startswith(root_prefix):
                for pn, pp in profile_prefixes.items():
                    if k.startswith(pp):
                        prop_name = k[len(pp):].lower()
                        prop_names.add(prop_name)
                        break
                else:
                    prop_name = k[len(root_prefix):].lower()
                    if prop_name == 'profile':
                        continue
                    prop_names.add(prop_name)

        dct = {pn: Property(pn, default=None) for pn in prop_names}
        dct['profile_root'] = profile_root
        profile_cls = type(
            profile_root.lower().title() + cls.__name__,
            (cls,),
            dct,
        )
        return profile_cls()

    def __init__(self, _frozen_name=NotSet, _values=None, _active_profile=None):
        """
        Keyword arguments that start with underscore should not be used from outside wr_profiles library.
        """

        if not self.profile_root:
            raise ValueError('{}.profile_root is required'.format(self.__class__.__name__))

        if not self._name_component_re.match(self.profile_root):
            raise ValueError('{}.profile_root {!r} is invalid'.format(self.__class__.__name__, self.profile_root))

        if _frozen_name is not NotSet and not self._name_component_re.match(_frozen_name):
            raise ValueError('{} profile name {!r} is invalid'.format(self.__class__.__name__, _frozen_name))

        self._frozen_name = _frozen_name

        self._values = _values or {}

        # Frozen profile needs to hold on to the non-frozen instance of the profile.
        # It is useful when you want to compare this profile instance with the active one.

        if _frozen_name is not NotSet:
            assert _active_profile is not None

        if _active_profile is not None:
            assert _frozen_name is not NotSet

        self._active_profile = _active_profile

    @property
    def is_frozen(self):
        """
        A profile is frozen when its values are not loaded from environment variables after the initial load.
        The opposite of frozen is live.
        """
        return self._frozen_name is not NotSet

    @property
    def is_live(self):
        """
        Returns true if the profile reads its property values from environment variables.
        """
        return not self.is_frozen

    @property
    def is_active(self):
        """
        Returns True if the current profile instance is pointing to the same profile as the active profile.
        Note that this is not the opposite of is_frozen. A profile can be frozen and active at the same time.
        The opposite of is_frozen is is_live.
        """
        if self.is_live:
            return True
        return self.profile_name == self._active_profile.profile_name

    @property
    def profile_name(self):
        if self._frozen_name:
            return self._frozen_name
        else:
            return self.get_active_name()

    def get_active_name(self) -> Optional[str]:
        """
        Returns the name of the active profile.
        If the production profile is active, the name is None (not a an empty string).
        """
        envvar_name = (self.profile_root + '_profile').upper()
        return os.environ.get(envvar_name) or None

    def get_envvar_name(self, prop_name, profile_name=NotSet) -> str:
        """
        Returns name for the environment variable holding the value of property called prop_name
        """
        if profile_name is NotSet:
            if self.is_frozen:
                profile_name = self._frozen_name
            else:
                profile_name = self.get_active_name()
        if profile_name:
            return (self.profile_root + '_' + profile_name + '_' + prop_name).upper()
        else:
            return (self.profile_root + '_' + prop_name).upper()

    @classmethod
    def has_prop(cls, name):
        """
        Returns True if there exists a profile property with the specified name.
        """
        try:
            cls.get_prop(name)
            return True
        except KeyError:
            return False

    @classmethod
    def get_prop(cls, name):
        """
        Returns the descriptor of the profile property.
        To get the value of property, use get_prop_value.
        """
        prop = getattr(cls, name, None)
        if not isinstance(prop, Property):
            raise KeyError(name)
        return prop

    def get_prop_value(self, name, default=NotSet, profile_name=NotSet):
        """
        Returns the value of the profile property.
        If the value is not set and no default value is provided, raises KeyError.
        """
        prop = self.get_prop(name)

        if self.is_frozen:
            return self._values[name]

        if name in self._values:
            # Hard-coded values means even a non-frozen profile won't look into environment variables.
            return self._values[name]

        envvar_name = self.get_envvar_name(name, profile_name=profile_name)

        if default is NotSet:
            default = prop.default

        if default is NotSet:
            return os.environ[envvar_name]
        else:
            return os.environ.get(envvar_name, default)

    def set_prop_value(self, name, value):
        """
        Sets property `name` value to `value` in this profile.
        """
        self.get_prop(name)  # validate the prop exists
        self._values[name] = value

    def unset_prop_value(self, name):
        """
        Removes any value for property `name` set on this profile instance.
        """
        self.get_prop(name)  # validate the prop exists
        if name in self._values:
            del self._values[name]

    def load_custom(self, profile_name):
        """
        Loads a custom frozen profile by name.
        The loaded profile does not have to be active and is not made active on loading.
        """
        return self.__class__(
            _frozen_name=profile_name,
            _values=self.to_dict(include_defaults=True, profile_name=profile_name),
            _active_profile=self._active_profile or self,
        )

    def to_dict(self, include_defaults=True, profile_name=NotSet, serialize=False):
        """
        Export values of the active profile (or the named profile) to a dictionary.
        If serialize is set to True, the values will be serialized (converted to strings).
        """
        if self.is_frozen:
            assert profile_name is NotSet
            return dict(self._values)

        if profile_name is NotSet:
            profile_name = self.profile_name

        _values = {}

        not_set = _NotSet()
        for prop in self.props:
            if include_defaults:
                if prop.has_default:
                    value = self.get_prop_value(prop.name, profile_name=profile_name)
                else:
                    value = self.get_prop_value(prop.name, not_set, profile_name=profile_name)
            else:
                value = self.get_prop_value(prop.name, not_set, profile_name=profile_name)

            if value is not_set:
                continue

            if serialize:
                value = prop.to_str(self, value)
            _values[prop.name] = value

        return _values

    def export(self, include_defaults=True, profile_name=NotSet):
        """
        Export values of the active profile to a dictionary, keys of which are
        environment variable names (unlike property names as in the dictionary returned
        by to_dict).
        """
        values = self.to_dict(include_defaults=include_defaults, profile_name=profile_name, serialize=True)
        return {
            self.get_envvar_name(k, profile_name=profile_name): v
            for k, v in values.items()
        }
