from wr_profiles.envvar_profile import envvar_profile_cls


@envvar_profile_cls
class WarehouseProfile:
    profile_root = "warehouse"

    host: str = "localhost"
    username: str
    password: str
