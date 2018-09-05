###########
wr-profiles
###########

Introduction
============

*wr-* in the package name stands for *Wheel Reinvented*. Just like all other packages whose name starts with
*wr-*, the meaning of this library (as in *meaning of life*) lies in its existence and evolution 
and not in any external application of it.

Why Do I Need This?
-------------------

You don't.

But you could find it useful if you use environment variables as primary means of passing 
configuration to your program, and you have scenarios when your program has to switch between sets of 
environment variables (which we call *profiles*).

Supported Python Versions
-------------------------

* Python 3.6
* Python 3.7

Example
=======

Here's an example of declaring a profile with three properties and using it to consult the values
of these properties. More advanced examples are available in the user guide below.

.. code-block:: python

    # profiles.py

    from wr_profiles import Profile, Property

    class WarehouseProfile(Profile):
        profile_root = "warehouse"
        username = Property(default="default-username")
        password = Property()

    warehouse_profile = WarehouseProfile()


.. code-block:: bash

    # Set up the environment

    export WAREHOUSE_PROFILE=staging
    export WAREHOUSE_STAGING_PARENT_PROFILE="production"
    export WAREHOUSE_STAGING_PASSWORD="staging-password"
    export WAREHOUSE_PRODUCTION_USERNAME="production-username"
    export WAREHOUSE_PRODUCTION_PASSWORD="production-password"


.. code-block:: python

    from profiles import warehouse_profile

    assert warehouse_profile.username == "production-username"
    assert warehouse_profile.password == "staging-password"



Installation
============

.. code-block:: bash

    pip install wr-profiles

If you decide to use this library, make sure you pin the version number in your requirements file.

We are following interpretation of the semantic versioning schema:

* ``v2.x.a -> v2.x.b`` - bugfix or non-breaking change, safe to upgrade.
* ``v2.x.* -> v3.y.*`` - potentially breaking changes, feature added, minimal changes to user code may be required
* ``v2.* -> v3.*`` - complete changeover


User Guide
==========

Concepts
--------

Profile
^^^^^^^

A **profile** represents a set of configurable **properties** of a single service
backed by environment variables.

There can be multiple unrelated profiles (multiple classes extending ``Profile`` class),
each providing interface to properties of a different service.

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

    class WarehouseProfile(Profile):
        profile_root = "warehouse"
        
        host = Property(default="localhost")
        username = Property()
        password = Property(default="")
    
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
the default value of the property (if available) would be used.

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

Normally you'd only need a single instance of your profile class.


Get Concrete Profile
^^^^^^^^^^^^^^^^^^^^

To work with a concrete profile which may not necessarily be activated, use ``load``
factory method:

.. code-block:: python

    staging = WarehouseProfile.load("staging")

By default, this profile will be frozen which means it will be loaded only once during instantiation.
If you want it to always consult environment variables, pass ``is_live=True``:

.. code-block:: python

    staging = WarehouseProfile.load("staging", is_live=True)


Customise Profile-Activating Environment Variable
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Imagine you have your ``WarehouseProfile`` and you want to use it in tests. In tests it should have different defaults.
Perhaps some properties with no defaults in production can have defaults in tests.

.. code-block:: python

    class WarehouseTestProfile(WarehouseProfile):

        # If you don't set this, it would be "WAREHOUSE_PROFILE" which would conflict
        # with your non-test profile.
        profile_activating_envvar = "WAREHOUSE_TEST_PROFILE"

        host = WarehouseProfile.host.replace(default="test-host")
        username = WarehouseProfile.username.replace(default="test-user")

        # No need to specify "username" here as it is the same as in WarehouseProfile

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

    assert isinstance(WarehouseProfile.username, Property)
    assert WarehouseProfile.username.name == "username"
    assert WarehouseProfile.username.has_default
    assert WarehouseProfile.username.default == "default-username"
