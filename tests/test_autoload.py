from wr_profiles import Profile


def test_autoload(monkeypatch):
    env = {
        'HELLO_PROFILE': 'sandbox',
        'HELLO_SANDBOX_HOST': 'sandbox.localhost',
        'HELLO_SANDBOX_USER_NAME': 'sandbox-username',
        'HELLO_PROD_HOST': 'production.localhost',
        'HELLO_PROD_PASSWORD': 'ProductionSecrets',
    }

    for k, v in env.items():
        monkeypatch.setenv(k, v)

    hello_profile = Profile.autoload(profile_root='hello', profile_names=['sandbox', 'prod'])
    assert isinstance(hello_profile, Profile)

    props = set(hello_profile.props)
    assert len(props) == 3
    assert hello_profile.has_prop('host')
    assert hello_profile.has_prop('user_name')
    assert hello_profile.has_prop('password')
    assert not hello_profile.has_prop('something_else')

    sandbox = hello_profile.load_custom('sandbox')
    assert sandbox.host == 'sandbox.localhost'
    assert sandbox.user_name == 'sandbox-username'
    assert sandbox.password is None

    prod = hello_profile.load_custom('prod')
    assert prod.host == 'production.localhost'
    assert prod.user_name is None
    assert prod.password == 'ProductionSecrets'

    assert sandbox.is_active
    assert not prod.is_active
