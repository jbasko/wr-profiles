from wr_profiles import Profile, Property


class WarehouseProfile(Profile):
    profile_root = 'warehouse'

    host = Property('host', default='localhost')
    username = Property('username')
    password = Property('password')
