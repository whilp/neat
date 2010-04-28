from webob.dec import wsgify

__all__ = ["wsgify"]

class wsgify(wsgify):

    def __call__(self, req, *args, **kwargs):
        if not isinstance(req, dict):
            if not isinstance(getattr(req, "response", None), req.ResponseClass):
                req.response = req.ResponseClass()
        return super(wsgify, self).__call__(req, *args, **kwargs)
