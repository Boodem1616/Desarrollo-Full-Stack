import json
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

from server import Catalog, CatalogHandler, CATALOG_PATH, ROOT, normalize_text


class CatalogApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog(CATALOG_PATH)
        handler = partial(CatalogHandler, catalog=cls.catalog, directory=ROOT)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get_json(self, path):
        try:
            response = urlopen(f"{self.base_url}{path}", timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.loads(response.read())

    def test_first_page_uses_full_catalog_and_expected_page_size(self):
        status, result = self.get_json("/api/products")
        self.assertEqual(status, 200)
        self.assertEqual(result["total"], 4032)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["pageSize"], 8)
        self.assertEqual(len(result["items"]), 8)

    def test_search_is_case_insensitive_and_runs_on_server(self):
        status, result = self.get_json("/api/products?q=CHOCOLATE%20LIQUIDO")
        self.assertEqual(status, 200)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all("chocolate liquido" in normalize_text(item["name"]) for item in result["items"]))
        self.assertLessEqual(len(result["items"]), 8)

    def test_category_and_format_filters_are_available_and_composable(self):
        status, options = self.get_json("/api/products/filters")
        self.assertEqual(status, 200)
        self.assertEqual(len(options["categories"]), 26)
        self.assertEqual(len(options["formats"]), 252)
        category = "Huevos, leche y mantequilla"
        product_format = "6 mini bricks x 200 ml"
        status, result = self.get_json(
            "/api/products?category=Huevos%2C%20leche%20y%20mantequilla&format=6%20mini%20bricks%20x%20200%20ml"
        )
        self.assertEqual(status, 200)
        self.assertGreater(result["total"], 0)
        self.assertTrue(all(item["category"].startswith(category) for item in result["items"]))
        self.assertTrue(all(item["format"] == product_format for item in result["items"]))

    def test_product_detail_returns_all_source_fields(self):
        status, product = self.get_json("/api/products/10043")
        self.assertEqual(status, 200)
        self.assertEqual(product["id"], "10043")
        self.assertEqual(
            set(product),
            {
                "id",
                "name",
                "description",
                "format",
                "category",
                "price",
                "priceUnit",
                "originalPrice",
                "currency",
                "imageUrl",
                "productUrl",
                "extractedAt",
            },
        )
        self.assertIsInstance(product["price"], int)

    def test_missing_product_and_invalid_pagination_return_errors(self):
        status, error = self.get_json("/api/products/not-a-product")
        self.assertEqual(status, 404)
        self.assertIn("error", error)
        for query in ("page=0", "page=invalid", "pageSize=101"):
            with self.subTest(query=query):
                status, error = self.get_json(f"/api/products?{query}")
                self.assertEqual(status, 400)
                self.assertIn("error", error)

    def test_empty_search_and_out_of_range_page_have_consistent_metadata(self):
        status, empty = self.get_json("/api/products?q=producto%20inexistente")
        self.assertEqual(status, 200)
        self.assertEqual(empty["items"], [])
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["totalPages"], 0)
        status, last_page = self.get_json("/api/products?page=99999&pageSize=100")
        self.assertEqual(status, 200)
        self.assertEqual(last_page["page"], last_page["totalPages"])

    def test_frontend_is_served_by_the_same_server(self):
        with urlopen(f"{self.base_url}/", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b'id="product-grid"', response.read())
        with urlopen(f"{self.base_url}/assets/favicon.svg", timeout=5) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"<svg", response.read())

    def test_catalog_file_and_unknown_api_routes_are_not_exposed(self):
        with self.assertRaises(HTTPError) as file_error:
            urlopen(f"{self.base_url}/data/catalog.csv", timeout=5)
        self.assertEqual(file_error.exception.code, 404)
        file_error.exception.close()
        status, error = self.get_json("/api/unknown")
        self.assertEqual(status, 404)
        self.assertIn("error", error)


if __name__ == "__main__":
    unittest.main()
