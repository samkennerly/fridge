'''
fridge consists of container objects whose values can self-destruct
after a certain period of time. Like a cache, it's designed to store
data which should never be served if it's past its expiration date.

Right now, the module only contains two classes:

minifridge is a dict-like class with optional self-destruct timers.

cache_output is a decorator which caches outputs of function calls.

'''

import datetime as dt
from threading import Lock


class minifridge(object):
    
    '''
    A minifridge is like a dictionary, but with 2 extra rules:
    
    1. If another thread is using the fridge, then wait your turn.
    2. If you see something past its expiration date, then throw it out.
    
    Some minifridge methods allow users to set a countdown timer.
    These timers are set using keyword arguments for datetime.timedelta:
    weeks, days, hours, minutes, seconds, microseconds, milliseconds
    
    Examples:
    
    mf = minifridge(minutes=1)      # Make a fridge with 1-minute timer
    
    mf.put('spam',42,expire=False)  # Put spam in mf. It never expires
    mf.put('eggs',2,seconds=2)      # Put eggs in mf. It expires in 2 seconds.
    mf['beer'] = 100                # Put beer in mf. It expires in 1 minute.
    
    mf['spam']                      # Get value for key 'spam'
    mf.get('eggs',default='Nope')   # Get value without raising KeyError if key is bad
    mf.pop('beer',default=None)     # Pop value without raising KeyError if key is bad
    
    mf.keys()                       # Delete any bad items. Return the good keys.
    mf.purge()                      # Delete any expired (key,value) pairs
    mf.clear()                      # Delete everything 
    
    minifridge was inspired by (but is not a fork of) ExpiringDict.
    Unlike ExipringDict, minifridge does not use re-entrant locks.
    https://github.com/mailgun/expiringdict
    
    Caution: There are no built-in limits to size or number of elements.
    Caution: Not all dictionary methods have been implemented yet.
    Caution: Not well-tested yet, especially with multi-threading.
    ''' 

    @staticmethod
    def is_past(t):
        # Convenience function for figuring out if something has expired
        return ( (t is not None) and (t < dt.datetime.today()) )
    
    def __init__(self,**kwargs):
        # Initialize an empty dictionary with a lock and optional default timer.
        # Use timedelta kwargs to set default timer. Stored items will expire
        # after this much time unless specified otherwise. If no **kwargs,
        # then timer is set to roughly 100 years.
        
        self._contents  = dict()
        self.lock       = Lock() 
        if kwargs:
            self.default_timer = dt.timedelta(**kwargs)
        else:
            self.default_timer = None
    
    def __setitem__(self,key,value):
        # Put a (key,value) pair in the minifridge dictionary-style,
        # e.g. my_fridge['spam'] = 42. Use default timer.
        with self.lock:
            birth = dt.datetime.today()
            death = birth + self.default_timer
            self._contents[key] = (value,birth,death)
    
    def __getitem__(self,key):
        # Get a value from the minifridge dictionary-style.
        # If key is not found, this will throw a KeyError.
        # If key is found but expired, this with throw a KeyError.
        with self.lock:
            value,birth,death = self._contents[key]
            if self.is_past(death):
                del self._contents[key]
                raise KeyError(key)
            else:
                return value
    
    def __delitem__(self,key):
        # Delete (key,value) pair
        with self.lock:
            del self._contents[key]
    
    def __contains__(self,key):
        # Magic function for answering "x in minifridge" questions.
        # If key is not found, then return False.
        # If key is found but has expired, then throw it out!
        # If key is found and has not expired, then return True.
        with self.lock: 
            if not key in self._contents:
                return False
            else:
                value,birth,death = self._contents[key]
                if self.is_past(death):
                    del self._contents[key]
                    return False
                else:
                    return True
    
    def __len__(self):
        # How many keys?
        with self.lock:
            return len(self._contents)
    
    def put(self,key,value,expire=True,**kwargs):
        # Put a (key,value) pair in the minifridge with optional timer.
        # By default, it will expire after default_timer elapses.
        # To choose a different lifetime, use timedelta kwargs.
        # To prevent the item from expiring, use expire=False.

        with self.lock:

            # Remember creation time and calculate expiration time
            birth = dt.datetime.now()

            # Is this item invincible? If not, when does it expire?
            if not expire:
                death = None
            else:
                if kwargs:
                    death = birth + dt.timedelta(**kwargs)
                else:
                    death = birth + self.default_timer

            # Store value, creation time, and expiration time as a 3-tuple.
            self._contents[key] = (value,birth,death)
    
    def get(self,key,default=None):
        # Like __getitem__(), but does not raise a KeyError if key is bad.
        # Returns default value instead.    
        with self.lock:
            try:
                value,birth,death = self._contents[key]
                if self.is_past(death):
                    del self._contents[key]
                    return default
                else:
                    return value
            except KeyError:
                return default
    
    def set_expiration(self,key,expiration_time):
        # Instead of a countdown timer, set a specific expiration date.
        # expiration_time should be a datetime object.
        # Will raise a KeyError if key is not found.
        ''' TO DO: use pandas to_datetime() ? '''
        with self.lock:
            value,birth,death   = self._contents[key]
            self._contents[key] = value,birth,expiration_time
    
    def purge(self):
        # Throw out anything that has gone bad.
        with self.lock:
            contents = self._contents
            def is_dead(key):
                death = contents[key][2]
                return self.is_past(death)
            bad_keys = [ k for k in contents.keys() if is_dead(k) ]
            for k in bad_keys:
                del contents[k]
            self._contents = contents
    
    def keys(self):
        # Throw out anything that has gone bad.
        # Return a list of surviving keys.
        self.purge()
        with self.lock:
            return self._contents.keys()
    
    def values(self):
        # Throw out anything that has gone bad.
        # Return a list of surviving values.
        self.purge()
        with self.lock:
            return self._contents.values()
    
    def pop(self,key,default=None):
        # Pop a value: return it and delete it. Like get(), but
        # deletes (key,value) whether or not it has expired.
        with self.lock:
            try:
                value,birth,death = self._contents[key]
                if self.is_past(death):
                    value = default
                del self._contents[key]
                return value
            except:
                return default
    
    def clear(self):
        # Delete all (key,value) pairs
        with self.lock:
            self._contents.clear()
    


class cache_output(object):
    
    '''
    Class-based decorator used to avoid re-calculating a function.
    The first time the function is called, it initializes a minifridge.
    Each time the function is called, input arguments are hashed.
    The resulting hash is used as a minifridge key, and the outputs of
    calling the function are stored for a limited time.
    
    Set timer using keyword arguments for datetime.timedelta:
    weeks, days, hours, minutes, seconds, microseconds, milliseconds
    
    Example:
    
    @cache_output(hours=1)
    def cached_power_tower(x,N):
        for n in range(N):
            x *= x
        return x
    
    This function can be extremely slow for N > 30.
    If it's called again with the same arguments within 1 hour,
    then it will just get the previous answer from a minifridge.
    
    cache_output is almost identical to Scott Lobdell's Memoized decorator:
    http://scottlobdell.me/2015/04/decorators-arguments-python/
    except that it uses a minifridge instead of a deque for storage.
    
    WARNING: @cache_output stores *outputs* of a function.
    It does not replicate *side effects* of a function!

    Caution: Not well-tested yet, especially with multi-threading.
    '''

    @staticmethod
    def _convert_args_to_hash(args,kwargs):
        # Convert arguments to a string and hash it
        return hash(str(args)+str(kwargs))
    
    def __init__(self,**kwargs):
        # Create a minifridge with timer set by timedelta arguments
        self.mf = minifridge(**kwargs)
    
    def __call__(self,func,*args,**kwargs):
        
        def wrapper(*args,**kwargs):
            # Convert inputs to key. Is this key in minifridge?
            # If so, just look up the answer. If not, call the
            # function and store the result in minifridge.
            
            key = self._convert_args_to_hash(args,kwargs)            
            if key in self.mf:
                result = self.mf[key]
            else:
                result = func(*args,**kwargs)
                self.mf[key] = result
            
            return result
        
        return wrapper
    




''' BSD 3-clause license

Copyright (c) 2015, Sam Kennerly
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
