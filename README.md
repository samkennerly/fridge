# fridge

fridge objects are key-value stores which automatically delete data which is past its expiration date.

## MiniFridge
**dictionary with optional self-destruct timers**

`MiniFridge` is similar to [ExpiringDict](https://github.com/mailgun/expiringdict) but does not use re-entrant locks.  
See the [minifridge](https://github.com/samkennerly/fridge/blob/master/minifridge.ipynb) demo notebook for examples.

## CacheOutput
**class-based function decorator which caches outputs of function calls**  
`CacheOutput` is similar to Scott Lobdell's [Memoized](http://scottlobdell.me/2015/04/decorators-arguments-python/) but with a `MiniFridge` instead of `deque` for storage.  
See the [cache_output](https://github.com/samkennerly/fridge/blob/master/cache_output.ipynb) demo notebook for examples.

