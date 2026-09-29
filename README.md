# Vitrina de productos

Aplicación web para explorar los 4.032 productos de `data/catalog.csv`. El backend entrega únicamente la página solicitada y aplica búsqueda y filtros; el navegador nunca carga ni filtra el catálogo completo.

## Ejecutar

Requiere Python 3.9 o posterior; no necesita dependencias ni compilación.

```bash
python3 server.py
```

Abre <http://127.0.0.1:8000>. Para detener el servidor, usa `Ctrl+C`. Las imágenes del catálogo se cargan desde las URL de origen y requieren conexión a internet; la búsqueda, los precios y los demás datos funcionan localmente.

## Comportamiento especificado

- La grilla presenta ocho cards por página con imagen, nombre, categoría principal, formato y precio en la moneda indicada por los datos.
- La búsqueda por nombre ignora mayúsculas, minúsculas y tildes. Se combina con filtros por categoría principal y formato.
- Los filtros se obtienen del catálogo y muestran todas las opciones disponibles, no una lista fija de ejemplos.
- La paginación permite avanzar, retroceder y elegir entre las páginas cercanas a la actual. Al cambiar búsqueda o filtros se vuelve a la primera página.
- Al seleccionar una card, se consulta el detalle por ID y se presentan los campos originales del producto, precio, moneda y enlace de origen.
- La interfaz comunica carga, resultados vacíos y errores recuperables. Los valores mostrados provienen del CSV; la aplicación no inventa ni convierte datos.
- La API usa tamaño de página 8 por defecto y admite hasta 100; páginas fuera de rango se ajustan a la última página disponible.

## Arquitectura y decisiones

- `server.py` carga y valida el CSV al iniciar, expone la API y sirve los archivos estáticos. Se eligió la biblioteca estándar de Python para mantener el ejercicio sencillo y sin dependencias.
- `Catalog` concentra lectura, opciones de filtros, búsqueda y paginación. El catálogo se conserva en memoria para evitar releer el CSV en cada solicitud.
- `app.js` consume la API con `fetch`, dibuja los resultados y construye el contenido mediante nodos DOM y `textContent`.
- `index.html` contiene la estructura; `styles.css` conserva la identidad visual del mockup.

## API

- `GET /api/products?q=<texto>&category=<categoría>&format=<formato>&page=<n>&pageSize=<n>` devuelve `{ items, page, pageSize, total, totalPages }`.
- `GET /api/products/<id>` devuelve todos los campos del producto o `404` si no existe.
- `GET /api/products/filters` devuelve las opciones de `categories` y `formats`.

Los errores de parámetros inválidos responden `400` con un objeto `{ "error": "..." }`.

## Verificación repetible

Ejecuta las pruebas de API y del catálogo con:

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas cubren el volumen del catálogo, búsqueda, filtros, paginación, detalle, errores HTTP y servicio de la interfaz. Las instrucciones persistentes para agentes están en [AGENTS.md](./AGENTS.md).
