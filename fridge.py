'''
MiniFridge is a dict-like class with optional self-destruct timers.
CacheOutput is a decorator which caches outputs of function calls.
'''

import datetime as dt
from threading import Lock


class MiniFridge(object):
    
    '''
    A MiniFridge is like a dictionary, but with 2 extra rules:
    
    1. If another thread is using the fridge, then wait your turn.
    2. If you see something past its expiration date, then throw it out.
    
    Some MiniFridge methods allow users to set a countdown timer.
    These timers are set using keyword arguments for datetime.timedelta:
    weeks, days, hours, minutes, seconds, microseconds, milliseconds
    
    Examples:
    
    mf = MiniFridge(minutes=1)      # Make a MiniFridge with 1-minute timer
    
    mf.put('spam',42,expire=False)  # Put spam in mf. It never expires
    mf.put('eggs',2,seconds=2)      # Put eggs in mf. It expires in 2 seconds.
    mf['beer'] = 100                # Put beer in mf. It expires in 1 minute.
    
    mf['spam']                      # Get value for key 'spam'
    mf.get('eggs',default='Nope')   # Get value without raising KeyError if key is bad
    mf.pop('beer',default=None)     # Pop value without raising KeyError if key is bad
    
    mf.keys()                       # Delete any bad items. Return the good keys.
    mf.purge()                      # Delete any expired (key,value) pairs
    mf.clear()                      # Delete everything 
        
    Caution: There are no built-in limits to size or number of elements.
    Caution: Not all dictionary methods have been implemented yet.
    Caution: Not well-tested yet, especially with multi-threading.
    ''' 

    @staticmethod
    def is_past(t):
        ''' Convenience function for figuring out if something has expired '''
        return ( (t is not None) and (t < dt.datetime.today()) )
    
    def __init__(self,**kwargs):
        '''
        Initialize an empty dictionary with a lock and optional default timer.
        Use timedelta kwargs to set default timer. Stored items will expire
        after this much time unless specified otherwise. If no **kwargs,
        then timer is set to roughly 100 years.
        '''
        
        self._contents  = dict()
        self.lock       = Lock() 
        if kwargs:
            self.default_timer = dt.timedelta(**kwargs)
        else:
            self.default_timer = None
    
    def __setitem__(self,key,value):
        ''' Put a (key,value) pair in the MiniFridge dictionary-style '''

        with self.lock:
            birth = dt.datetime.today()
            death = birth + self.default_timer
            self._contents[key] = (value,birth,death)
    
    def __getitem__(self,key):
        '''
        Get a value from the MiniFridge dictionary-style.
        If key is not found, this will throw a KeyError.
        If key is found but expired, this with throw a KeyError.
        '''

        with self.lock:
            value,birth,death = self._contents[key]
            if self.is_past(death):
                del self._contents[key]
                raise KeyError(key)
            else:
                return value
    
    def __delitem__(self,key):
        ''' Delete (key,value) pair '''

        with self.lock:
            del self._contents[key]
    
    def __contains__(self,key):
        '''
        Magic function for answering "x in MiniFridge" questions.
        If key is not found, then return False.
        If key is found but has expired, then throw it out! Return False.
        If key is found and has not expired, then return True.
        '''

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
        ''' How many items are in the fridge? '''

        with self.lock:
            return len(self._contents)
    
    def put(self,key,value,expire=True,**kwargs):
        '''
        Put a (key,value) pair in the MiniFridge with optional timer.
        By default, it will expire after default_timer elapses.
        To choose a different lifetime, use timedelta kwargs.
        To set lifetime to infinity, use expire=False.
        '''

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
        '''
        Like __getitem__(), but does not raise a KeyError if key is bad.
        Returns default value instead.
        '''

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
        '''
        Instead of a countdown timer, set a specific expiration date.
        expiration_time should be a datetime object.
        Will raise a KeyError if key is not found.
        '''

        with self.lock:
            value,birth,death   = self._contents[key]
            self._contents[key] = value,birth,expiration_time
    
    def purge(self):
        ''' Throw out anything that has expired '''

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
        '''
        Throw out anything that has expired.
        Return whatever keys are left.
        '''

        self.purge()
        with self.lock:
            return self._contents.keys()
    
    def values(self):
        '''
        Throw out anything that has expired.
        Return whatever values are left.
        '''

        self.purge()
        with self.lock:
            return self._contents.values()
    
    def pop(self,key,default=None):
        '''
        Pop a value: return it and delete it. Like get(), but
        deletes (key,value) whether or not it has expired.
        '''

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
        ''' Delete all (key,value) pairs '''

        with self.lock:
            self._contents.clear()
    


class CacheOutput(object):
    
    '''
    Class-based decorator used to avoid re-calculating a function.
    The first time the function is called, it initializes a MiniFridge.
    Each time the function is called, input arguments are hashed.
    The resulting hash is used as a MiniFridge key, and the outputs of
    calling the function are stored for a limited time.
    
    Set timer using keyword arguments for datetime.timedelta:
    weeks, days, hours, minutes, seconds, microseconds, milliseconds
    
    Example:
    
    @CacheOutput(hours=1)
    def cached_power_tower(x,N):
        for n in range(N):
            x *= x
        return x
    
    WARNING: @CacheOutput stores *outputs* of a function.
    It does not replicate *side effects* of a function!

    Caution: Not well-tested yet, especially with multi-threading.
    '''

    @staticmethod
    def _convert_args_to_hash(args,kwargs):
        ''' Convert arguments to a string and hash it '''
        return hash(str(args)+str(kwargs))
    
    def __init__(self,**kwargs):
        ''' Create a MiniFridge with timer set by timedelta arguments '''

        self.fridge = MiniFridge(**kwargs)
    
    def __call__(self,func,*args,**kwargs):
        
        def wrapper(*args,**kwargs):
            '''
            Convert inputs to key. Is this key in MiniFridge?
            If so, just look up the answer. If not, call the
            function and store the result in MiniFridge.
            '''
            
            key = self._convert_args_to_hash(args,kwargs)            
            if key in self.fridge:
                result = self.fridge[key]
            else:
                result = func(*args,**kwargs)
                self.fridge[key] = result
            
            return result
        
        return wrapper



