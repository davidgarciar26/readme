# Movimientos de agencias automotrices en México

Registro de qué grupos automotrices abren y cierran agencias (puntos de venta) cada mes, armado a partir de noticias.

## Archivos

| Archivo | Qué contiene |
|---|---|
| `data/movimientos.csv` | Movimientos confirmados (ene–nov 2026): fecha, grupo, tipo, marca, ciudad, estado, puntos, fuente y nota. |
| `data/noticias_detectadas.csv` | Lo genera el rastreador: titulares candidatos sin revisar. |
| `scripts/rastrear_noticias.py` | Busca en Google News (México) y clasifica titulares como apertura, cierre o cambio de distribuidor. |
| `.github/workflows/rastreo-mensual.yml` | Corre el rastreador el día 1 de cada mes y guarda lo que encontró. |

`tipo` puede ser `apertura`, `cierre`, `cambio_distribuidor`, `anuncio_expansion` o `contexto`. Las filas con `estado = Nacional` son reportes agregados (por ejemplo, un recorte de red de varias marcas) y no se suman a los conteos por mes.

## Flujo mensual

1. El workflow (o `python3 scripts/rastrear_noticias.py --dias 35`) agrega candidatos a `data/noticias_detectadas.csv`.
2. Revisa cada candidato, abre la nota y, si se confirma, cópialo a `data/movimientos.csv`.

## Limitaciones

- Las fechas de 2026 salen de los resultados de búsqueda y de la URL de cada nota; no se abrió cada página.
- La prensa local está poco indexada, así que los conteos son un piso, no el total del mercado.
- Si la nota no nombra al operador, el grupo aparece como "No identificado".
