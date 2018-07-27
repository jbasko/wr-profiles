from typing import Any

from .not_set import NotSet


class Property:
    """
    Represents a profile property -- a value backed by an environment variable.
    The exact environment variable depends on what profile the property belongs to.
    """

    class MissingValue(Exception):
        """
        Raised when the value is requested for an existing property
        """
        def __init__(self, prop):
            self.prop = prop

        def __repr__(self):
            return '<{} {!r}>'.format(self.__class__.__name__, self.prop.name)

    def __init__(self, name=None, default: Any=NotSet, deserializer=None, serializer=None):
        self.name = name
        self.default = default
        self._deserializer = deserializer
        self._serializer = serializer

    def __hash__(self):
        return hash((self.__class__, self.name))

    def __set_name__(self, owner, name):
        # Only works in Python 3.6+
        # On Python 3.5 you need to manually pass the name.
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.get_prop_value(self)

    def __set__(self, instance, value):
        instance.set_prop_value(self, value)

    def __str__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.name)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.name)

    def get_envvar(self, profile):
        assert self.name
        return '{}{}'.format(profile.envvar_prefix, self.name.upper())

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

    def missing_value(self):
        return self.MissingValue(self)


class AttributesList:
    def __init__(self, attr_base_cls):
        self._attr_base_cls = attr_base_cls

    def __get__(self, instance, owner):
        if instance is None:
            return self

        for name in dir(owner):
            if name.startswith('__'):
                continue
            attr = getattr(owner, name)
            if isinstance(attr, self._attr_base_cls):
                yield attr
