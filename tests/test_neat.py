from tests import AppTest

from neat.neat import Resource, Service

class TestResource(AppTest):

    def setUp(self):
        class Empty(Resource):
            collection = "empty"

        class Minimal(Resource):
            collection = "minimal"

            def list(self):
                pass

        service = Service(
            Empty(),
            Minimal(),
        )

        self.application = service

    def test_no_resource(self):
        response = self.app("/doesnotexist")
        self.assertEqual(response.status_int, 404)

    def test_no_method(self):
        response = self.app("/empty")
        self.assertEqual(response.status_int, 404)
