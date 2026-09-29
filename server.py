import argparse
import csv
import json
import math
import unicodedata
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "data" / "catalog.csv"
PAGE_SIZE_DEFAULT = 8
PAGE_SIZE_MAX = 100
PRODUCT_FIELDS = {
    "id": "id",
    "name": "name",
    "description": "description",
    "format": "format",
    "category": "category",
    "price": "price",
    "priceUnit": "priceUnit",
    "originalPrice": "originalPrice",
    "currency": "currency",
    "imageUrl": "imageUrl",
    "productUrl": "productUrl",
    "extractedAt": "extractedAt",
}


def normalize_text(value):
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(character for character in decomposed if unicodedata.category(character) != "Mn")


class Catalog:
    def __init__(self, path):
        with path.open(newline="", encoding="utf-8") as catalog_file:
            reader = csv.DictReader(catalog_file)
            missing = set(PRODUCT_FIELDS.values()) - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"Faltan columnas requeridas en el catálogo: {', '.join(sorted(missing))}")
            self.products = []
            for row in reader:
                product = {key: row[column] for key, column in PRODUCT_FIELDS.items()}
                product["price"] = int(product["price"])
                product["originalPrice"] = int(product["originalPrice"])
                self.products.append(product)
        self.by_id = {product["id"]: product for product in self.products}
        if len(self.by_id) != len(self.products):
            raise ValueError("El catálogo contiene identificadores de producto duplicados.")

    def filters(self):
        categories = {product["category"].split(" > ")[0] for product in self.products}
        formats = {product["format"] for product in self.products}
        return {
            "categories": sorted(categories, key=str.casefold),
            "formats": sorted(formats, key=str.casefold),
        }

    def search(self, query="", category="", product_format="", page=1, page_size=PAGE_SIZE_DEFAULT):
        normalized_query = normalize_text(query.strip())
        products = [
            product
            for product in self.products
            if normalized_query in normalize_text(product["name"])
            and (not category or product["category"].split(" > ")[0] == category)
            and (not product_format or product["format"] == product_format)
        ]
        total = len(products)
        total_pages = math.ceil(total / page_size) if total else 0
        current_page = min(page, total_pages) if total_pages else 1
        start = (current_page - 1) * page_size
        return {
            "items": products[start : start + page_size],
            "page": current_page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
        }


class CatalogHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, catalog, directory, **kwargs):
        self.catalog = catalog
        super().__init__(*args, directory=str(directory), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            self.log_message("Client disconnected before the response was complete")

    @staticmethod
    def positive_integer(params, name, default):
        value = params.get(name, [str(default)])[0]
        try:
            parsed = int(value)
        except ValueError as error:
            raise ValueError(f"'{name}' debe ser un número entero.") from error
        if parsed < 1:
            raise ValueError(f"'{name}' debe ser mayor que cero.")
        return parsed

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/products/filters":
            self.send_json(self.catalog.filters())
            return
        if parsed.path == "/api/products":
            params = parse_qs(parsed.query, keep_blank_values=True)
            try:
                page = self.positive_integer(params, "page", 1)
                page_size = self.positive_integer(params, "pageSize", PAGE_SIZE_DEFAULT)
                if page_size > PAGE_SIZE_MAX:
                    raise ValueError(f"'pageSize' no puede superar {PAGE_SIZE_MAX}.")
                result = self.catalog.search(
                    query=params.get("q", [""])[0],
                    category=params.get("category", [""])[0],
                    product_format=params.get("format", [""])[0],
                    page=page,
                    page_size=page_size,
                )
            except ValueError as error:
                self.send_json({"error": str(error)}, status=400)
                return
            self.send_json(result)
            return
        if parsed.path.startswith("/api/products/"):
            product_id = unquote(parsed.path.removeprefix("/api/products/"))
            product = self.catalog.by_id.get(product_id)
            if product is None:
                self.send_json({"error": "No se encontró el producto solicitado."}, status=404)
            else:
                self.send_json(product)
            return
        if parsed.path.startswith("/api/"):
            self.send_json({"error": "No se encontró la ruta solicitada."}, status=404)
            return
        if parsed.path in {"/", "/index.html", "/app.js", "/styles.css"}:
            super().do_GET()
            return
        if parsed.path.startswith("/assets/"):
            asset = (ROOT / unquote(parsed.path).lstrip("/")).resolve()
            if asset.is_relative_to(ROOT / "assets") and asset.is_file():
                super().do_GET()
                return
        self.send_error(404, "Recurso no encontrado.")


def main():
    parser = argparse.ArgumentParser(description="Servidor web y API del catálogo de productos.")
    parser.add_argument("--host", default="127.0.0.1", help="Interfaz de red (por defecto: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Puerto HTTP (por defecto: 8000).")
    args = parser.parse_args()
    catalog = Catalog(CATALOG_PATH)
    handler = partial(CatalogHandler, catalog=catalog, directory=ROOT)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Aplicación disponible en http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
