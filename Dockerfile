# Imagen única para Railway: FastAPI sirve la API en /api y la app web compilada en /.

# Etapa 1: compilar la app web (React + Vite).
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Etapa 2: servidor Python.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENTORNO=produccion
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
# config.CARPETA_FRONTEND apunta por defecto a ../frontend/dist.
COPY --from=web /web/dist /app/frontend/dist

# Migraciones antes de arrancar (una sola instancia, así que no compiten entre sí).
# --proxy-headers: detrás del proxy de Railway, sin esto todas las peticiones llegan con la misma IP
# y el límite de intentos por IP bloquearía a todos los usuarios a la vez.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
