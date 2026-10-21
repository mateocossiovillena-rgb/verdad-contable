"""Lo que se registra en obra: gastos, avances y cierres del día."""

from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, servicios
from app.db import obtener_sesion
from app.esquemas import (
    Anulacion,
    AvanceEntrada,
    AvanceSalida,
    CierreEntrada,
    Dia,
    GastoEntrada,
    GastoSalida,
    TipoGasto,
)
from app.modelos import TIPOS_GASTO, Avance, CierreDia, Gasto, Partida, Usuario
from app.seguridad import obra_propia, obra_visible, partida_visible, solo_dueno, usuario_actual

rutas = APIRouter(prefix="/api", tags=["registros"])


def _gasto_salida(sesion: Session, gasto: Gasto) -> GastoSalida:
    return GastoSalida.model_validate(servicios.gastos_con_nombres(sesion, [gasto])[0])


# --- Gastos ---


@rutas.post("/obras/{obra_id}/gastos", response_model=GastoSalida, status_code=status.HTTP_201_CREATED)
def registrar_gasto(
    obra_id: int,
    datos: GastoEntrada,
    response: Response,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_visible(sesion, usuario, obra_id)
    if datos.id_cliente:
        repetido = sesion.scalar(select(Gasto).where(Gasto.id_cliente == datos.id_cliente))
        if repetido is not None:
            if repetido.obra_id != obra_id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Registro duplicado")
            response.status_code = status.HTTP_200_OK
            return _gasto_salida(sesion, repetido)
    fecha = datos.fecha or servicios.hoy()
    if fecha > servicios.hoy():
        raise HTTPException(422, "No se pueden registrar gastos de días futuros")
    servicios.exigir_dia_abierto(sesion, obra_id, fecha)
    if datos.partida_id is None:
        partida = servicios.partida_generales(sesion, obra)
    else:
        partida = sesion.get(Partida, datos.partida_id)
        if partida is None or partida.obra_id != obra_id:
            raise HTTPException(422, "La partida no es de esta obra")
    gasto = Gasto(
        obra_id=obra_id,
        partida_id=partida.id,
        fecha=fecha,
        monto=datos.monto,
        tipo=datos.tipo,
        descripcion=datos.descripcion.strip(),
        con_factura=datos.con_factura,
        foto=servicios.guardar_foto(datos.foto_base64),
        usuario_id=usuario.id,
        id_cliente=datos.id_cliente,
    )
    sesion.add(gasto)
    sesion.commit()
    return _gasto_salida(sesion, gasto)


def _filtrar_gastos(
    sesion: Session,
    obra_id: int,
    desde: date | None,
    hasta: date | None,
    partida_id: int | None,
    tipo: str | None,
    sin_factura: bool,
    incluir_anulados: bool,
) -> list[Gasto]:
    consulta = select(Gasto).where(Gasto.obra_id == obra_id)
    if desde:
        consulta = consulta.where(Gasto.fecha >= desde)
    if hasta:
        consulta = consulta.where(Gasto.fecha <= hasta)
    if partida_id:
        consulta = consulta.where(Gasto.partida_id == partida_id)
    if tipo:
        consulta = consulta.where(Gasto.tipo == tipo)
    if sin_factura:
        consulta = consulta.where(Gasto.con_factura.is_(False))
    if not incluir_anulados:
        consulta = consulta.where(Gasto.anulado.is_(False))
    return list(sesion.scalars(consulta.order_by(Gasto.fecha.desc(), Gasto.id.desc())))


@rutas.get("/obras/{obra_id}/gastos", response_model=list[GastoSalida])
def listar_gastos(
    obra_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    partida_id: int | None = None,
    tipo: TipoGasto | None = None,
    sin_factura: bool = False,
    incluir_anulados: bool = False,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra_propia(sesion, dueno, obra_id)
    gastos = _filtrar_gastos(sesion, obra_id, desde, hasta, partida_id, tipo, sin_factura, incluir_anulados)
    return servicios.gastos_con_nombres(sesion, gastos)


@rutas.get("/obras/{obra_id}/gastos.xlsx")
def exportar_gastos(
    obra_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    partida_id: int | None = None,
    tipo: TipoGasto | None = None,
    sin_factura: bool = False,
    dueno: Usuario = Depends(solo_dueno),
    sesion: Session = Depends(obtener_sesion),
):
    obra = obra_propia(sesion, dueno, obra_id)
    gastos = servicios.gastos_con_nombres(
        sesion, _filtrar_gastos(sesion, obra_id, desde, hasta, partida_id, tipo, sin_factura, False)
    )
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Gastos"
    encabezados = ["Fecha", "Partida", "Tipo", "Descripción", f"Monto ({obra.moneda})", "Con factura", "Registró"]
    hoja.append(encabezados)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for g in gastos:
        hoja.append(
            [
                g["fecha"],
                g["partida_nombre"],
                TIPOS_GASTO.get(g["tipo"], g["tipo"]),
                g["descripcion"],
                float(g["monto"]),
                "Sí" if g["con_factura"] else "No",
                g["usuario_nombre"],
            ]
        )
        hoja.cell(row=hoja.max_row, column=1).number_format = "DD/MM/YYYY"
        hoja.cell(row=hoja.max_row, column=5).number_format = "#,##0.00"
    fila_total = hoja.max_row + 1
    hoja.cell(row=fila_total, column=4, value="TOTAL").font = Font(bold=True)
    if gastos:
        hoja.cell(row=fila_total, column=5, value=f"=SUM(E2:E{fila_total - 1})").number_format = "#,##0.00"
    for columna, ancho in zip("ABCDEFG", (12, 28, 14, 40, 14, 12, 20), strict=True):
        hoja.column_dimensions[columna].width = ancho
    archivo = BytesIO()
    libro.save(archivo)
    archivo.seek(0)
    nombre = f"gastos-obra-{obra.id}-{servicios.hoy().isoformat()}.xlsx"
    return StreamingResponse(
        archivo,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@rutas.post("/gastos/{gasto_id}/anular", response_model=GastoSalida)
def anular_gasto(
    gasto_id: int, datos: Anulacion, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    gasto = sesion.get(Gasto, gasto_id)
    if gasto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gasto no encontrado")
    obra_propia(sesion, dueno, gasto.obra_id)
    if gasto.anulado:
        raise HTTPException(status.HTTP_409_CONFLICT, "El gasto ya estaba anulado")
    servicios.exigir_dia_abierto(sesion, gasto.obra_id, gasto.fecha)
    gasto.anulado = True
    gasto.motivo_anulacion = datos.motivo.strip()
    gasto.anulado_por = dueno.id
    sesion.commit()
    return _gasto_salida(sesion, gasto)


# --- Avances ---


@rutas.post("/partidas/{partida_id}/avances", response_model=AvanceSalida, status_code=status.HTTP_201_CREATED)
def registrar_avance(
    partida_id: int,
    datos: AvanceEntrada,
    response: Response,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    partida = partida_visible(sesion, usuario, partida_id)
    if partida.es_generales:
        raise HTTPException(422, "Los gastos generales no tienen avance físico")
    if datos.id_cliente:
        repetido = sesion.scalar(select(Avance).where(Avance.id_cliente == datos.id_cliente))
        if repetido is not None:
            if repetido.partida_id != partida_id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Registro duplicado")
            response.status_code = status.HTTP_200_OK
            return repetido
    fecha = datos.fecha or servicios.hoy()
    if fecha > servicios.hoy():
        raise HTTPException(422, "No se puede registrar avance de días futuros")
    avance = Avance(
        partida_id=partida_id,
        fecha=fecha,
        porcentaje=datos.porcentaje,
        nota=datos.nota.strip(),
        foto=servicios.guardar_foto(datos.foto_base64),
        usuario_id=usuario.id,
        id_cliente=datos.id_cliente,
    )
    sesion.add(avance)
    sesion.commit()
    return avance


@rutas.get("/partidas/{partida_id}/avances", response_model=list[AvanceSalida])
def historial_avances(
    partida_id: int, usuario: Usuario = Depends(usuario_actual), sesion: Session = Depends(obtener_sesion)
):
    partida_visible(sesion, usuario, partida_id)
    return list(
        sesion.scalars(
            select(Avance).where(Avance.partida_id == partida_id).order_by(Avance.fecha.desc(), Avance.id.desc())
        )
    )


# --- Día y cierres ---


@rutas.get("/obras/{obra_id}/dia", response_model=Dia)
def ver_dia(
    obra_id: int,
    fecha: date | None = None,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    obra_visible(sesion, usuario, obra_id)
    fecha = fecha or servicios.hoy()
    gastos = list(
        sesion.scalars(
            select(Gasto)
            .where(Gasto.obra_id == obra_id, Gasto.fecha == fecha, Gasto.anulado.is_(False))
            .order_by(Gasto.creado_en)
        )
    )
    cierre = servicios.cierre_de(sesion, obra_id, fecha)
    cerrado_por = sesion.get(Usuario, cierre.usuario_id).nombre if cierre else None
    return Dia(
        obra_id=obra_id,
        fecha=fecha,
        gastos=[GastoSalida.model_validate(g) for g in servicios.gastos_con_nombres(sesion, gastos)],
        total_dia=servicios.gastado_en(sesion, obra_id, fecha),
        acumulado=servicios.gastado_hasta(sesion, obra_id, fecha),
        cerrado=cierre is not None,
        cerrado_por=cerrado_por,
    )


@rutas.post("/obras/{obra_id}/cierres", response_model=Dia, status_code=status.HTTP_201_CREATED)
def cerrar_dia(
    obra_id: int,
    datos: CierreEntrada,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    obra_visible(sesion, usuario, obra_id)
    fecha = datos.fecha or servicios.hoy()
    if fecha > servicios.hoy():
        raise HTTPException(422, "No se puede cerrar un día futuro")
    servicios.exigir_dia_abierto(sesion, obra_id, fecha)
    sesion.add(
        CierreDia(
            obra_id=obra_id,
            fecha=fecha,
            total_dia=servicios.gastado_en(sesion, obra_id, fecha),
            acumulado=servicios.gastado_hasta(sesion, obra_id, fecha),
            usuario_id=usuario.id,
        )
    )
    sesion.commit()
    return ver_dia(obra_id, fecha, usuario, sesion)


@rutas.delete("/obras/{obra_id}/cierres/{fecha}", status_code=status.HTTP_204_NO_CONTENT)
def reabrir_dia(
    obra_id: int, fecha: date, dueno: Usuario = Depends(solo_dueno), sesion: Session = Depends(obtener_sesion)
):
    obra_propia(sesion, dueno, obra_id)
    cierre = servicios.cierre_de(sesion, obra_id, fecha)
    if cierre is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese día no está cerrado")
    sesion.delete(cierre)
    sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Fotos ---


@rutas.get("/fotos/{nombre}")
def ver_foto(nombre: str = Path(pattern=r"^[0-9a-f]{32}\.(jpg|png|webp)$")):
    # Los nombres son aleatorios (128 bits), así que no se pueden adivinar.
    ruta = config.CARPETA_FOTOS / nombre
    if not ruta.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Foto no encontrada")
    return FileResponse(ruta, headers={"Cache-Control": "private, max-age=31536000, immutable"})
