from tests import AppTest, log

from neat.neat import Resource, Service

class TestStack(AppTest):

    def setUp(self):
        class Empty(Resource):
            collection = "empty"

        class Minimal(Resource):
            collection = "minimal"

        class Multiple1(Resource):
            collection = "multiple"

            def retrieve_text(self, req, member):
                return "multiple1: %s" % member

        class Multiple2(Resource):

            def retrieve_text(self, req, member):
                return "multiple2: %s" % member

        service = Service(
            Empty(),
            Minimal(),
            Multiple1(mimetypes = {"*/*": "text"}),
            Multiple2("multiple"),
        )

        self.application = service
        self.empty = Empty()

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

class TestResource(AppTest):

    def test_resource_name(self):
        self.assertEqual(str(Resource()), "Resource")
