import logging
import os

from urllib import urlencode

import webob.exc
from webob import Response, Request
from webob.acceptparse import Accept

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

        if resource is None:
            raise webob.exc.HTTPNotFound("No resource matches the request")

        return resource(req)

    def match(self, req, resources):
        """Return the resource that matches *req*.

        *req* should be a :class:`webob.Request` instance; *resources* should be
        an iterable of :class:`Resource` subclasses. Returns None if no resource
        matches the request.

        A resource matches a request when the request's PATH_INFO starts with
        the resource's :attr:`prefix` string (first match wins).
        """
        resource = None
        for resource in resources:
            if req.path_info.startswith(resource.prefix):
                break

        return resource
