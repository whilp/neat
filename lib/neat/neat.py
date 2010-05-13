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

	@wsgify
	def __call__(self, req):
		pass
