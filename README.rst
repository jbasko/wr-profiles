*****************************
wr-profiles
*****************************

.. code-block:: shell

    pip install wr-profiles

=======
Example
=======

.. code-block:: python

    # warehouse.py

    from wr_profiles import Profile, Property

    class _WarehouseProfile(Profile):
        profile_root = 'warehouse'

        host = Property('host', default='localhost')
        user = Property('user')
        password = Property('password', default='')

        @property
        def url(self):
            return '{user}:{password}@{host}'.format(user=self.user, password=self.password, host=self.host)

    warehouse_profile = _WarehouseProfile()

    print(warehouse_profile.url)


.. code-block:: bash

    > export WAREHOUSE_SANDBOX_USER="sandbox-user"
    > export WAREHOUSE_SANDBOX_PASSWORD="sandbox-password"
    > export WAREHOUSE_PROD_USER="root"
    > export WAREHOUSE_PROD_PASSWORD="bigSecret"
    > export WAREHOUSE_PROFILE="sandbox"

    > python warehouse.py
    sandbox-user:sandbox-password@localhost

    > WAREHOUSE_PROFILE="prod" python warehouse.py
    root:bigSecret@localhost


=======
Profile
=======

A **Profile** represents a set of configuration values backed by environment variables.
The **active** profile can be switched by changing just one environment variable -- the one identifying the name of the profile to be used.
Your code may be using more than one independent profile at a time, or a combination of interrelated profiles when changing one enclosing profile changes selection of sub-profiles.

For example, your code may be connecting to a data warehouse.
Most of the time you connect to one instance, but in certain scenarios, say,
when doing integration testing, you may wish to connect to a different instance.
The configuration for this connection consists of multiple environment variables.
Changing them all just to connect to a different warehouse should be as easy as
setting a single environment variable.

A profile can be either **live** or **frozen**.
A live profile always checks the backing environment variables.
A frozen profile instance uses the values that were loaded before freezing and does not consult
the environment variables.

In a single codebase, one usually has a single object whose properties are consulted to get the
prop values of the active profile. The variables being consulted depend on the currently selected
profile of the particular type. Profiles of one type have a common **profile root**.
Profile root is the name that all environment variables backing this profile start with.

For example, a warehouse connection could be governed by a ``WarehouseProfile``.
In your code you would then refer to ``warehouse_profile``, a singleton of this class.
Profile root for this profile could be ``warehouse``. The active warehouse profile would be pointed to
by environment variable ``WAREHOUSE_PROFILE`` which holds the **name** of the active profile.
If this variable was set to ``"local_replica"``, then the properties of warehouse profile
would be loaded from environment variables that start with ``WAREHOUSE_LOCAL_REPLICA_``.
