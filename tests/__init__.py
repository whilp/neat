try:
    import unittest2 as unittest
except ImportError:
    import unittest

from webob import Request, Response

class BaseTest(unittest.TestCase):
    pass

class AppTest(BaseTest):
    application = None
    
    def app(self, *args, **kwargs):
        req = Request.blank(*args, **kwargs)

        return req.get_response(self.application)
