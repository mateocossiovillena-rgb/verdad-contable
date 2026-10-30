# Verdad Contable

Control de obra para constructores en Bolivia: avance físico frente a gasto real (valor ganado).
Backend FastAPI + PostgreSQL, frontend React (PWA). Detalle del producto en `CLAUDE.md` y `docs/plan-mvp.md`.

## En tu PC

Requisitos: Python 3.12 y Node 22.

```bash
# Backend (SQLite local en backend/verdad_contable.db)
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m app.datos_demo      # opcional: obra de ejemplo
.venv\Scripts\pytest -q

# Frontend
cd frontend
npm ci
```

Después, `iniciar.bat` levanta los dos servidores y abre http://localhost:5173.

## Publicación (Railway)

Cada push a `main` corre las pruebas en GitHub Actions (`.github/workflows/pruebas.yml`) y Railway publica
si pasan. La imagen sale del `Dockerfile`: compila el frontend, instala el backend, corre
`alembic upgrade head` y arranca uvicorn. Railway revisa `/api/salud` antes de dar por buena la versión.

Variables en el servicio de Railway:

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (referencia al servicio PostgreSQL) |
| `CLAVE_SECRETA` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` — nunca la misma que en local |
| `ENTORNO` | `produccion` (ya viene en la imagen) |
| `CARPETA_FOTOS` | `/data/fotos` |
| `CARPETA_PLANOS` | `/data/planos` |

Fotos y planos van en un volumen de Railway montado en `/data`: sobrevive a cada publicación. Respaldo diario
de PostgreSQL y restauración: `docs/piloto.md` §5. Pendiente: pasar las fotos a Cloudflare R2.
