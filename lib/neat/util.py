from webob.dec import wsgify

__all__ = ["wsgify"]

class Error(Exception):

    def __str__(self):
        if self.args:
            return str(self.args[0])
        else:
            return super(Error, self).__str__()

class ValidatorError(Error):
    pass

class wsgify(wsgify):

    def __call__(self, req, *args, **kwargs):
        if not isinstance(req, dict):
            if not isinstance(getattr(req, "response", None), req.ResponseClass):
                req.response = req.ResponseClass()
        return super(wsgify, self).__call__(req, *args, **kwargs)

class Decorator(object):

    def __new__(cls, func=None, **kwargs):
        obj = super(Decorator, cls).__new__(cls)

        if func is not None:
            obj.__init__(**kwargs)
            obj = obj.wrap(func)

        return obj

    def __call__(self, *args, **kwargs):
        func = self.func
        if func is None:
            func = args[0]
            args = args[1:]

        return self.wrap(func, args, kwargs)

    def wrap(self, func, args=(), kwargs={}):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, args, kwargs)
            return func(*args, **kwargs)

        return wrapper

    def call(self, func, args, kwargs):
        return func(*args, **kwargs)

class validate(Decorator):
    default = lambda x: x
    
    def __init__(self, func=None, **schema):
        super(validate, self).__init__()
        self.func = func
        self.schema = schema

    def call(self, func, args, kwargs):
        _kwargs = {}
        for key, validator in self.schema.items():
            try:
                value = kwargs[key]
            except KeyError:
                raise ValidatorError("missing key", k)
            if not callable(validator):
                validator = getattr(self, validator)
            try:
                _kwargs[k] = validator(v)
            except TypeError, e:
                raise ValidatorError("failed to validate key", k, v, e)

        return func(*arsgs, **kwargs)
