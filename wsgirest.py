import logging

from posixpath import dirname
from webob import Response, Request, exc

def parent(uri):
    """Return the parent of a URI.

    Here, a parent URI is similar to a POSIX parent directory.
    """
    return dirname(uri)

class Service(object):
    """A WSGI service.

    Services route HTTP requests to :class:`Resource` subclasses
    registered with the service. :class:`Service` is a valid WSGI
    application (see :meth:`__call__`); the registered resources should
    also be valid WSGI applications.

    When instantiating a :class:`Service`, the :class:`Resource`
    subclasses may be passed as arguments to the constructor. Otherwise,
    the :meth:`register` method may be called later to add other
    resources.
    """
    prefix = ""
    resources = {}
    """A dictionary mapping URIs to resources.

    Each key should be a URI that will be matched against the HTTP
    request's PATH_INFO environment variable. The values should be
    subclasses of :class:`Resource` (or something else that implements
    similar functionality). When a resource matches a requested URI, it
    will be instantiated and passed the standard WSGI arguments.
    """
    methods = {
        "member": dict(GET="retrieve", POST="replace", PUT="update", DELETE="delete"),
        "collection": dict(GET="list", POST="create"),
    }
    """A nested dictionary mapping HTTP methods to resource methods and types.

    The keys in the toplevel dictionary describes a type of resource
    (either "member" or "collection"). Those keys point to dictionaries
    mapping HTTP methods to methods of the :class:`Resource` that are
    appropriate for the resource type.
    """
    
    def __init__(self, *resources):
        logging.debug("Registered %d resources", len(resources))
        self.resources = {}
        self.register(*resources)
    
    def __call__(self, environ, start_response):
        """Route to a resource.

        This method makes the :class:`Service` a valid WSGI application.
        If :meth:`route` does not find a suitable resource, an
        :instance:`webob.exc.HTTPNotFound` instance will be returned.
        After the proper resource is found, :meth:`__call__` calls
        :meth:`dispatch` to find the appropriate method on the resource.
        Finally, the resource's method is called with the *environ* and
        *start_response* arguments and the result is returned.
        """
        req = Request(environ)
        notfound = ""
        resource = self.route(req)

        if resource is None:
            notfound = "No matching resource"
        else:
            resource = resource(req)

        method = self.dispatch(resource)
        if method is None:
            notfound = "No matching method"

        if notfound:
            return exc.HTTPNotFound(notfound)(environ, start_response)

        target = "%s.%s" % (method.im_class.__name__, method.im_func.func_name)
        try:
            response = method(*req.urlargs, **req.urlvars)
            logging.debug("Dispatching to %s with "
                "args=%s, kwargs=%s", target, req.urlargs,
                req.urlvars)
        except NotImplementedError:
            logging.debug("Resource method not implemented")
            response = exc.HTTPNotFound()
        except exc.HTTPException, e:
            response = e

        if response is None:
            response = resource.response
        elif isinstance(response, basestring):
            try:
                resource.response.unicode_body = response
            except TypeError:
                resource.response.body = response
            response = resource.response

        return resource.response(environ, start_response)

    def register(self, *resources):
        """Register *resources* with the service.

        Each resource should be a subclass of :class:`Resource` with a
        :attr:`Resource.uri` attribute; this URI will be set as the key
        for the resource in the :attr:`resources` dictionary.
        """
        self.resources.update([(r.uri, r) for r in resources])

    def route(self, request):
        """Route the *request* to the appropriate resource.

        :meth:`route` first checks that the *request*'s PATH_INFO
        falls under the :class:`Serivce`'s :attr:`prefix`. If not,
        :meth:`route` returns None. Otherwise, :meth:`route` first
        looks for a resource registered in :attr:`resources` that
        matches PATH_INFO (minus the Service prefix). If no resource
        matches, :meth:`route` computes the possible parent resource of
        the request (using :func:`parent`) and checks again. Finally,
        either the matching resource or None is returned.
        """
        uri = request.path_info
        if not uri.startswith(self.prefix):
            logging.debug("Request URI '%s' not in service prefix '%s'",
                uri, self.prefix)
            return None
        uri = uri[len(self.prefix):]

        # Look up the resource. If we don't find anything the first
        # time, we might have a request for a specific member, so check
        # compute its parent and check for that.
        resource = self.resources.get(uri, None)
        if resource is None:
            resource = self.resources.get(parent(uri), None)

        if resource is None:
            logging.debug("Routing request for '%s'", uri)

        return resource

    def dispatch(self, resource):
        """Dispatch the *request* to the appropriate method on *resource*.

        After :meth:`route` has found the matching resource for a
        request, :meth:`dispatch` chooses the appropriate method using
        the :attr:`methods` dictionary and returns it.
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
    """A WSGI resource.
 
    A Resource instance or subclass allows standard REST-like access
    to a resource. The methods implemented here correspond to the
    protocol operations defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.

    At instantiation, a :class:`webob.Request` instance should be passed
    to the :class:`Resource`. The REST methods may then be called with
    arguments and keyword arguments parsed from the Request instance.
    These methods return a :instance:`webob.Response` instance (which is
    a WSGI application).
    """
    uri = ""

    def __init__(self, request):
        self.request = request
        self.response = Response()

    def list(self):
        """List members of a collection."""
        pass

    def create(self):
        """Create a new member of a collection."""
        pass

    def retrieve(self, member):
        """Fetch a member."""
        pass

    def edit(self, member):
        """Edit or update a member."""
        pass

    def delete(self, member):
        """Remove and delete a member."""
        pass

    def replace(self, member):
        """Replace a member."""
        pass

class Records(Resource):
    uri = "/records"

def lala():
    logging.basicConfig(level=logging.DEBUG)
    s = Service(
        Records,
    )
    logging.basicConfig()
    r = Request.blank("/records/1")
    r.get_response(s)
    print r

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
