# Instrucciones para agentes

- Antes de editar, contrasta los cambios con la consigna en `Desafio-Full-Stack-Etapa-1.pdf` y la especificación del `README.md`.
- Conserva los datos originales de `data/catalog.csv`: no inventes, traduzcas ni recalcules atributos o precios.
- Mantén búsqueda, filtros y paginación en `/api/products`; el frontend no debe descargar ni procesar el catálogo completo.
- Valida rutas, parámetros y errores con respuestas HTTP explícitas; no ocultes fallos con datos de ejemplo.
- Para cambios de backend, ejecuta `python3 -m unittest discover -s tests -v`. Comprueba también que la interfaz consuma los endpoints reales.
- Prefiere la biblioteca estándar y evita añadir dependencias si la aplicación puede seguir resolviendo el problema sin ellas.
