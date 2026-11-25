"""Kit TCM (AACE): plantilla Excel, importar obra, estimado con APU, clase, base del estimado y línea base."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import servicios
from app.calculos import costos
from app.calculos import valor_ganado as vg
from app.db import obtener_sesion
from app.esquemas import (
    ActividadEstimadaSalida,
    ApuSalida,
    BaseEstimadoEntrada,
    BaseEstimadoSalida,
    BitacoraCambios,
    CambioEntrada,
    CambioSalida,
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
    RegistroRiesgos,
    RegistrosImportados,
    ResolucionCambio,
    ResumenImportacion,
    RiesgoEntrada,
    RiesgoSalida,
    SemanaSalida,
    VistaPrevia,
    VistaPreviaRegistros,
)
from app.modelos import BaseEstimado, Cambio, LineaBase, Obra, ParametrosApu, Riesgo, Usuario
from app.seguridad import obra_propia, solo_dueno
from app.tcm import clasificacion as cl
from app.tcm import exportar
from app.tcm import plantilla as pl
from app.tcm import registros_excel as rx
from app.tcm import riesgos as rg
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


def _resumen(base: LineaBase, nombres: dict[int, str], sesion: Session | None = None) -> LineaBaseResumen:
    codigo = None
    if base.cambio_id and sesion is not None and (c := sesion.get(Cambio, base.cambio_id)) is not None:
        codigo = ts.codigo_cambio(c)
    return LineaBaseResumen.model_validate(base).model_copy(
        update={"aprobada_por_nombre": nombres.get(base.aprobada_por, ""), "cambio_codigo": codigo}
    )


def _detalle(sesion: Session, base: LineaBase) -> LineaBaseDetalle:
    resumen = _resumen(base, _nombres_usuarios(sesion, {base.aprobada_por}), sesion)
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
        lineas_base=[_resumen(lb, nombres, sesion) for lb in lineas],
        vigente=_detalle(sesion, vigente) if vigente else None,
        plan_distinto_de_base=plan_distinto,
        **_campos_contingencia(sesion, obra, est.total),
    )


def _campos_contingencia(sesion: Session, obra: Obra, total: Decimal) -> dict:
    r = rg.resumir([_datos_riesgo(x) for x in _riesgos(sesion, obra.id)], total)
    return {
        "riesgos_abiertos": r.abiertos,
        "riesgos_valor_esperado": r.valor_esperado,
        "riesgos_porcentaje": None if r.porcentaje_del_estimado is None else float(r.porcentaje_del_estimado),
    }


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
    contenido = exportar.exportar_estimado(
        sesion,
        obra,
        servicios.linea_base_vigente(sesion, obra.id),
        registros=(_riesgos(sesion, obra.id), _cambios(sesion, obra.id), _versiones_por_cambio(sesion, obra.id)),
    )
    return _excel(contenido, f"estimado-obra-{obra.id}-{date.today().isoformat()}.xlsx")


# --- Registro de riesgos (AACE 44R-08) ---


def _riesgos(sesion: Session, obra_id: int) -> list[Riesgo]:
    return list(sesion.scalars(select(Riesgo).where(Riesgo.obra_id == obra_id).order_by(Riesgo.numero)))


def _datos_riesgo(r: Riesgo) -> rg.DatosRiesgo:
    return rg.DatosRiesgo(r.probabilidad, r.impacto_costo, r.impacto_dias, r.estado)


def _registro(sesion: Session, obra: Obra) -> RegistroRiesgos:
    total = ts.estimado(sesion, obra).total
    riesgos = _riesgos(sesion, obra.id)
    resumen = rg.resumir([_datos_riesgo(r) for r in riesgos], total)
    salida = []
    for r in riesgos:
        d = _datos_riesgo(r)
        salida.append(
            RiesgoSalida.model_validate(r).model_copy(
                update={
                    "codigo": f"R-{r.numero:02d}",
                    "valor_esperado": rg.valor_esperado(d),
                    "dias_esperados": float(rg.dias_esperados(d)),
                    "nivel": rg.nivel(d, total),
                }
            )
        )
    return RegistroRiesgos(
        moneda=obra.moneda,
        total_estimado=total,
        riesgos=salida,
        abiertos=resumen.abiertos,
        valor_esperado=resumen.valor_esperado,
        dias_esperados=float(resumen.dias_esperados),
        porcentaje_del_estimado=None
        if resumen.porcentaje_del_estimado is None
        else float(resumen.porcentaje_del_estimado),
        contingencia_actual_porcentaje=float(ts.base_del_estimado(sesion, obra.id).contingencia_porcentaje),
    )


def _riesgo_propio(sesion: Session, dueno: Usuario, riesgo_id: int) -> tuple[Riesgo, Obra]:
    riesgo = sesion.get(Riesgo, riesgo_id)
    if riesgo is None:
        raise HTTPException(404, "Riesgo no encontrado")
    return riesgo, obra_propia(sesion, dueno, riesgo.obra_id)


@rutas.get("/obras/{obra_id}/riesgos", response_model=RegistroRiesgos)
def ver_riesgos(obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    return _registro(sesion, obra_propia(sesion, dueno, obra_id))


@rutas.post("/obras/{obra_id}/riesgos", response_model=RegistroRiesgos, status_code=status.HTTP_201_CREATED)
def crear_riesgo(
    obra_id: int, datos: RiesgoEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    numero = (sesion.scalar(select(func.max(Riesgo.numero)).where(Riesgo.obra_id == obra.id)) or 0) + 1
    sesion.add(Riesgo(obra_id=obra.id, numero=numero, **_limpio(datos)))
    sesion.commit()
    return _registro(sesion, obra)


def _limpio(datos: RiesgoEntrada) -> dict:
    return {k: v.strip() if isinstance(v, str) else v for k, v in datos.model_dump().items()}


@rutas.put("/riesgos/{riesgo_id}", response_model=RegistroRiesgos)
def editar_riesgo(
    riesgo_id: int,
    datos: RiesgoEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    riesgo, obra = _riesgo_propio(sesion, dueno, riesgo_id)
    for campo, valor in _limpio(datos).items():
        setattr(riesgo, campo, valor)
    sesion.commit()
    return _registro(sesion, obra)


@rutas.delete("/riesgos/{riesgo_id}", response_model=RegistroRiesgos)
def borrar_riesgo(riesgo_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    """Para errores de carga. Un riesgo que ya no aplica se marca "cerrado" para conservar el historial."""
    riesgo, obra = _riesgo_propio(sesion, dueno, riesgo_id)
    sesion.delete(riesgo)
    sesion.commit()
    return _registro(sesion, obra)


@rutas.post("/obras/{obra_id}/riesgos/contingencia", response_model=EstimadoObra)
def usar_como_contingencia(
    obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    """Pone en la Base del estimado la contingencia que sugiere el registro de riesgos (suma P × I de los abiertos)."""
    obra = obra_propia(sesion, dueno, obra_id)
    total = ts.estimado(sesion, obra).total
    resumen = rg.resumir([_datos_riesgo(r) for r in _riesgos(sesion, obra.id)], total)
    if resumen.porcentaje_del_estimado is None:
        raise HTTPException(422, "La obra no tiene estimado: no se puede expresar la contingencia como porcentaje.")
    if resumen.porcentaje_del_estimado > 100:
        raise HTTPException(422, "Los riesgos abiertos suman más que el estimado: revisa los impactos cargados.")
    fila = sesion.get(BaseEstimado, obra.id)
    if fila is None:
        fila = BaseEstimado(obra_id=obra.id)
        sesion.add(fila)
        for campo in ts.CAMPOS_BASE:
            setattr(fila, campo, "")
    fila.contingencia_porcentaje = resumen.porcentaje_del_estimado
    monto = vg.formatear_bs(resumen.valor_esperado).replace("Bs", obra.moneda)
    porcentaje = str(resumen.porcentaje_del_estimado).replace(".", ",")
    cuantos = "el riesgo abierto" if resumen.abiertos == 1 else f"los {resumen.abiertos} riesgos abiertos"
    fila.contingencia_nota = (
        f"Suma de los valores esperados (P × I) de {cuantos} del registro de riesgos "
        f"(AACE 44R-08): {monto}, el {porcentaje} % del estimado. Calculada el {servicios.hoy():%d/%m/%Y}."
    )
    sesion.commit()
    return _estimado_obra(sesion, obra)


# --- Bitácora de cambios ---


def _cambios(sesion: Session, obra_id: int) -> list[Cambio]:
    return list(sesion.scalars(select(Cambio).where(Cambio.obra_id == obra_id).order_by(Cambio.numero)))


def _bitacora(sesion: Session, obra: Obra) -> BitacoraCambios:
    cambios = _cambios(sesion, obra.id)
    versiones = dict(
        sesion.execute(
            select(LineaBase.cambio_id, LineaBase.version).where(
                LineaBase.obra_id == obra.id, LineaBase.cambio_id.is_not(None)
            )
        ).all()
    )
    aprobados = [c for c in cambios if c.estado == "aprobado"]
    pendientes = [c for c in cambios if c.estado == "pendiente"]
    vigente = servicios.linea_base_vigente(sesion, obra.id)
    return BitacoraCambios(
        moneda=obra.moneda,
        cambios=[
            CambioSalida.model_validate(c).model_copy(
                update={"codigo": ts.codigo_cambio(c), "linea_base_version": versiones.get(c.id)}
            )
            for c in cambios
        ],
        pendientes=len(pendientes),
        aprobados=len(aprobados),
        costo_aprobado=sum((c.impacto_costo for c in aprobados), Decimal("0")),
        dias_aprobados=sum(c.impacto_dias for c in aprobados),
        costo_pendiente=sum((c.impacto_costo for c in pendientes), Decimal("0")),
        linea_base_version=vigente.version if vigente else None,
    )


def _cambio_propio(sesion: Session, dueno: Usuario, cambio_id: int) -> tuple[Cambio, Obra]:
    cambio = sesion.get(Cambio, cambio_id)
    if cambio is None:
        raise HTTPException(404, "Cambio no encontrado")
    return cambio, obra_propia(sesion, dueno, cambio.obra_id)


def _datos_cambio(datos: CambioEntrada) -> dict:
    return {k: v.strip() if isinstance(v, str) else v for k, v in datos.model_dump().items()}


@rutas.get("/obras/{obra_id}/cambios", response_model=BitacoraCambios)
def ver_cambios(obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    return _bitacora(sesion, obra_propia(sesion, dueno, obra_id))


@rutas.post("/obras/{obra_id}/cambios", response_model=BitacoraCambios, status_code=status.HTTP_201_CREATED)
def crear_cambio(
    obra_id: int, datos: CambioEntrada, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    numero = (sesion.scalar(select(func.max(Cambio.numero)).where(Cambio.obra_id == obra.id)) or 0) + 1
    sesion.add(Cambio(obra_id=obra.id, numero=numero, estado="pendiente", **_datos_cambio(datos)))
    sesion.commit()
    return _bitacora(sesion, obra)


@rutas.put("/cambios/{cambio_id}", response_model=BitacoraCambios)
def editar_cambio(
    cambio_id: int,
    datos: CambioEntrada,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    cambio, obra = _cambio_propio(sesion, dueno, cambio_id)
    ts.exigir_pendiente(cambio)
    for campo, valor in _datos_cambio(datos).items():
        setattr(cambio, campo, valor)
    sesion.commit()
    return _bitacora(sesion, obra)


@rutas.delete("/cambios/{cambio_id}", response_model=BitacoraCambios)
def borrar_cambio(cambio_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    """Solo un cambio pendiente (error de carga). Uno aprobado o rechazado queda en la bitácora."""
    cambio, obra = _cambio_propio(sesion, dueno, cambio_id)
    ts.exigir_pendiente(cambio)
    sesion.delete(cambio)
    sesion.commit()
    return _bitacora(sesion, obra)


@rutas.post("/cambios/{cambio_id}/aprobar", response_model=BitacoraCambios)
def aprobar_cambio(
    cambio_id: int,
    datos: ResolucionCambio,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    cambio, obra = _cambio_propio(sesion, dueno, cambio_id)
    ts.aprobar_cambio(sesion, obra, cambio, dueno, datos.aprobador, datos.agregar_partida, datos.comentario)
    sesion.commit()
    return _bitacora(sesion, obra)


@rutas.post("/cambios/{cambio_id}/rechazar", response_model=BitacoraCambios)
def rechazar_cambio(
    cambio_id: int,
    datos: ResolucionCambio,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    cambio, obra = _cambio_propio(sesion, dueno, cambio_id)
    ts.rechazar_cambio(cambio, datos.aprobador, datos.comentario)
    sesion.commit()
    return _bitacora(sesion, obra)


# --- Riesgos y cambios por Excel ---


def _versiones_por_cambio(sesion: Session, obra_id: int) -> dict[int, int]:
    return dict(
        sesion.execute(
            select(LineaBase.cambio_id, LineaBase.version).where(
                LineaBase.obra_id == obra_id, LineaBase.cambio_id.is_not(None)
            )
        ).all()
    )


@rutas.get("/obras/{obra_id}/registros.xlsx")
def exportar_registros(obra_id: int, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)):
    obra = obra_propia(sesion, dueno, obra_id)
    contenido = rx.escribir_registros(
        _riesgos(sesion, obra.id), _cambios(sesion, obra.id), _versiones_por_cambio(sesion, obra.id)
    )
    return _excel(contenido, f"riesgos-y-cambios-obra-{obra.id}.xlsx")


async def _leer_registros(request: Request, sesion: Session, obra: Obra) -> rx.LecturaRegistros:
    contenido = await _leer_cuerpo(request)
    return await run_in_threadpool(rx.leer_registros, contenido, _riesgos(sesion, obra.id), _cambios(sesion, obra.id))


def _conteo(lista, nuevos: bool) -> int:
    return sum(1 for x in lista if (x.numero is None) == nuevos)


@rutas.post("/obras/{obra_id}/registros/previa", response_model=VistaPreviaRegistros)
async def vista_previa_registros(
    obra_id: int, request: Request, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra = obra_propia(sesion, dueno, obra_id)
    lec = await _leer_registros(request, sesion, obra)
    return VistaPreviaRegistros(
        valida=lec.valida,
        errores=_problemas(lec.errores),
        advertencias=_problemas(lec.advertencias),
        riesgos_nuevos=_conteo(lec.riesgos, True),
        riesgos_actualizados=_conteo(lec.riesgos, False),
        cambios_nuevos=_conteo(lec.cambios, True),
        cambios_actualizados=_conteo(lec.cambios, False),
    )


@rutas.post("/obras/{obra_id}/registros/importar", response_model=RegistrosImportados)
async def importar_registros(
    obra_id: int, request: Request, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    """Vuelve a validar y, si no hay errores, crea o actualiza riesgos y cambios (los cambios nuevos, pendientes)."""
    obra = obra_propia(sesion, dueno, obra_id)
    lec = await _leer_registros(request, sesion, obra)
    if not lec.valida:
        primero = lec.errores[0]
        donde = f"{primero.hoja}, fila {primero.fila}" if primero.fila else primero.hoja
        raise HTTPException(422, f"El archivo tiene {len(lec.errores)} error(es). Primero: {donde}: {primero.mensaje}")
    riesgos = {r.numero: r for r in _riesgos(sesion, obra.id)}
    siguiente = max(riesgos, default=0)
    for r in lec.riesgos:
        if r.numero is None:
            siguiente += 1
            sesion.add(Riesgo(obra_id=obra.id, numero=siguiente, **r.datos))
        else:
            for campo, valor in r.datos.items():
                setattr(riesgos[r.numero], campo, valor)
    cambios = {c.numero: c for c in _cambios(sesion, obra.id)}
    siguiente = max(cambios, default=0)
    for c in lec.cambios:
        if c.numero is None:
            siguiente += 1
            sesion.add(Cambio(obra_id=obra.id, numero=siguiente, estado="pendiente", **c.datos))
        else:
            for campo, valor in c.datos.items():
                setattr(cambios[c.numero], campo, valor)
    sesion.commit()
    return RegistrosImportados(
        riesgos=_registro(sesion, obra), cambios=_bitacora(sesion, obra), advertencias=_problemas(lec.advertencias)
    )
