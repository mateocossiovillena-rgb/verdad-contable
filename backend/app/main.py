"""Aplicación FastAPI: API en /api y la app web compilada en /."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.rutas import cronograma, estimaciones, obras, registros, sesion

app = FastAPI(title="Verdad Contable", version="0.1.0")
app.include_router(sesion.rutas)
app.include_router(obras.rutas)
app.include_router(registros.rutas)
app.include_router(cronograma.rutas)
app.include_router(estimaciones.rutas)


@app.get("/api/salud")
def salud():
    return {"estado": "ok"}


if (config.CARPETA_FRONTEND / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=config.CARPETA_FRONTEND / "assets"), name="assets")

    @app.get("/{ruta:path}", include_in_schema=False)
    def app_web(ruta: str):
        if ruta.startswith("api/"):
            raise HTTPException(404, "No encontrado")
        archivo = (config.CARPETA_FRONTEND / ruta).resolve()
        if ruta and archivo.is_file() and config.CARPETA_FRONTEND.resolve() in archivo.parents:
            return FileResponse(archivo)
        # Cualquier otra ruta la resuelve la app de React.
        return FileResponse(config.CARPETA_FRONTEND / "index.html", headers={"Cache-Control": "no-cache"})
