import logging
import re

from posixpath import dirname

from webob import Response, Request, exc
from webob.dec import wsgify
from webob.exc import HTTPNotFound

class Service(object):
    """A WSGI service.

    Services route HTTP requests to resources (usually subclasses of
    :class:`Resource`) registered with the service. :class:`Service`
    is a valid WSGI application (see :meth:`__call__`); the registered
    resources should provide methods that return valid WSGI applications
    (see :attr:`methods`).

    When instantiating a :class:`Service`, the uninstantiated resources
    may be passed as arguments to the constructor. Otherwise, the
    :meth:`register` method may be called later to add other resources.
    """
    prefix = ""
    """URI prefix under which the Service's resources can be found.

    Request URIs that do not match this prefix will raise
    :class:`webob.exc.HTTPNotFound` errors.
    """
    resources = {}
    """A dictionary mapping URIs to resources.

    Each key should be a URI that will be matched against the HTTP
    request's PATH_INFO environment variable. The values should be
    subclasses of :class:`Resource` (or something else that implements
    similar functionality). When a resource matches a requested URI, it
    will be instantiated and passed the standard WSGI arguments. Note
    that the values of this dictionary should be classes, not instances.
    """
    methods = {
        "member": dict(GET="retrieve", POST="replace", PUT="update", DELETE="delete"),
        "collection": dict(GET="list", POST="create"),
    }
    """A nested dictionary mapping HTTP methods to resource methods and types.

    The keys in the toplevel dictionary describes a type of resource
    (either "member" or "collection"). Those keys point to dictionaries
    mapping HTTP methods to the names of methods that will be called on
    registered resources. These methods should return valid WSGI
    applications.
    """
    
    def __init__(self, *resources):
        logging.debug("Registered %d resources", len(resources))
        self.resources = list(resources)
    
    @wsgify
    def __call__(self, req):
        """Route to a resource.

        This method makes the :class:`Service` a valid WSGI application.
        If :meth:`route` does not find a suitable resource, an
        :class:`webob.exc.HTTPNotFound` instance will be returned.
        After the proper resource is found, :meth:`__call__` calls
        :meth:`dispatch` to find the appropriate method on the resource.
        Finally, the resource's method is called with the *environ* and
        *start_response* arguments and the resulting WSGI application is
        returned.
        """
        req, resource = self.route(req)
        if resource is None:
            raise HTTPNotFound("No matching resource")

        req, method = self.dispatch(req, resource)
        if method is None:
            raise HTTPNotFound("No matching method")

        target = "%s.%s.%s" % (method.im_class.__module__,
            method.im_class.__name__, method.im_func.func_name)
        logging.debug("Dispatching to %s with "
            "args=%s, kwargs=%s", target, req.urlargs,
            req.urlvars)

        try:
            response = method(req)
        except NotImplementedError:
            raise HTTPNotfound("Not implemented")

        return response

    def route(self, req):
        """Route the *req* to the appropriate resource.

        :meth:`route` first checks that the *request*'s PATH_INFO
        falls under the :class:`Serivce`'s :attr:`prefix`. If not,
        :meth:`route` returns None. Otherwise, :meth:`route` then
        looks for a resource registered in :attr:`resources` that
        matches PATH_INFO (minus the Service prefix). If no resource
        matches, :meth:`route` computes the possible parent resource of
        the request (using :func:`parent`) and checks again. Finally,
        either the matching resource or None is returned.
        """
        matches = {}
        for resource in self.resources:
            match = resource.template.match(req.path_info)
            if match:
                matches[resource] = match

        resources = matches.keys()
        if not resources:
            resource = None
        elif len(resources) == 1:
            resource = resources[0]
        else:
            supported = dict((getattr(r, "supported"), r) for r in resources)
            accept = best_match(supported, req.accept or "*/*")
            # We need to use .get() here because best_match() might
            # return '' (if no supported header matches).
            resource = supported.get(accept, None)

        return req, resource

    def dispatch(self, resource):
        """Dispatch to the appropriate method on *resource*.

        After :meth:`route` has found the matching resource for a
        request, :meth:`dispatch` chooses the appropriate method using
        the *resource*'s :attr:`Resource.request` attribute and the
        :attr:`methods` dictionary and returns the matching method.
        """
        req = resource.request
        req.urlargs, req.urlvars = (), {}

        resourcetype = "collection"
        if req.path_info != resource.uri:
            resourcetype = "member"
            req.urlargs = (req.path_info[len(resource.uri) + 1:],)

        methname = self.methods[resourcetype].get(req.method, None)
        if methname is None:
            logging.debug("Method %s not registered", methname)
            return None
        method = getattr(resource, methname, None)

        return method

class Resource(object):
    """A REST resource.

    A :class:`Resource` instance or subclass allows standard REST-like
    access to a HTTP resource. The methods implemented here correspond
    to the protocol operations defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.

    On instantiation, a :class:`webob.Request` instance should be passed
    to the :class:`Resource`. The REST methods may then be called with
    arguments and keyword arguments parsed from the Request instance.
    These methods return a :instance:`webob.Response` instance (which is
    a WSGI application).
    """
    template = ""
    """A URI template."""
    supported = []
    """A list of supported MIME types."""

    def __init__(self, uri="", supported=[]):
        if uri:
            self.uri = re.compile(uri)
        if supported:
            self.supported = supported

    def list(self):
        """List members of a collection."""
        raise NotImplementedError

    def create(self):
        """Create a new member of a collection."""
        raise NotImplementedError

    def retrieve(self, member):
        """Fetch a member."""
        raise NotImplementedError

    def edit(self, member):
        """Edit or update a member."""
        raise NotImplementedError

    def delete(self, member):
        """Remove and delete a member."""
        raise NotImplementedError

    def replace(self, member):
        """Replace a member."""
        raise NotImplementedError

class Records(Resource):
    uri = "/records"

def lala():
    logging.basicConfig(level=logging.DEBUG)
    s = Service(
        Records,
    )
    logging.basicConfig()
    request = Request.blank("/records/1")
    response = request.get_response(s)
    print response

def serve():
    from wsgiref.simple_server import make_server

    service = Service()

    server = make_server("127.0.0.1", 8080, service)
    server.serve_forever()

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "serve":
        serve()
    else:
        lala()
