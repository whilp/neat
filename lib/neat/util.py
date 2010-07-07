from webob.dec import wsgify

__all__ = ["validate", "validator", "wsgify"]

try:
    from functools import wraps
except ImportError:
    def update_wrapper(wrapper, wrapped):
        for attr in "module name doc".split():
            attr = "__%s__" % attr
            setattr(wrapper, attr, getattr(wrapped, attr))
        for attr in "dict".split():
            attr = "__%s__" % attr
            getattr(wrapper, attr).update(getattr(wrapped, attr, {}))

        return wrapper

    def wraps(wrapped):
        return partial(update_wrapper, wrapped=wrapped)

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

class validator(Decorator):

    def call(self, func, args, kwargs):
        instance = args[0]
        exception = getattr(instance, "exception", None)
        excs = getattr(instance, "excs", None)
        if excs is None:
            excs = (TypeError, ValueError)
        try:
            return func(*args, **kwargs)
        except Exception, e:
            if exception is not None and isinstance(e, excs):
                raise exception(e.args[0])
            raise

class validate(Decorator):
    default = lambda x: x
    
    def __init__(self, func=None, **schema):
        super(validate, self).__init__()
        self.func = func
        self.schema = schema

    def call(self, func, args, kwargs):
        varnames = self.getvarnames(func)
        args, kwargs = self.validate(self.schema, varnames, args, kwargs)

        return func(*args, **kwargs)

    def validate(self, schema, varnames, args, kwargs):
        _kwargs = {}
        args = list(args)
        for key, validator in schema.items():
            index = None
            try:
                value = kwargs[key]
            except KeyError:
                # Let the wrapped method raise TypeError if the key isn't in
                # kwargs or args.
                try:
                    index = varnames.index(key)
                    value = args[index]
                except (IndexError, ValueError):
                    continue

            value = validator(value)

            if index is not None:
                args[index] = value
            else:
                _kwargs[key] = value

        return args, _kwargs

    def getvarnames(self, func):
        try:
            code = func.im_func.func_code
        except AttributeError:
            code = func.func_code

        return code.co_varnames
