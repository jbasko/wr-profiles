import os

from wr_profiles import Profile, Property

# TODO consider sqlalchemy-like access to a bound property:
# profile = AppProfile()
# profile.p.username -- it's not profile.username (the value), but AppProfile.username yet bound to profile instance.


class AppProfile(Profile):
    profile_root = "app"

    host = Property(default="localhost")
    username = Property(default="root")
    password = Property()


class AppTestProfile(AppProfile):
    # This is how you tell that this profile must load the active profile based on APP_TEST_PROFILE envvar
    profile_activating_envvar = "APP_TEST_PROFILE"

    # This is how you customise inherited properties:
    host = AppProfile.password.replace(default="test-host")
    username = AppProfile.username.replace(default="test-username")
    password = AppProfile.password.replace(default="test-password")


profile = AppProfile()

# sandbox_profile = AppProfile.load("sandbox")
# sandbox_profile.set_prop_value("password", "sandbox-password")
# os.environ.update(sandbox_profile.to_envvars())  # TODO ability to exclude defaults?

test_profile = AppTestProfile.load("sandbox", is_live=True)
assert test_profile.host == 'test-host'
assert test_profile.username == 'test-username'
assert test_profile.password == 'test-password'

print(test_profile.to_dict())  # TODO ability to export str names instead of Property instances as names

os.environ["APP_SANDBOX_PASSWORD"] = "sandbox-password"
assert test_profile.password == "sandbox-password"

fully_live_test_profile = AppTestProfile()

os.environ["APP_TEST_PROFILE"] = "integration"
os.environ["APP_INTEGRATION_HOST"] = "int.localhost"

print(fully_live_test_profile.to_dict())
assert fully_live_test_profile.host == "int.localhost"
