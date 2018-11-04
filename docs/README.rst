###########
wr-profiles
###########

Introduction
============

**wr-profiles** allows declaring a profile -- a collection of key, value pairs backed by environment variables and accessing them
through dot notation with auto-complete working in your IDE. You can also have multiple separate environments declared
and switch between profiles by changing just one environment variable (just like you normally do when working with
multiple AWS accounts if you have that background). And a little bit more.

    *wr-* in the package name stands for *Wheel Reinvented*. Just like all other packages whose name starts with
    *wr-*, the meaning of this library (as in *meaning of life*) lies in its existence and evolution
    and not in any external application of it.

Supported Python Versions
-------------------------

* Python 3.6
* Python 3.7

Example
=======

Declare the profile:

.. code-block:: python

    from wr_profiles import envvar_profile_cls

    @envvar_profile_cls
    class WarehouseProfile:
        host: str = "localhost"
        username: str
        password: str

    warehouse_profile = WarehouseProfile()


Set up the environments:

.. code-block:: bash

    export WAREHOUSE_STAGING_PARENT_PROFILE="production"
    export WAREHOUSE_STAGING_PASSWORD="staging-password"
    export WAREHOUSE_PRODUCTION_USERNAME="production-username"
    export WAREHOUSE_PRODUCTION_PASSWORD="production-password"

Select the active environment:

.. code-block:: shell

    export WAREHOUSE_PROFILE=staging


Use the profile:

.. code-block:: python

    from profiles import warehouse_profile

    assert warehouse_profile.host == "localhost"
    assert warehouse_profile.username == "production-username"
    assert warehouse_profile.password == "staging-password"


Installation
============

.. code-block:: bash

    pip install wr-profiles

If you decide to use this library, make sure you pin the version number in your requirements file.

We are following interpretation of the semantic versioning schema. Example:

* ``v2.x.a -> v2.x.b`` - bugfix or non-breaking change, safe to upgrade.
* ``v2.x.* -> v3.y.*`` - potentially breaking changes, feature added, minimal changes to user code may be required
* ``v2.* -> v3.*`` - complete changeover


Changelog
=========

v4.2.0
------

* Added ``profile_delegate`` feature.

v4.1.0
------

* Added ``EnvvarProfile.create_env`` which creates an ``Environment`` which can be applied
  as a context manager.


User Guide
==========

Concepts
--------

Profile
^^^^^^^

A **profile** represents a set of configurable **properties** of a single service
backed by environment variables.

In your application, there can be multiple unrelated profiles each providing interface
to properties of a different service.

Instances of profiles associated with the same service share the same base class and are identified by
``profile_root`` specified in that base class. Is is the root from which all relevant
environment variable names are formed.

Profiles of unrelated services do not share any information.
In the discussion below, different instances or kinds of profiles all relate to the same service,
e.g. same ``profile_root``.

Warehouse Profile (Example)
"""""""""""""""""""""""""""

In the discussion below, we will use a profile for a data warehouse access as an example.
Class ``WarehouseProfile`` declares the profile and the properties it provides.
Object ``warehouse_profile`` is the single instance through which user must look up service's
active configuration.

.. code-block:: python

    from wr_profiles import envvar_profile_cls

    @envvar_profile_cls
    class WarehouseProfile:
        host: str = "localhost"
        username: str
        password: str
    
    warehouse_profile = WarehouseProfile()


Profile Name
^^^^^^^^^^^^

Individual instances of profiles are identified by their name (``profile_name`` property).


Active Profile
^^^^^^^^^^^^^^

The **active profile** is the profile of a service that should be used 
according to the environment variables.

By default, the active profile can be switched by setting a special environment variable
``<PROFILE_ROOT>_PROFILE``. For ``WarehouseProfile`` that would be ``WAREHOUSE_PROFILE``.

The name of this variable can be customised by setting your class's ``profile_activating_envvar``.

If this variable is not set, the active profile is *an empty string*, and the environment variables
consulted are in the form:

.. code-block:: bash

    <PROFILE_ROOT>_<PROPERTY_NAME>

For example, ``WAREHOUSE_HOST``.

If ``<PROFILE_ROOT>_PROFILE`` is set then the active profile consults environment variables in the form:

.. code-block::

    <PROFILE_ROOT>_<PROFILE_NAME>_<PROPERTY_NAME>

For example, if ``WAREHOUSE_PROFILE`` is set to ``staging`` then ``host`` property will be looked up
under ``WAREHOUSE_STAGING_HOST``.


Parent Profile
^^^^^^^^^^^^^^

Any particular profile (for example, ``staging`` profile of ``WarehouseProfile``) can be instructed
to inherit its property values from a **parent profile** by setting:

.. code-block:: bash

    <PROFILE_ROOT>_<PROFILE_NAME>_PARENT_PROFILE

For example, ``WAREHOUSE_STAGING_PARENT_PROFILE``, if set to ``production``, would mean that
if environment variable ``WAREHOUSE_STAGING_HOST`` was not set, property value loader would
consult ``WAREHOUSE_PRODUCTION_HOST`` instead. And only if that variable was not present,
the default value of the property would be used.

*Limitation*: The default profile (``profile_name=""``) cannot be used as a parent profile.
If you specify empty string as ``<PROFILE_ROOT>_<PROFILE_NAME>_PARENT_PROFILE`` then this
profile won"t have any parent profile. It is the same as having no value set. 


Live Profile vs Frozen Profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A **live** profile always consults environment variables (``os.environ``) whereas
a **frozen** profile does so only during instantiation and when explicitly loaded
with ``load()`` method.

Common Scenarios
----------------


Get Current Active Profile
^^^^^^^^^^^^^^^^^^^^^^^^^^

Current active profile is always available through the instance of your profile class which is
instantiated with no arguments:

.. code-block:: python

    warehouse_profile = WarehouseProfile()

Normally you'd only need a single instance of your profile class pointing to the active profile.


Get Concrete Profile
^^^^^^^^^^^^^^^^^^^^

To work with a concrete profile which may not necessarily be activated, use ``load``
factory method:

.. code-block:: python

    staging = WarehouseProfile.load("staging")

By default, this profile will be frozen which means it will be loaded only once during instantiation.
If you want it to always consult environment variables, pass ``profile_is_live=True``:

.. code-block:: python

    staging = WarehouseProfile.load("staging", profile_is_live=True)


Customise Profile-Activating Environment Variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Imagine you have your ``WarehouseProfile`` and you want to use it in tests. In tests it should have different defaults.

.. code-block:: python

    @envvar_profile_cls
    class WarehouseTestProfile(WarehouseProfile):

        # If you don't set this, it would be "WAREHOUSE_PROFILE" which would conflict
        # with your non-test profile.
        profile_activating_envvar = "WAREHOUSE_TEST_PROFILE"

        host: str = "test-host"
        username: str = "test-user"


In your application you would then have two instances:

.. code-block:: python

    profile = WarehouseProfile()
    test_profile = WarehouseTestProfile()

Now you can reuse your non-test profiles in tests when it makes sense. For example, if you have set up environment
variables in the form ``WAREHOUSE_SANDBOX_*`` then this "sandbox" profile can be used in tests by just setting
``WAREHOUSE_TEST_PROFILE`` to ``sandbox``.

Note that ``profile_root`` for both profiles is the same.

Activate Profile
^^^^^^^^^^^^^^^^

To activate a profile, call ``activate`` method on a frozen instance of the profile without any arguments,
or, ``activate(profile_name)`` on the live current profile instance:

.. code-block:: python

    staging.activate()
    # or:
    warehouse_profile.activate("staging")


Get All Values
^^^^^^^^^^^^^^

.. code-block:: python

    warehouse_profile.to_dict()


Set Environment Variables
^^^^^^^^^^^^^^^^^^^^^^^^^

Note that the environment variables you set normally apply only to the current process and its sub-processes
so this will have limited use -- it will only make sense when you are launching sub-processes or you do this
somewhere early in the code before environment variables are loaded by other parts of your code.

.. code-block:: python

    os.environ.update(warehouse_profile.to_envvars())


Check If Property Has Non-Default Value
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    warehouse_profile.has_prop_value("username")
    # or
    warehouse_profile.has_prop_value(WarehouseProfile.username)


Inspect Property
^^^^^^^^^^^^^^^^

.. code-block:: python

    from wr_profiles import EnvvarProfileProperty

    assert isinstance(WarehouseProfile.username, EnvvarProfileProperty)
    assert WarehouseProfile.username.name == "username"
    assert WarehouseProfile.username.default == "default-username"


Environment Objects
^^^^^^^^^^^^^^^^^^^

Starting from version 4.1 you can create an instance of ``Environment`` which can then be applied on ``os.environ``
or pytest's ``monkeypatch`` fixture. ``Environment`` is a dictionary of environment variables that neet to
be set or unset in order to apply the specified environment. The values are determined at environment
creation time.

.. code-block:: python

    test_env = warehouse_profile.create_env(username='test', password=None)
    with test_env.applied():
        assert warehouse_profile.username == 'test'
        assert os.environ['WAREHOUSE_USERNAME'] == 'test'

        assert warehouse_profile.password is None
        assert 'WAREHOUSE_PASSWORD' not in os.environ


Config Object that Delegates to Profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environment variables are not necessarily the only source of configuration.
In a non-trivial application you probably won't be consulting the profile object from your application code
directly. Instead, you'll have a config object which will consult different sources including the
environment variable profile.
It is very likely that the properties defined in your profile class will
be a subset of those exposed by the config object. If you don't want to repeat yourself, you can have your
config class extend the profile class and have the config class delegate all the attributes to the profile
class except for those implemented in the config class.

.. code-block:: python

    profile = WarehouseProfile()

    class WarehouseConfig(WarehouseProfile):
        @property
        def profile_delegate(self):
            return profile

        @property
        def username(self):
            return profile.username or "anonymous"
