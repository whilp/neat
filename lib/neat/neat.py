import logging
import os

from urllib import urlencode

from webob import Response, Request
from webob.acceptparse import Accept
from webob.exc import HTTPNotFound

from .util import wsgify

try:
    import json
except ImportError: # pragma: nocover
    import simplejson as json

__all__ = ["Resource", "Dispatch"]

def logger(cls):
    name = "%s.%s" % (__name__, cls.__class__.__name__)
    return logging.getLogger(name)

class Resource(object):
    prefix = ""

    @wsgify
    def __call__(self, req):
        pass

class Dispatch(object):
    resources = []

    def __init__(self, *resources):
        self.resources = list(resources)
    
    @wsgify
    def __call__(self, req):
        resource = self.match(req, self.resources)

    def match(self, req, resources):
        resource = None
        for resource in resources:
            if req.path_info.startswith(resource.prefix):
                break

        return resource
