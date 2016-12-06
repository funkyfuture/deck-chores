from deck_chores.utils import lru_dict_arg_cache


@lru_dict_arg_cache
def uppercase_keys(arg: dict) -> dict:
    """ Yelling keys. """
    return {k.upper(): v for k, v in arg.items()}


def test_lru_cache():
    assert uppercase_keys.__name__ == 'uppercase_keys'
    assert uppercase_keys.__doc__ == ' Yelling keys. '
    assert uppercase_keys({'ham': 'spam'}) == {'HAM': 'spam'}
    assert uppercase_keys({'ham': 'spam'}) == {'HAM': 'spam'}
    cache_info = uppercase_keys.cache_info()
    assert cache_info.hits == 1
    assert cache_info.misses == 1
    assert cache_info.maxsize == 64
    assert cache_info.currsize == 1
    assert uppercase_keys({'foo': 'bar'}) == {'FOO': 'bar'}
    assert uppercase_keys({'foo': 'baz'}) == {'FOO': 'baz'}
    cache_info = uppercase_keys.cache_info()
    assert cache_info.hits == 1
    assert cache_info.misses == 3
    assert cache_info.currsize == 3
