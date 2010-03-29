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
    
    def __init__(self, *resources):
        logging.debug("Registered %d resources", len(resources))
        self.resources = {}
        self.register(*resources)
    
    def __call__(self, environ, start_response):
        """Dispatch to a resource.

        This method makes the :class:`Service` a valid WSGI application.
        If :meth:`dispatch` does not find a suitable resource, an
        :instance:`webob.exc.HTTPNotFound` instance will be returned.
        """
        req = Request(environ)
        resource = self.dispatch(req)
        if resource is None:
            return exc.HTTPNotFound()(environ, start_response)
        return resource(req)(environ, start_response)

    def register(self, *resources):
        """Register *resources* with the service.

        Each resource should be a subclass of :class:`Resource` with a
        :attr:`Resource.uri` attribute; this URI will be set as the key
        for the resource in the :attr:`resources` dictionary.
        """
        self.resources.update([(r.uri, r) for r in resources])

    def dispatch(self, request):
        """Route the *request* to the appropriate resource.

        :meth:`dispatch` first checks that the *request*'s PATH_INFO
        falls under the :class:`Serivce`'s :attr:`prefix`. If not,
        :meth:`dispatch` returns None. Otherwise, :meth:`dispatch` first
        looks for a resource registered in :attr:`resources` that
        matches PATH_INFO (minus the Service prefix). If no resource
        matches, :meth:`dispatch` computes the possible parent resource of
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
            logging.debug("Dispatching request for '%s'", uri)

        return resource

class Resource(object):
    """A WSGI resource.

    A Resource is a valid WSGI application that allows standard
    REST-like access to a resource. The methods implemented here correspond
    to the protocol operations defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.

    At instantiation, a :class:`webob.Request` instance should be passed
    to the :class:`Resource`. When called, the :class:`Resource` will
    parse the Request to determine the appropriate method to call.
    """
    uri = ""
    methods = {
        "member": dict(GET="retrieve", POST="replace", PUT="update", DELETE="delete"),
        "collection": dict(GET="list", POST="create"),
    }

    def __init__(self, request):
        self.request = request
        self.response = None
    
    def __call__(self, environ, start_response):
        req = self.request
        req.urlargs, req.urlvars = (), {}

        resource = "collection"
        if req.path_info != self.uri:
            resource = "member"
            req.urlargs = (req.path_info[len(self.uri) + 1:],)

        methname = self.methods[resource].get(req.method, None)
        if methname is None:
            logging.debug("Method %s not registered", methname)
            return exc.HTTPNotFound()(environ, start_response)
        method = getattr(self, methname)

        try:
            logging.debug("Dispatching to method %s with "
                "args=%s, kwargs=%s", methname, req.urlargs,
                req.urlvars)
            response = method(*req.urlargs, **req.urlvars)
        except NotImplementedError:
            logging.debug("Method %s not implemented", methname)
            response = exc.HTTPNotFound()
        except exc.HTTPException, e:
            response = e

        if response is None:
            response = ''
        if isinstance(response, basestring):
            response = Response(body=response)

        return response(environ, start_response)
            
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
