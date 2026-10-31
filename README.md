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

## Publicación (Render)

Todo está descrito en `render.yaml` (Blueprint): servicio web Docker, PostgreSQL 17 y un disco de 1 GB en
`/data` para fotos y planos. La imagen sale del `Dockerfile`: compila el frontend, instala el backend, corre
`alembic upgrade head` y arranca uvicorn. Render revisa `/api/salud` antes de dar por buena la versión, y
publica cada push a `main` solo si pasaron las pruebas de GitHub Actions (`.github/workflows/pruebas.yml`).

Variables (ya definidas en el Blueprint):

| Variable | Valor |
| --- | --- |
| `DATABASE_URL` | la base `verdad-contable-db` |
| `CLAVE_SECRETA` | la genera Render (aleatoria); nunca la misma que en local |
| `ENTORNO` | `produccion` |
| `CARPETA_FOTOS` / `CARPETA_PLANOS` | `/data/fotos` / `/data/planos` |

Respaldo diario de PostgreSQL y restauración: `docs/piloto.md` §5. Pendiente: pasar las fotos a Cloudflare R2.
