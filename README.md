# juan-representaciones

Catálogo consolidado de productos para Juan Representaciones. El repo contiene **el código** del proyecto; los datos (listas de precios en PDF, imágenes, modelos, backups) se manejan por fuera del control de versiones (ver `.gitignore`).

## Componentes

### `catalogo-app/` — Aplicación web
Full-stack: **FastAPI + MySQL + Alembic + Angular 18 + Tailwind**, dockerizada.
Login JWT, catálogo navegable, carrito, generación de órdenes con condiciones de pago,
envío de la orden por email (PDF adjunto) y panel de administración (productos, usuarios, condiciones).
Ver [`catalogo-app/README.md`](catalogo-app/README.md) para levantarla.

### Pipeline de catálogo (scripts en la raíz)
Toma las listas de precios en PDF y genera el catálogo consolidado:

| Script | Función |
|---|---|
| `build_excel.py` | Construye `Catalogo_Consolidado.xlsx` desde las listas |
| `build_html.py` | Genera el catálogo HTML estático |
| `build_manual.py` | Genera el manual de uso |
| `extract_images.py` / `extract_crops_cv.py` / `extract_crops_sam.py` | Extracción de imágenes de productos (OpenCV / SAM) |
| `clip_match.py` | Asocia imágenes a productos con CLIP |
| `ocr_pending.py` | OCR de PDFs sin texto |
| `transparentize_logos.py` | Limpieza de logos |
| `e2e_test.py` | Test end-to-end del pipeline |

## Deploy

La app corre en un servidor con Docker (`/srv/catalogo-app`), expuesta en el puerto `8003`,
más un Caddy estático para el catálogo HTML en el `8002`. El deploy es manual
(`docker compose up -d --build`).

> Datos excluidos del repo: `Listas actualizadas*/`, `images/`, `media/`, `screenshots/`,
> `sam_models/`, `backups/`, `*.zip`, `*.pdf`, `*.xlsx`, `*.docx` y secretos (`.env`, `*.pem`).
