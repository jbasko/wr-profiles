class _NotSet:
    """
    Not set value marker.
    Do not use directly, instead use the NotSet instance.
    """
    def __bool__(self):
        return False


NotSet = _NotSet()
