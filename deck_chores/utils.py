from functools import _lru_cache_wrapper, lru_cache, partial, update_wrapper
from functools import _CacheInfo  # type: ignore
import json
from typing import Any, Callable, Dict, Hashable, Tuple, Union
from uuid import NAMESPACE_OID, uuid5


def from_json(s: Union[bytes, str]) -> dict:
    if isinstance(s, bytes):
        s = s.decode()
    return json.loads(s)


@lru_cache(128)
def generate_id(*args) -> str:
    return str(uuid5(NAMESPACE_OID, ''.join(args)))


# dead code
def lru_dict_arg_cache(func: Callable) -> Callable:
    # TODO? wrapper that allows maxsize
    def unpacking_func(func: Callable, arg: frozenset) -> Any:
        return func(dict(arg))

    _unpacking_func = _lru_cache_wrapper(partial(unpacking_func, func),  # type: ignore
                                         64, False, _CacheInfo)

    def packing_func(arg: Dict[Hashable, Hashable]) -> Any:
        return _unpacking_func(frozenset(arg.items()))

    update_wrapper(packing_func, func)
    packing_func.cache_info = _unpacking_func.cache_info  # type: ignore
    return packing_func


def split_string(value: str, delimiter: str = ',', strip: bool = True,
                 sort: bool = False) -> Tuple[str, ...]:
    result = []
    for part in value.split(delimiter):
        if strip:
            result.append(part.strip())
        else:
            result.append(part)
    if sort:
        result.sort()
    return tuple(result)


def trueish(value: str) -> bool:
    return value.strip().lower() in ('1', 'on', 'true', 'yes')


__all__ = [from_json.__name__,
           lru_dict_arg_cache.__name__,
           split_string.__name__,
           trueish.__name__]
