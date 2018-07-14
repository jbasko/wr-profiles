*****************************
wr-profiles
*****************************

.. code-block:: shell

    pip install wr-profiles

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
