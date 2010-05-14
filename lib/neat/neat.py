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
    """The URI space for which this resource is responsible."""
    methods = {
        "GET": "get",
        "POST": "post",
        "PUT": "put",
        "DELETE": "delete",
        "HEAD": "head",
    }
    """Maps HTTP methods to local method base names.

    For example:

        GET -> get
        POST -> post
    """
    media = {}
    """Maps media types to local method suffixes.

    For example:
        
        text/html -> html
        application/vnd.my.resource+json -> json
    """
    extensions = {}
    """Maps URI file extensions to local method suffixes.

    For example:
        
        .html -> html
        .json -> json
	"""

    @wsgify
    def __call__(self, req):
        """Route a request to an appropriate method of the resource, returning a response.

        *req* is a :class:`webob.Request` instance (either provided by the
        caller or created by the :class:`webob.dec.wsgify` decorator). This
        method will first check the request's HTTP method, mapping it to a local
        method name using :attr:`methods`. If the request's PATH_INFO ends
        with an extension registered in :attr:`extensions`, the extension's
        handler will be used; otherwise, this method will try to match the
        request's Accept header (or Content-Type for PUT or POST) against
        handlers registered in :attr:`media`. If no handler can be found, this
        method raises an exception from :module:`webob.exc`.

        For example, a request made with the GET method and an Accept header (or
        PATH_INFO file extension) that matches the "html" handler will be
        dispatched to a method on the :class:`Resource` named "get_html". These
        methods take no arguments; the :class:`webob.Request` instance is
        available in the :attr:`request` attribute.
        """
        try:
            method = self.methods[req.method]
        except KeyError:
            raise webob.exc.HTTPMethodNotAllowed(
                "HTTP method '%s' is not supported" % req.method,
                headers={"Allow": ", ".join(self.methods.values())})

        root, ext = os.path.splitext(req.path_info)
        handler = self.extensions.get(ext, None)
        if handler is None:
            if req.method in ("POST", "PUT"):
                accept = Accept("Content-Type", req.content_type)
            else:
                accept = req.accept
            media = accept.best_match(self.media)
            handler = self.media.get(media, None)

        method = getattr(self, "%s_%s" % (method, handler), None)
        if  not callable(method):
            raise webob.exc.HTTPUnsupportedMediaType("No handler for response media type")

        if not hasattr(req, "response"):
            req.response = Response()
        self.req = req
        return method(req)

class Dispatch(object):
    """A WSGI application that dispatches to other WSGI applications.

    Incoming requests are passed to registered :class:`Resource` subclasses.
    Resources can be registered by passing them as arguments on initialization
    or by adding them to :attr:`resources` later.
    """
    resources = []
    """A list of :class:`Resource` subclasses."""

    def __init__(self, *resources):
        self.resources = list(resources)
    
    @wsgify
    def __call__(self, req):
        """Dispatch the request to a registered resource.

        *req* is a :class:`webob.Request` instance (created if necessary by the
        :class:`webob.dec.wsgify` decorator). This method calls :meth:`match` to
        find a matching resource; if none is found, it raises
        :class:`webob.exc.HTTPNotFound`. It then instantiates the matching :class:`Resource`
        subclass and calls it with the request.
        """
        resource = self.match(req, self.resources)

        if resource is None:
            raise webob.exc.HTTPNotFound("No resource matches the request")

        return resource(req)

    def match(self, req, resources):
        """Return the resource that matches *req*.

        *req* should be a :class:`webob.Request` instance; *resources* should be
        an iterable of :class:`Resource` subclasses. Returns None if no resource
        matches the request.

        A request matches if:
         
         * PATH_INFO ends in '/' and starts with the resource's
         :attr:`Resource.prefix` attribute; or
         * PATH_INFO is the same as the resource's :attr:`Resource.prefix`
         attribute.

        The first match wins.
        """
        resource = None
        for resource in resources:
            if resource.prefix.endswith('/'):
                matches = req.path_info.startswith(resource.prefix)
            else:
                matches = req.path_info == resource.prefix
            if matches:
                break

        return resource
