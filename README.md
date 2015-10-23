# fridge

fridge consists of container objects whose values can self-destruct
after a certain period of time. Like a cache, it's designed to store
data which should never be served if it's past its expiration date.

To use fridge, copy the 'fridge' folder to somewhere Python can find it.
Then type 'import fridge' at the top of your code.

Right now, the module only contains two classes:

# minifridge
is a dict-like class with optional self-destruct timers.
See /examples/minifridge.ipynb for examples.

# cache_output
is a decorator which caches outputs of function calls.
See /examples/cache_output.ipynb for examples.
