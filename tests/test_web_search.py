import unittest
from fastapi.testclient import TestClient
from main import app

class TestWebSearchAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_web_search_empty_query(self):
        response = self.client.get("/api/web-search?q=")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "")
        self.assertEqual(data["results"], [])

    def test_web_search_with_query(self):
        response = self.client.get("/api/web-search?q=UX+Research+interview+questions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("query", data)
        self.assertIn("results", data)
        self.assertGreater(len(data["results"]), 0)
        first = data["results"][0]
        self.assertIn("title", first)
        self.assertIn("snippet", first)
        print("[Web Search Test Log] Search results received:", len(data["results"]), "First title:", first["title"])

if __name__ == "__main__":
    unittest.main()
