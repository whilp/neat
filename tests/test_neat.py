from tests import AppTest, BaseTest, log

from neat.neat import Resource, Service

try:
    import json
except ImportError:
    import simplejson as json

class ServiceTest(AppTest):

    def setUp(self):
        class Empty(Resource):
            collection = "empty"

        class Minimal(Resource):
            collection = "minimal"

            def list(self, req):
                pass

        class Content(Resource):
            collection = "content"
            mimetypes = {
                "application/javascript": "json",
                "text/plain": "text",
            }

            def list(self, req):
                return [{"name": "a"}, {"name": "b"}]

            def list_text(self, req):
                req.response.content_type = "text/plain"
                return '\n'.join('name: %(name)s' % d for d in self.list(req))

            def list_json(self, req):
                req.response.content_type = "application/javascript"
                return json.dumps(self.list(req))

        class Multiple1(Resource):
            collection = "multiple"

            def retrieve_text(self, req, member):
                return "multiple1: %s" % member

        class Multiple2(Resource):

            def retrieve_text(self, req, member):
                return "multiple2: %s" % member

        class NoMime(Resource):
            collection = "nomime"
            best_match = False

            def list(self, req):
                pass

            retrieve = False

        class Extensions(Resource):
            collection = "extensions"
            extensions = {".json": "application/javascript"}
            mimetypes = {
                "application/javascript": "json",
                "text/plain": "txt",
            }

            def list_json(self, req):
                req.response.content_type = "application/javascript"
                return json.dumps([{"name": str(x)} for x in range(5)])

            def retrieve_json(self, req, name):
                req.response.content_type = "application/javascript"
                return json.dumps({"name": name})

            def retrieve_txt(self, req, name):
                req.response.content_type = "text/plain"
                return "name: %s" % name

        service = Service(
            Empty(),
            Content(),
            Minimal(),
            Multiple1(mimetypes = {"*/*": "text"}),
            Multiple2("multiple"),
            NoMime(),
            Extensions(),
        )

        self.service = service
        self.application = service
        self.empty = Empty()

class TestService(ServiceTest):

    def test_url_collection(self):
        self.assertEqual(self.service.url("content"), "content")

    def test_url_member(self):
        self.assertEqual(self.service.url("content", "foo"), "content/foo")

    def test_url_params(self):
        self.assertEqual(self.service.url("content", "foo", spam="eggs"), "content/foo?spam=eggs")

    def test_url_no_resource(self):
        self.assertEqual(self.service.url("blargle"), None)

class TestResource(BaseTest):

    def setUp(self):
        self.resource = Resource("foo")
    
    def test_resource_name(self):
        self.assertEqual(str(self.resource), "Resource")

    def test_url_collection(self):
        self.assertEqual(self.resource.url(), "foo")

    def test_url_member(self):
        self.assertEqual(self.resource.url("bar"), "foo/bar")

    def test_url_params(self):
        self.assertEqual(self.resource.url(spam="eggs", swallow="laden"),
            'foo?swallow=laden&spam=eggs')

class TestStack(ServiceTest):

    def test_no_resource(self):
        response = self.app("/doesnotexist")
        self.assertEqual(response.status_int, 404)

    def test_no_method(self):
        response = self.app("/empty")
        self.assertEqual(response.status_int, 404)

    def test_multiple_matches(self):
        response = self.app("/multiple/foo")
        self.assertEqual(response.body, "multiple1: foo")

    def test_method_not_implemented(self):
        response = self.app("/minimal/foo")
        self.assertEqual(response.status_int, 404)

    def test_crazy_http_method(self):
        response = self.app("/minimal", method="NOTAREALMETHOD")
        self.assertEqual(response.status_int, 404)

    def test_no_accept_header(self):
        response = self.app("/content")
        self.assertEqual(response.content_type, "text/plain")
        self.assertEqual(response.body, "name: a\nname: b")

    def test_accept_header(self):
        response = self.app("/content", accept="application/javascript")
        self.assertEqual(response.content_type, "application/javascript")
        self.assertEqual(response.body, """[{"name": "a"}, {"name": "b"}]""")

    def test_no_mime_at_all(self):
        response = self.app("/nomime")
        self.assertEqual(response.status_int, 200)

    def test_no_mime_match(self):
        response = self.app("/nomime", accept="something/youdontsupport")
        self.assertEqual(response.status_int, 404)

    def test_method_isnt_callable(self):
        response = self.app("/nomime/foo")
        self.assertEqual(response.status_int, 404)

    def test_map_extensions(self):
        response = self.app("/extensions/foo.json")
        self.assertEqual(response.content_type, "application/javascript")
        self.assertEqual(response.body, '{"name": "foo"}')

    def test_extension_overrides_accept(self):
        response = self.app("/extensions/foo.json", accept="text/html")
        self.assertEqual(response.content_type, "application/javascript")
        self.assertEqual(response.body, '{"name": "foo"}')

    def test_extesion_collection(self):
        response = self.app("/extensions.json")
        self.assertEqual(response.content_type, "application/javascript")
        self.assertEqual(response.body,
            '[{"name": "0"}, {"name": "1"}, {"name": "2"}, {"name": "3"}, {"name": "4"}]')
