"""Kit TCM (AACE): plantilla Excel, importar obra, estimado con APU, clase, base del estimado y línea base."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import costos
from app.db import obtener_sesion
from app.esquemas import (
    ActividadEstimadaSalida,
    ApuSalida,
    BaseEstimadoEntrada,
    BaseEstimadoSalida,
    ClaseSalida,
    ClasificacionEntrada,
    ClasificacionSalida,
    EntregableSalida,
    EstimadoObra,
    FaseEstimadaSalida,
    InsumoSalida,
    LineaBaseDetalle,
    LineaBaseEntrada,
    LineaBaseResumen,
    ObraImportada,
    ObraSalida,
    ParametrosApuEntrada,
    ParametrosApuSalida,
    ProblemaSalida,
    ResumenImportacion,
    SemanaSalida,
    VistaPrevia,
)
from app.modelos import BaseEstimado, LineaBase, Obra, ParametrosApu, Usuario
from app.seguridad import obra_propia, solo_dueno
from app.tcm import clasificacion as cl
from app.tcm import exportar
from app.tcm import plantilla as pl
from app.tcm import servicio as ts

rutas = APIRouter(prefix="/api", tags=["kit TCM"])

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TAMANO_MAX_EXCEL = 5 * 1024 * 1024


def _excel(contenido: bytes, nombre: str) -> Response:
    return Response(contenido, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{nombre}"'})


def _apu(a: costos.Apu) -> ApuSalida:
    return ApuSalida(
        materiales=a.materiales,
        mano_obra=a.mano_obra,
        cargas_sociales=a.cargas_sociales,
        iva_mano_obra=a.iva_mano_obra,
        equipo=a.equipo,
        herramientas=a.herramientas,
        costo_directo=a.costo_directo,
        gastos_generales=a.gastos_generales,
        utilidad=a.utilidad,
        impuestos=a.impuestos,
        total=a.total,
    )


def _clase(c: cl.Clase) -> ClaseSalida:
    return ClaseSalida(
        clase=c.clase,
        definicion_norma=c.definicion_norma,
        uso=c.uso,
        metodologia=c.metodologia,
        exactitud_baja=list(c.exactitud_baja),
        exactitud_alta=list(c.exactitud_alta),
    )


def _nombres_usuarios(sesion: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(sesion.execute(select(Usuario.id, Usuario.nombre).where(Usuario.id.in_(ids))).all())


def _resumen(base: LineaBase, nombres: dict[int, str]) -> LineaBaseResumen:
    return LineaBaseResumen.model_validate(base).model_copy(
        update={"aprobada_por_nombre": nombres.get(base.aprobada_por, "")}
    )


def _detalle(sesion: Session, base: LineaBase) -> LineaBaseDetalle:
    resumen = _resumen(base, _nombres_usuarios(sesion, {base.aprobada_por}))
    return LineaBaseDetalle(
        **resumen.model_dump(),
        partidas=base.partidas,
        semanas=[
            SemanaSalida(
                numero=s.numero,
                inicio=s.inicio,
                fin=s.fin,
                pv=s.pv,
                pv_acumulado=s.pv_acumulado,
                porcentaje_acumulado=None if s.porcentaje_acumulado is None else float(s.porcentaje_acumulado),
            )
            for s in ts.pv_semanal(base)
        ],
    )


def _estimado_obra(sesion: Session, obra: Obra) -> EstimadoObra:
    est = ts.estimado(sesion, obra)
    resultado = ts.clasificar(sesion, obra, est.total)
    tabla = cl.tabla()
    lista = ts.checklist(sesion, obra.id)
    base = ts.base_del_estimado(sesion, obra.id)
    lineas = ts.lineas_base(sesion, obra.id)
    nombres = _nombres_usuarios(sesion, {lb.aprobada_por for lb in lineas})
    vigente = next((lb for lb in lineas if lb.vigente), None)
    plan_distinto = False
    if vigente is not None:
        actuales = {
            p.id: (p.presupuesto, p.fecha_inicio, p.fecha_fin) for p in servicios.partidas_de_obra(sesion, obra.id)
        }
        congeladas = {
            lp.partida_id: (lp.presupuesto, lp.fecha_inicio, lp.fecha_fin) for lp in vigente.partidas if lp.partida_id
        }
        # Los gastos generales sin fechas propias se congelan con las de la obra: comparar solo el monto.
        plan_distinto = set(actuales) != set(congeladas) or any(
            actuales[i][0] != congeladas[i][0] or (actuales[i][1] and actuales[i][1:] != congeladas[i][1:])
            for i in actuales
        )
    p = est.parametros
    return EstimadoObra(
        obra=ObraSalida.model_validate(obra),
        parametros=ParametrosApuSalida(**{k: float(getattr(p, k)) for k in pl.PARAMETROS}),
        fases=[
            FaseEstimadaSalida(
                id=f.fase.id,
                nombre=f.fase.nombre,
                total=f.total,
                actividades=[
                    ActividadEstimadaSalida(
                        id=a.actividad.id,
                        codigo=a.actividad.codigo,
                        nombre=a.actividad.nombre,
                        unidad=a.actividad.unidad,
                        computo=None if a.actividad.computo is None else float(a.actividad.computo),
                        fecha_inicio=a.actividad.fecha_inicio,
                        fecha_fin=a.actividad.fecha_fin,
                        apu=_apu(a.apu),
                        precio_unitario=a.precio_unitario,
                        insumos=[
                            InsumoSalida(
                                tipo=r.tipo,
                                descripcion=r.descripcion,
                                unidad=r.unidad,
                                rendimiento=None if r.rendimiento is None else float(r.rendimiento),
                                cantidad=float(r.cantidad),
                                precio_unitario=r.precio_unitario,
                                parcial=costos.costo_recurso(servicios.datos_recurso(r), a.actividad.duracion_dias),
                            )
                            for r in a.recursos
                        ],
                    )
                    for a in f.actividades
                ],
            )
            for f in est.fases
        ],
        totales=ApuSalida(
            **{campo: est.suma(campo) for campo in ApuSalida.model_fields},
        ),
        clasificacion=ClasificacionSalida(
            entregables=[
                EntregableSalida(clave=e.clave, nombre=e.nombre, peso=float(e.peso), estado=lista.get(e.clave, "no"))
                for e in tabla.entregables
            ],
            porcentaje_definicion=float(resultado.porcentaje_definicion),
            clase=_clase(resultado.clase),
            minimo=resultado.minimo,
            maximo=resultado.maximo,
            clases=[_clase(c) for c in sorted(tabla.clases, key=lambda c: -c.clase)],
        ),
        base=BaseEstimadoSalida.model_validate(base).model_copy(
            update={"contingencia_monto": (est.total * base.contingencia_porcentaje / 100).quantize(Decimal("0.01"))}
        ),
        lineas_base=[_resumen(lb, nombres) for lb in lineas],
        vigente=_detalle(sesion, vigente) if vigente else None,
        plan_distinto_de_base=plan_distinto,
    )


# --- Plantilla e importación ---


@rutas.get("/kit/plantilla.xlsx")
def descargar_plantilla(_dueno: Usuario = Depends(solo_dueno)):
    return _excel(pl.escribir_plantilla(), "plantilla-kit-tcm.xlsx")


async def _leer_cuerpo(request: Request) -> bytes:
    datos = bytearray()
    async for parte in request.stream():
        datos += parte
        if len(datos) > TAMANO_MAX_EXCEL:
            raise HTTPException(413, "El archivo pesa más de 5 MB.")
    if not datos:
        raise HTTPException(422, "El archivo está vacío")
    return bytes(datos)


def _problemas(lista: list[pl.Problema]) -> list[ProblemaSalida]:
    return [ProblemaSalida(hoja=p.hoja, fila=p.fila, columna=p.columna, mensaje=p.mensaje) for p in lista]


def _total_leido(d: pl.ObraLeida) -> Decimal:
    parametros = costos.ParametrosApu(**d.parametros)
    computos = {a.codigo: a.computo for a in d.actividades}
    por_actividad: dict[str, list[costos.DatosRecurso]] = {}
    for r in d.insumos:
        if r.codigo_actividad in computos:
            cantidad = (r.rendimiento * computos[r.codigo_actividad]).quantize(Decimal("0.001"))
            por_actividad.setdefault(r.codigo_actividad, []).append(costos.DatosRecurso(r.tipo, cantidad, r.precio))
    return sum(
        (costos.calcular_apu(costos.costo_actividad(rs, 1), parametros).total for rs in por_actividad.values()),
        Decimal("0"),
    )


@rutas.post("/kit/importar/previa", response_model=VistaPrevia)
async def vista_previa(request: Request, _dueno: Usuario = Depends(solo_dueno)):
    """Lee y valida la plantilla sin grabar nada. El cuerpo es el .xlsx tal cual (application/octet-stream)."""
    lectura = await run_in_threadpool(pl.leer_plantilla, await _leer_cuerpo(request))
    d = lectura.obra
    resumen = None
    if d.actividades:
        resultado = cl.clasificar(d.clasificacion, cl.tabla())
        resumen = ResumenImportacion(
            nombre=d.nombre,
            fecha_inicio=d.fecha_inicio,
            moneda=d.moneda,
            fases=len({a.fase for a in d.actividades}),
            actividades=len(d.actividades),
            insumos=len(d.insumos),
            total_estimado=_total_leido(d),
            porcentaje_definicion=float(resultado.porcentaje_definicion),
            clase=resultado.clase.clase,
        )
    return VistaPrevia(
        valida=lectura.valida,
        errores=_problemas(lectura.errores),
        advertencias=_problemas(lectura.advertencias),
        resumen=resumen,
    )


@rutas.post("/kit/importar", response_model=ObraImportada, status_code=status.HTTP_201_CREATED)
async def importar(request: Request, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    """Vuelve a validar el mismo archivo y, solo si no tiene errores, crea la obra completa."""
    lectura = await run_in_threadpool(pl.leer_plantilla, await _leer_cuerpo(request))
    if not lectura.valida:
        primero = lectura.errores[0]
        donde = f"{primero.hoja}, fila {primero.fila}" if primero.fila else primero.hoja
        raise HTTPException(
            422, f"El archivo tiene {len(lectura.errores)} error(es). Primero: {donde}: {primero.mensaje}"
        )
    obra = ts.crear_obra_desde_plantilla(sesion, dueno, lectura.obra)
    sesion.commit()
    return ObraImportada(obra=ObraSalida.model_validate(obra), advertencias=_problemas(lectura.advertencias))


# --- Estimado de una obra ---


@rutas.get("/obras/{obra_id}/estimado", response_model=EstimadoObra)
def ver_estimado(obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    return _estimado_obra(sesion, obra_propia(sesion, dueno, obra_id))


@rutas.put("/obras/{obra_id}/estimado/clasificacion", response_model=EstimadoObra)
def guardar_clasificacion(
    obra_id: int,
    datos: ClasificacionEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_propia(sesion, dueno, obra_id)
    ts.guardar_checklist(sesion, obra.id, datos.entregables)
    sesion.commit()
    return _estimado_obra(sesion, obra)


@rutas.put("/obras/{obra_id}/estimado/parametros", response_model=EstimadoObra)
def guardar_parametros(
    obra_id: int,
    datos: ParametrosApuEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    """Cambia los % del APU y recalcula el presupuesto de las partidas (no la línea base aprobada)."""
    obra = obra_propia(sesion, dueno, obra_id)
    fila = sesion.get(ParametrosApu, obra.id)
    if fila is None:
        fila = ParametrosApu(obra_id=obra.id)
        sesion.add(fila)
    for campo, valor in datos.model_dump().items():
        setattr(fila, campo, valor)
    servicios.recalcular_cronograma(sesion, obra)
    sesion.commit()
    return _estimado_obra(sesion, obra)


@rutas.put("/obras/{obra_id}/estimado/base", response_model=EstimadoObra)
def guardar_base(
    obra_id: int,
    datos: BaseEstimadoEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_propia(sesion, dueno, obra_id)
    fila = sesion.get(BaseEstimado, obra.id)
    if fila is None:
        fila = BaseEstimado(obra_id=obra.id)
        sesion.add(fila)
    for campo, valor in datos.model_dump().items():
        setattr(fila, campo, valor.strip() if isinstance(valor, str) else valor)
    sesion.commit()
    return _estimado_obra(sesion, obra)


@rutas.post("/obras/{obra_id}/lineas-base", response_model=EstimadoObra, status_code=status.HTTP_201_CREATED)
def aprobar_linea_base(
    obra_id: int,
    datos: LineaBaseEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_propia(sesion, dueno, obra_id)
    ts.aprobar_linea_base(sesion, obra, dueno, datos.motivo)
    sesion.commit()
    return _estimado_obra(sesion, obra)


@rutas.get("/lineas-base/{linea_base_id}", response_model=LineaBaseDetalle)
def ver_linea_base(linea_base_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    base = sesion.get(LineaBase, linea_base_id)
    if base is None:
        raise HTTPException(404, "Línea base no encontrada")
    obra_propia(sesion, dueno, base.obra_id)
    return _detalle(sesion, base)


@rutas.get("/obras/{obra_id}/estimado.xlsx")
def exportar_estimado(obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    obra = obra_propia(sesion, dueno, obra_id)
    contenido = exportar.exportar_estimado(sesion, obra, servicios.linea_base_vigente(sesion, obra.id))
    return _excel(contenido, f"estimado-obra-{obra.id}-{date.today().isoformat()}.xlsx")
