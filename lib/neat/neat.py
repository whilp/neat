import logging
import re

from posixpath import dirname

from webob import Response, Request, exc
from webob.dec import wsgify
from webob.exc import HTTPNotFound

try:
    import json
except ImportError:
    import simplejson as json

try:
    from mimeparse import best_match
except ImportError:
    best_match = False

class Service(object):
    """A WSGI service.

    Services route HTTP requests to resources (usually subclasses of
    :class:`Resource`) registered with the service. :class:`Service` is a WSGI
    application (see :meth:`__call__`); the registered resources should provide
    methods that also return WSGI applications.

    When instantiating a :class:`Service`, the resource objects may be passed as
    arguments to the constructor.

    """
    resources = []
    """A list of registered resource instances.

    Each resource should either subclass :class:`Resource` or implement
    its interface.
    """
    def __init__(self, *resources):
        logging.debug("Registered %d resources", len(resources))
        self.resources = list(resources)
    
    @wsgify
    def __call__(self, req):
        """Pass the request to a resource and return the response.

        *req* is a :class:`webob.Request` instance, though
        :class:`webob.dec.wsgify` will automatically build *req* if passed the
        standard WSGI arguments (*environ*, *start_response*). :meth:`__call__`
        looks up the correct resource using :meth:`match`.
        """
        match = self.match(req)
        if match is None:
            raise HTTPNotFound("Not implemented")
        method, args, kwargs = match

        # XXX: It'd be nice to log a unique name for the method.
        try:
            response = method(req, *args, **kwargs)
        except NotImplementedError:
            raise HTTPNotfound("Not implemented")

        return response

    def match(self, req):
        """Match a request to a resource.

        Returns the output of the first :meth:`Resource.match` call that does
        not return None. First match wins.
        """
        match = None
        for resource in self.resources:
            match = resource.match(req)
            if match is not None:
                break

        return match

class Resource(object):
    """A resource.

    The :class:`Resource` models real data and state stored
    on the server and supports client interactions similar
    to those defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.
    :class:`Resource` instances can be registered with a :class:`Service` to
    provide access to the resource model over WSGI (and therefore HTTP).

    A :class:`Resource` instance's methods should correspond to those registered
    in the :attr:`methods` dictionary.
    """
    methods = {
        "member": dict(GET="retrieve", POST="replace", PUT="update", DELETE="delete"),
        "collection": dict(GET="list", POST="create"),
    }
    """A nested dictionary mapping HTTP methods to resource types and methods.

    The keys in the toplevel dictionary describe a type of resource (either
    "member" or "collection"). Those keys point to dictionaries mapping HTTP
    methods to the names of methods that will be called on the resource.
    These methods should return WSGI applications.
    """
    mimetypes = {
    }
    """Dictionary of supported mimetypes.

    Values in this dictionary will be appended to base method names (see
    :attr:`methods`) when mapping requests to resource methods (see
    :meth:`match`).
    """
    collection = ""
    """The collection modeled by this resource."""

    def __init__(self, collection="", mimetypes={}):
        if collection:
            self.collection = collection
        if mimetypes:
            self.mimetypes = mimetypes

        try:
            self.setup()
        except NotImplementedError:
            pass

    def setup(self):
        raise NotImplementedError

    def match(self, req):
        """Match the resource to a request.

        Return (method, args, kwargs) if the request matches. *method* is the
        matching method on this resource; *args* is a tuple of positional
        arguments; *kwargs* is a dictionary of keyword arguments. *args* and
        *kwargs* can then be passed to *method* by the caller.

        A resource matches a request when: the first element in its path
        (:data:`req.path_info`) matches :attr:`collection; its HTTP method
        (:data:`req.method`) maps to a resource method in :attr:`methods`; and
        its Accept header (:data:`req.accept` or "*/*") matches a mimetype in
        :attr:`mimetypes`. If the request is for a member of the collection, the
        member portion of the path will be included in *args*. If any of the
        above criteria are not satisfied, :meth:`match` returns None.

        Since resource matching is controlled by the resource (and not the
        service), different resources can implement different strategies as long
        as they preserve the basic signature.
        """
        args = (); kwargs = {}
        path = req.path_info.strip('/')
        collection, _, resource = path.partition('/')
        if collection != self.collection:
            logging.debug("Collection '%s' does not match request path: '%s'",
                self.collection, path)
            return None
        elif resource:
            methodskey = "member"
            args = (resource,)
        else:
            methodskey = "collection"

        methods = self.methods.get(methodskey)
        method = methods.get(req.method, None)

        if method is None:
            logging.debug("Request path '%s' did not match any base method", path)
            return None

        logging.debug("Request path '%s' matched base method '%s'", path, method)

        accept = "*/*"
        if req.accept:
            accept = req.accept
        if best_match and self.mimetypes:
            mimetype = best_match(self.mimetypes, accept)
        else:
            full, _, params = accept.partition(';')
            full = full.strip()
            if full == '*': full = "*/*"
            mimetype = full

        suffix = self.mimetypes.get(mimetype, None)
        if suffix is None:
            return None
        elif suffix:
            method = '_'.join((method, suffix))

        _method = getattr(self, method, None)

        if not callable(_method):
            logging.debug("Request Accept header '%s' did not match any method",
                acccept)
            return None

        logging.debug("Request Accept header '%s' matched method '%s'",
            accept, method)

        return _method, args, kwargs

    def url(self, *args, **kwargs):
        raise NotImplementedError

    def list(self, req, *args, **kwargs):
        """List members of a collection."""
        raise NotImplementedError

    def create(self, req, *args, **kwargs):
        """Create a new member of a collection."""
        raise NotImplementedError

    def retrieve(self, req, *args, **kwargs):
        """Fetch a member."""
        raise NotImplementedError

    def edit(self, req, *args, **kwargs):
        """Edit or update a member."""
        raise NotImplementedError

    def delete(self, req, *args, **kwargs):
        """Remove and delete a member."""
        raise NotImplementedError

    def replace(self, req, *args, **kwargs):
        """Replace a member."""
        raise NotImplementedError

def serve():
    from wsgiref.simple_server import make_server

    service = Service()

    server = make_server("127.0.0.1", 8080, service)
    server.serve_forever()

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "serve":
        serve()
