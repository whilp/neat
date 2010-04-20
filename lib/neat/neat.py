import logging

from webob import Response, Request
from webob.dec import wsgify
from webob.exc import HTTPNotFound

try:
    import json
except ImportError: # pragma: nocover
    import simplejson as json

try:
    from mimeparse import best_match
except ImportError: # pragma: nocover
    best_match = False

__all__ = ["Resource", "Service"]

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
        name = "%s.%s" % (method.im_class.__name__, method.im_func.func_name)

        try:
            response = method(req, *args, **kwargs)
        except NotImplementedError:
            raise HTTPNotFound("Not implemented")

        logging.debug("Dispatching request to %s(req, *%s, **%s)", name, args, kwargs)
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

    def url(self, collection, *args, **kwargs):
        """Generate a URL for *collection*.

        *collection* is a string matching a :attr:`~Resource.collection`
        attribute of a :class:`Resource` registered with the :class:`Service`.
        *args* and *kwargs* are passed to :class:`Resource.url`. Returns None if
        no :class:`Resource` matches.
        """
        resource = None
        for resource in self.resources:
            if resource.collection == collection:
                break

        if resource is None:
            return None

        return resource.url(*args, **kwargs)

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
        "*/*": "",
    }
    """Dictionary of supported mimetypes.

    Values in this dictionary will be appended to base method names (see
    :attr:`methods`) when mapping requests to resource methods (see
    :meth:`match`). By default, all requests are routed directly to the base
    methods (ie, no suffix is appended).
    """

    collection = ""
    """The collection modeled by this resource."""

    best_match = staticmethod(best_match)

    def __init__(self, collection="", mimetypes={}):
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
            logging.debug("Resource '%s' does not match request path: '%s'",
                self, req.path_info)
            return None
        elif resource:
            methodskey = "member"
            args = (resource,)
        else:
            methodskey = "collection"

        logging.debug("Resource '%s' matches request path: '%s'",
            self, req.path_info)

        methods = self.methods.get(methodskey)
        method = methods.get(req.method, None)

        if method is None:
            logging.debug("Request path '%s' did not match any base method "
                "on resource '%s'", req.path_info, self)
            return None

        logging.debug("Request path '%s' matched base method '%s' "
            "on resource '%s'", req.path_info, method, self)

        accept = "*/*"
        if req.accept:
            accept = str(req.accept)
        if self.best_match and self.mimetypes:
            mimetype = self.best_match(self.mimetypes, accept)
        else:
            full, _, params = accept.partition(';')
            full = full.strip()
            if full == '*': full = "*/*"
            mimetype = full

        suffix = self.mimetypes.get(mimetype, None)
        if suffix is None:
            logging.debug("Request mimetype '%s' not supported by resource '%s'", 
                mimetype, self)
            return None
        elif suffix:
            method = '_'.join((method, suffix))

        _method = getattr(self, method, None)

        if not callable(_method):
            logging.debug("Request Accept header '%s' did not match any method "
                "on resource '%s'", accept, self)
            return None

        logging.debug("Request Accept header '%s' matched method '%s' "
            "on resource '%s'", accept, method, self)

        return _method, args, kwargs

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

    def list(self, req, *args, **kwargs):
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
