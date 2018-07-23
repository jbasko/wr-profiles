**TODO** Already out of date!

## Profile

A **profile** represents a set of configurable **properties** of a single service
backed by environment variables.

There can be multiple unrelated profiles (multiple classes extending `Profile` class),
each providing interface to properties of a different service.

Instances of profiles associated with the same service share the same base class and are identified by
`profile_root` specified in that base class. Is is the root from which all relevant 
environment variable names are formed.

Profiles of unrelated services do not share any information.
In the discussion below, different instances or kinds of profiles all relate to the same service,
e.g. same `profile_root`.

##### Warehouse Profile (Example)

In the discussion below, we will use a profile for a data warehouse access as an example.
Class `WarehouseProfile` declares the profile and the properties it provides.
Object `warehouse_profile` is the single instance through which user must look up service's
active configuration.

    class WarehouseProfile(Profile):
        profile_root = 'warehouse'
        
        host = Property(default='localhost')
        username = Property()
        password = Property(default='')
    
    warehouse_profile = WarehouseProfile()

##### Profile Name

Individual instances of profiles are identified by their name (`profile_name` property).

##### Active Profile

The **active profile** is the profile of a service that should be used 
according to the environment variables.

The active profile can be switched by setting a special environment variable
`<PROFILE_ROOT>_PROFILE`. For `WarehouseProfile` that would be `WAREHOUSE_PROFILE`.

If this variable is not set, the active profile consults environment variables in the
form:

    <PROFILE_ROOT>_<PROPERTY_NAME>

For example, `WAREHOUSE_HOST`.

If `<PROFILE_ROOT>_PROFILE` is set then the active profile consults environment variables in the form:

    <PROFILE_ROOT>_<PROFILE_NAME>_<PROPERTY_NAME>

For example, if `WAREHOUSE_PROFILE` is set to `staging` then `host` property will be looked up
under `WAREHOUSE_STAGING_HOST`.

##### Parent Profile

Any particular profile (for example, `staging` profile of `WarehouseProfile`) can be instructed
to inherit its property values from a **parent profile** by setting:

    <PROFILE_ROOT>_<PROFILE_NAME>_PARENT_PROFILE

For example, `WAREHOUSE_STAGING_PARENT_PROFILE`, if set to `production`, would mean that
if environment variable `WAREHOUSE_STAGING_HOST` was not set, property value loader would
consult `WAREHOUSE_PRODUCTION_HOST` instead. And only if that variable was not present,
the default value of the property (if available) would be used.

*Limitation*: The default profile (`profile_name=""`) cannot be used as a parent profile.
If you specify empty string as `<PROFILE_ROOT>_<PROFILE_NAME>_PARENT_PROFILE` then this
profile won't have any parent profile. It is the same as having no value set. 

##### Live Profile vs Frozen Profile

A **live** profile always consults environment variables (`os.environ`).
A **frozen** profile provides values based on profile defaults and values previously loaded (`_frozen_values`).
A frozen profile consults environment variables only when `load()` method is called.

##### Property Value Resolution Order (for Live Profile)

**TODO** Update

If `WAREHOUSE_PROFILE` was set to `staging` and `WAREHOUSE_STAGING_PARENT_PROFILE` was set to
`production`, value of `warehouse_profile.host` would be looked up from multiple sources.
The first discovered value would be returned and sub-sequent sources would not be consulted.

 1. `os.environ['WAREHOUSE_STAGING_HOST']`
 2. `os.environ['WAREHOUSE_PRODUCTION_HOST']`
 3. `warehouse_profile.defaults['host']` (instance-associated defaults)
 4. `WarehouseProfile.host.default`

If no value was to be found (note that `Property.default` is not necessarily set),
a `KeyError('host')` would be raised.

##### Property Value Resolution Order (for Frozen Profile)

**TODO** Update

 1. `warehouse_profile._const_values['host']`
 1. `warehouse_profile._frozen_inherited_values['host']`
 2. `warehouse_profile.defaults['host']`
 3. `WarehouseProfile.host.default`

If no value is found, `KeyError('host')` is raised.

### API

##### `Profile().to_dict()`

Generates a dictionary of property values that would represent the current
state of the profile.

##### `Profile().to_envvars()`

Generates a dictionary of environment variables that would represent the
current state of the profile.

Note that there are many ways to represent the same state due to profile inheritance.
This returns the most straight-forward (not necessarily the most efficient in terms of
number of environment variables used) specification.
