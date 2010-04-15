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
        :class:`webob.dec.wsgify` will automatically build *req* if
        passed the standard WSGI arguments (*environ*,
        *start_response*). :meth:`__call__` looks up the correct
        resource using :meth:`map`.
        """
        resource, args, kwargs = self.match(req)

        # XXX: It'd be nice to log a unique name for the method.
        try:
            response = resource(req, *args, **kwargs)
        except NotImplementedError:
            raise HTTPNotfound("Not implemented")

        return response

class Resource(object):
    """A resource.

    The :class:`Resource` models real data and state stored
    on the server and supports client interactions similar
    to those defined in the `Atom Publishing Protocol
    <http://bitworking.org/projects/atom/rfc5023.html#operation>`_.
    :class:`Resource` instances can be registered with a
    :class:`Service` to provide access to the resource model over WSGI
    (and therefore HTTP).

    A :class:`Resource` instance's methods should correspond to those registered
    in the :attr:`Service.methods` dictionary.
    """
    """The MIME type supported by this resource."""
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

    def match(self, req):
        return args, kwargs

    def url(self, *args, **kwargs):
        pass

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

    service = Service()
    lambda register = template, resources, *cls: \
        resources.extend(r(template) for r in cls)
    register("/records/(?P<member>\S+)", service.resources, JSONRecords))

    service = Service(
        JSONRecords("/records/(?P<member>\S+)")
    )

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
