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

class NoMatch(Exception):
    pass

class Dispatch(object):
    """A WSGI service.

    Dispatchs route HTTP requests to resources (usually subclasses of
    :class:`Resource`) registered with the service. :class:`Dispatch` is a WSGI
    application (see :meth:`__call__`); the registered resources should provide
    methods that also return WSGI applications.

    When instantiating a :class:`Dispatch`, the resource objects may be passed as
    arguments to the constructor.
    """

    resources = []
    """A list of registered resource instances.

    Each resource should either subclass :class:`Resource` or implement
    its interface.
    """

    def __init__(self, *resources):
        self.log = logger(self)
        self.log.debug("Registered %d resources", len(resources))
        self.resources = list(resources)
    
    @wsgify
    def __call__(self, req):
        """Pass the request to a resource and return the response.

        *req* is a :class:`webob.Request` instance, though
        :class:`webob.dec.wsgify` will automatically build *req* if passed the
        standard WSGI arguments (*environ*, *start_response*). :meth:`__call__`
        looks up the correct resource using :meth:`match`.
        """
        req, match = self.match(req)
        if match is None:
            raise HTTPNotFound("Not implemented")

        name = match.im_func.func_name
        self.log.debug("Dispatching request to method %s", name)
            
        try:
            response = match(req)
        except NotImplementedError:
            self.log.debug("Method %s is not implemented", name)
            raise HTTPNotFound("Not implemented")

        return response

    def match(self, req):
        """Match a request to a resource.

        Returns the output of the first :meth:`Resource.match` call that does
        not raise :class:`NoMatch`. First match wins.
        """
        match = None
        backup = req.copy()
        self.log.debug("Matching %s", str(req).strip().replace('\n', '; '))
        for resource in self.resources:
            try:
                match = resource.match(req)
                self.log.debug("Resource %s matched request", resource)
                break
            except NoMatch, e:
                self.log.debug("Resource %s did not match request: %s", resource, e)
                req = backup

        return req, match

    def url(self, collection, *args, **kwargs):
        """Generate a URL for *collection*.

        *collection* is a string matching a :attr:`~Resource.collection`
        attribute of a :class:`Resource` registered with the :class:`Dispatch`.
        *args* and *kwargs* are passed to :class:`Resource.url`. Returns None if
        no :class:`Resource` matches.
        """
        match = None
        for resource in self.resources:
            if resource.collection == collection:
                match = resource
                break

        if match is None:
            return None

        return resource.url(*args, **kwargs)

class Resource(object):
    """A resource.

    The :class:`Resource` models real data and state stored
    on the server and supports client interactions similar
    to those defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.
    :class:`Resource` instances can be registered with a :class:`Dispatch` to
    provide access to the resource model over WSGI (and therefore HTTP).

    A :class:`Resource` instance's methods should correspond to those registered
    in the :attr:`methods` dictionary.
    """

    extensions = {}
    """A dictionary mapping path extensions to mimetypes.

    Keys here should match *ext* as returned by :func:`os.path.splitext` when
    called on an incoming :attr:`Request.path_info`. Values should be mimetypes
    that are also registered in the :attr:`mimetypes` dictionary.
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
        self.log = logger(self)
        if collection:
            self.collection = collection
        m = {}
        m.update(self.mimetypes, **mimetypes)
        self.mimetypes = m

        try:
            self.setup()
        except NotImplementedError:
            pass

    def __str__(self):
        return self.__class__.__name__

    def setup(self):
        """Set up the resource.

        Provided as a convenience so that subclasses don't have to override
        :meth:`__init__`.
        """
        raise NotImplementedError

    def match(self, req):
        """Match the resource to a request.

        Returns a method of this resource instance if the request matches.

        If :attr:`req.path_info` ends with an extension registered in
        :attr:`extensions`, the extension will be removed from the path and the
        matching mimetype will be used in place of the request's Accept header.
        This allows clients to request different representations without having
        to set the Accept header.

        A resource matches a request when: the first element in its path
        (:data:`req.path_info`) matches :attr:`collection; its HTTP method
        (:data:`req.method`) maps to a resource method in :attr:`methods`; and
        its Accept header (:data:`req.accept` or "*/*") matches a mimetype in
        :attr:`mimetypes`. If any of the above criteria are not satisfied,
        :meth:`match` raises :class:`NoMatch`.

        Since resource matching is controlled by the resource (and not the
        service), different resources can implement different strategies as long
        as they preserve the basic signature.
        """
        root, ext = os.path.splitext(req.path_info)
        mimetype = self.extensions.get(ext, None)
        if mimetype is not None:
            req.path_info = root

        collection = req.path_info_peek()

        if collection == self.collection:
            methodskey = "collection"
            req.path_info_pop()
        else:
            raise NoMatch("Collection does not match")

        if req.path_info_peek():
            methodskey = "member"

        accept = req.accept
        if req.method in ("PUT", "POST"):
            accept = Accept("Content-Type", req.content_type)
        if mimetype is not None:
            accept = Accept("Accept", mimetype)

        methodname = self.methods[methodskey].get(req.method, None)

        if methodname is None:
            raise NoMatch("HTTP method does not match")

        mimetype = accept.best_match(self.mimetypes)
        suffix = self.mimetypes.get(mimetype, None)
        if suffix:
            methodname = '_'.join((methodname, suffix))

        method = getattr(self, methodname, None)

        if not callable(method):
            raise NoMatch("Accept header does not match a method")

        return method

    def url(self, member=None, **kwargs):
        """Generate a URL for the resource.

        If *member* is not None, a URL pointing to the member will be generated.
        Otherwise, the URL will point to the collection. If *kwargs* is present,
        it will be urlencoded and appended to the resulting URL as GET
        parameters.
        """
        url = self.collection
        if member is not None:
            url = '/'.join((url, member))

        if kwargs:
            url = '?'.join((url, urlencode(kwargs)))

        return url

    def list(self, req, *args, **kwargs): # pragma: nocover
        """List members of a collection."""
        raise NotImplementedError

    def create(self, req, *args, **kwargs): # pragma: nocover
        """Create a new member of a collection."""
        raise NotImplementedError

    def retrieve(self, req, *args, **kwargs): # pragma: nocover
        """Fetch a member."""
        raise NotImplementedError

    def edit(self, req, *args, **kwargs): # pragma: nocover
        """Edit or update a member."""
        raise NotImplementedError

    def delete(self, req, *args, **kwargs): # pragma: nocover
        """Remove and delete a member."""
        raise NotImplementedError

    def replace(self, req, *args, **kwargs): # pragma: nocover
        """Replace a member."""
        raise NotImplementedError
