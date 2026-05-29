# Catálogo Consolidado · App

Full-stack app: **FastAPI + MySQL + Alembic + Angular 18 + Tailwind**.

## Estructura

```
catalogo-app/
├── backend/                # FastAPI + SQLAlchemy + Alembic
│   ├── app/
│   ├── alembic/
│   ├── scripts/import_excel.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # Angular 18 (standalone) + Tailwind
│   ├── src/app/
│   │   ├── core/           # auth service, guard, interceptor, models
│   │   ├── layout/shell/   # sidebar layout Fuse-like
│   │   └── pages/          # login, catalog, suppliers
│   ├── tailwind.config.js
│   ├── nginx.conf
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Levantar local

```bash
cp .env.example .env
# editar credenciales/paths si hace falta
docker compose up -d --build
```

Frontend en http://localhost:8003

## Importar datos desde el Excel/images existentes

Una vez que el backend esté arriba y las migraciones aplicadas:

```bash
docker compose exec backend python -m scripts.import_excel \
    /data/Catalogo_Consolidado.xlsx \
    /data/images/manifest.json
```

(El path `/data` mapea al `DATA_DIR` del `.env` — por default `/home/javier/juan`.)

## Endpoints clave

- `POST /api/auth/login` — body `{username, password}` → `{access_token, user}`
- `GET  /api/auth/me`
- `GET  /api/products?q=...&supplier_id=&category_id=&currency=&max_price=&sort=&page=`
- `GET  /api/products/facets`
- `GET  /api/products/{id}`
- `GET  /api/suppliers`
- `GET  /api/categories?supplier_id=`

Todos los endpoints (menos `/login` y `/health`) requieren `Authorization: Bearer <token>`.

## Credenciales iniciales

Al primer arranque, el backend siembra `INITIAL_ADMIN_USER` / `INITIAL_ADMIN_PASSWORD` del `.env` (por default `juan` / `juan2026`).
