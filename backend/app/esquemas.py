"""Formas de los datos que entran y salen de la API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

# El dinero se calcula con Decimal y se envía como número al navegador.
Dinero = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
DineroOpcional = Annotated[
    Decimal | None,
    PlainSerializer(lambda v: None if v is None else float(v), return_type=float | None, when_used="json"),
]
MontoEntrada = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]
TipoGasto = Literal["material", "mano_obra", "subcontrato", "caja_chica", "transporte"]
Moneda = Literal["Bs", "USD"]


class Modelo(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _validar_fechas(inicio: date | None, fin: date | None) -> None:
    if inicio and fin and fin < inicio:
        raise ValueError("La fecha de fin no puede ser anterior a la de inicio")


# --- Sesión y usuarios ---


class RegistroDueno(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    correo: str = Field(min_length=5, max_length=200, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    clave: str = Field(min_length=8, max_length=200)


class Ingreso(BaseModel):
    usuario: str = Field(min_length=3, description="Correo (dueño) o teléfono (encargado)")
    clave: str = Field(min_length=1)


class UsuarioSalida(Modelo):
    id: int
    nombre: str
    correo: str | None
    telefono: str | None
    rol: str
    activo: bool


class Sesion(BaseModel):
    token: str
    usuario: UsuarioSalida


class EncargadoNuevo(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    telefono: str = Field(min_length=7, max_length=30, pattern=r"^\+?[0-9 ]+$")
    pin: str = Field(pattern=r"^[0-9]{6}$", description="PIN de 6 dígitos")
    obra_ids: list[int] = []


class EncargadoCambios(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    pin: str | None = Field(default=None, pattern=r"^[0-9]{6}$")
    activo: bool | None = None
    obra_ids: list[int] | None = None


class EncargadoSalida(UsuarioSalida):
    obra_ids: list[int] = []


# --- Obras, partidas, hitos ---


class ObraEntrada(BaseModel):
    nombre: str = Field(min_length=2, max_length=160)
    ubicacion: str = Field(default="", max_length=200)
    cliente: str = Field(default="", max_length=160)
    fecha_inicio: date
    # Opcional: si no se indica, la obra termina donde termina su cronograma.
    fecha_fin: date | None = None
    moneda: Moneda = "Bs"
    presupuesto_total: MontoEntrada | None = None
    umbral_amarillo: Decimal = Field(default=Decimal("0.90"), gt=0, le=2, decimal_places=2)
    umbral_rojo: Decimal = Field(default=Decimal("0.80"), gt=0, le=2, decimal_places=2)

    @model_validator(mode="after")
    def _coherente(self):
        _validar_fechas(self.fecha_inicio, self.fecha_fin)
        if self.umbral_rojo > self.umbral_amarillo:
            raise ValueError("El umbral rojo debe ser menor o igual al amarillo")
        return self


class ObraSalida(Modelo):
    id: int
    nombre: str
    ubicacion: str
    cliente: str
    fecha_inicio: date
    fecha_fin: date
    moneda: str
    presupuesto_total: DineroOpcional = None
    umbral_amarillo: Dinero
    umbral_rojo: Dinero


class ObraResumen(ObraSalida):
    """Para el encargado solo se llena `gastado_hoy`; los totales los ve el dueño."""

    gastado_hoy: Dinero
    presupuesto: DineroOpcional = None
    gastado: DineroOpcional = None
    avance_real: float | None = None
    avance_planificado: float | None = None
    spi: float | None = None
    cpi: float | None = None
    semaforo: str | None = None
    alertas: int = 0


class PartidaEntrada(BaseModel):
    codigo: str = Field(default="", max_length=20)
    nombre: str = Field(min_length=1, max_length=160)
    fase: str = Field(default="", max_length=80)
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    presupuesto: MontoEntrada = Decimal("0")
    orden: int | None = None

    @model_validator(mode="after")
    def _coherente(self):
        _validar_fechas(self.fecha_inicio, self.fecha_fin)
        return self


class PartidaSalida(Modelo):
    id: int
    obra_id: int
    codigo: str
    nombre: str
    fase: str
    fecha_inicio: date | None
    fecha_fin: date | None
    presupuesto: Dinero
    orden: int
    es_generales: bool
    porcentaje_avance: float = 0


class HitoEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    fecha_prevista: date
    fecha_real: date | None = None


class HitoSalida(Modelo):
    id: int
    obra_id: int
    nombre: str
    fecha_prevista: date
    fecha_real: date | None


# --- Avances y gastos ---


class AvanceEntrada(BaseModel):
    fecha: date | None = None
    porcentaje: Decimal = Field(ge=0, le=100, decimal_places=2)
    nota: str = Field(default="", max_length=2000)
    foto_base64: str | None = None
    id_cliente: str | None = Field(default=None, max_length=64)


class AvanceSalida(Modelo):
    id: int
    partida_id: int
    fecha: date
    porcentaje: float
    nota: str
    foto: str | None
    usuario_id: int
    creado_en: datetime


class GastoEntrada(BaseModel):
    fecha: date | None = None
    monto: MontoEntrada
    tipo: TipoGasto
    partida_id: int | None = None
    descripcion: str = Field(default="", max_length=2000)
    con_factura: bool = False
    foto_base64: str | None = None
    id_cliente: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _positivo(self):
        if self.monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        return self


class GastoSalida(Modelo):
    id: int
    obra_id: int
    partida_id: int
    partida_nombre: str = ""
    fecha: date
    monto: Dinero
    tipo: str
    descripcion: str
    con_factura: bool
    foto: str | None
    usuario_id: int
    usuario_nombre: str = ""
    creado_en: datetime
    anulado: bool
    motivo_anulacion: str


class Anulacion(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)


# --- Día y cierres ---


class Dia(BaseModel):
    obra_id: int
    fecha: date
    gastos: list[GastoSalida]
    total_dia: Dinero
    acumulado: Dinero
    cerrado: bool
    cerrado_por: str | None = None


class CierreEntrada(BaseModel):
    fecha: date | None = None


# --- Indicadores ---


class AdvertenciaSalida(BaseModel):
    codigo: str
    mensaje: str


class IndicadoresSalida(BaseModel):
    bac: Dinero
    pv: Dinero
    ev: Dinero
    ac: Dinero
    sv: Dinero
    cv: Dinero
    spi: float | None
    cpi: float | None
    eac: DineroOpcional
    avance_planificado: float | None
    avance_real: float | None
    avance_esperado_por_gasto: float | None


class PartidaIndicadores(BaseModel):
    partida: PartidaSalida
    porcentaje_avance: float
    indicadores: IndicadoresSalida
    semaforo: str
    advertencias: list[AdvertenciaSalida]


class PuntoCurvaSalida(BaseModel):
    fecha: date
    pv: Dinero
    ev: DineroOpcional
    ac: DineroOpcional


class IndicadoresObra(BaseModel):
    obra: ObraSalida
    corte: date
    indicadores: IndicadoresSalida
    semaforo: str
    frases: list[str]
    advertencias: list[AdvertenciaSalida]
    partidas: list[PartidaIndicadores]
    curva: list[PuntoCurvaSalida]
    hitos: list[HitoSalida]


class Alerta(BaseModel):
    obra_id: int
    obra_nombre: str
    partida_id: int | None = None
    nivel: Literal["amarillo", "rojo"]
    mensaje: str


# --- Cronograma ---


class FaseEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)


class OrdenFases(BaseModel):
    ids: list[int] = Field(description="Ids de todas las fases de la obra en el nuevo orden")


TipoRecurso = Literal["mano_obra", "material"]


class RecursoEntrada(BaseModel):
    tipo: TipoRecurso
    descripcion: str = Field(min_length=1, max_length=160, description="Cargo (Albañil) o material (Cemento)")
    unidad: str = Field(default="", max_length=20, description="Solo materiales: bolsa, m³, pieza…")
    cantidad: Decimal = Field(gt=0, max_digits=14, decimal_places=3, description="Personas o cantidad")
    precio_unitario: MontoEntrada = Field(description="Costo por persona o precio por unidad")
    por_dia: bool = Field(default=False, description="Mano de obra pagada por día (jornal)")

    @model_validator(mode="after")
    def _coherente(self):
        if self.tipo == "material":
            self.por_dia = False
        elif self.cantidad != self.cantidad.to_integral_value():
            raise ValueError("La cantidad de personas debe ser un número entero")
        return self


class RecursoSalida(BaseModel):
    id: int
    tipo: str
    descripcion: str
    unidad: str
    cantidad: float
    precio_unitario: Dinero
    por_dia: bool
    costo: Dinero


class ActividadEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    duracion_dias: int = Field(ge=1, le=3650)
    inicio_manual: date | None = Field(default=None, description="Se ignora si hay predecesoras")
    predecesoras: list[int] = []
    fase_id: int | None = Field(default=None, description="Solo al editar, para mover de fase")
    # None = no tocar los recursos que ya tiene; [] = quitarlos todos.
    recursos: list[RecursoEntrada] | None = Field(default=None, max_length=100)


class ActividadSalida(BaseModel):
    id: int
    fase_id: int
    nombre: str
    duracion_dias: int
    inicio_manual: date | None
    fecha_inicio: date
    fecha_fin: date
    orden: int
    predecesoras: list[int]
    recursos: list[RecursoSalida] = []
    costo_mano_obra: Dinero = Decimal("0")
    costo_materiales: Dinero = Decimal("0")
    costo_total: Dinero = Decimal("0")


class FaseSalida(BaseModel):
    id: int
    nombre: str
    orden: int
    actividades: list[ActividadSalida]
    costo_total: Dinero = Decimal("0")


class Cronograma(BaseModel):
    obra: ObraSalida
    hoy: date
    fecha_inicio: date
    fecha_fin: date
    fases: list[FaseSalida]
    costo_mano_obra: Dinero = Decimal("0")
    costo_materiales: Dinero = Decimal("0")
    costo_total: Dinero = Decimal("0")


# --- Estimación desde plano ---

RolCapa = Literal["muros", "puertas", "ventanas", "ambientes", "columnas", "ignorar"]
PasoEstimacion = Literal["capas", "plantas", "formulario", "cantidades", "confirmada"]


class CapasEntrada(BaseModel):
    capas: dict[str, RolCapa]
    unidades: Literal[1, 2, 4, 5, 6] = Field(description="1 pulgadas, 2 pies, 4 mm, 5 cm, 6 m")


class PlantaEntrada(BaseModel):
    indice: int = Field(ge=0)
    nombre: str = Field(max_length=60)
    incluir: bool
    repeticiones: int = Field(default=1, ge=1, le=60)


class FormularioEntrada(BaseModel):
    tipo_obra: Literal["vivienda", "departamentos", "comercial"] = "vivienda"
    altura_piso: float = Field(default=2.60, ge=2.0, le=6.0)
    tipo_muro: Literal["ladrillo_6h", "bloque_cemento", "adobe"] = "ladrillo_6h"
    espesor_exterior: float = Field(default=0.18, ge=0.08, le=0.6)
    espesor_interior: float = Field(default=0.12, ge=0.05, le=0.4)
    losa: Literal["alivianada", "maciza", "viguetas"] = "alivianada"
    cubierta: Literal["losa", "calamina", "teja"] = "losa"
    fundacion: Literal["zapatas", "cimiento_corrido"] = "zapatas"
    acabado: Literal["economico", "medio", "alto"] = "medio"
    piso: Literal["ceramica", "porcelanato", "cemento"] = "ceramica"
    banos: int | None = Field(default=None, ge=0, le=50)
    cocinas: int | None = Field(default=None, ge=0, le=50)


class CantidadesEntrada(BaseModel):
    ediciones: dict[str, Annotated[float, Field(ge=0, le=1_000_000)]] = Field(default_factory=dict)
    confirmar: bool = False


class CapaSalida(BaseModel):
    nombre: str
    lineas: int
    bloques: int
    arcos: int
    textos: int
    rol: RolCapa
    rol_sugerido: RolCapa
    recordada: bool


class PlantaSalida(BaseModel):
    indice: int
    nombre: str
    incluir: bool
    repeticiones: int
    ancho: float | None
    alto: float | None
    detalle: str


class PisoMedidoSalida(BaseModel):
    nombre: str
    repeticiones: int
    area_planta: float
    largo_muros: float
    perimetro_exterior: float
    ambientes: int
    banos: int
    cocinas: int
    puertas: int
    ventanas: int


class CantidadSalida(BaseModel):
    clave: str
    rubro: str
    nombre: str
    piso: str | None
    unidad: str
    cantidad: float
    cantidad_original: float | None  # lo calculado, si se corrigió a mano
    origen: Literal["plano", "formulario", "proporcion", "editada"]
    origen_original: Literal["plano", "formulario", "proporcion"] | None
    detalle: str


class EstimacionSalida(BaseModel):
    id: int
    obra_id: int
    tipo_archivo: Literal["dxf", "ifc"]
    nombre_archivo: str
    paso: PasoEstimacion
    pasos: list[PasoEstimacion]
    unidades: int | None
    unidades_deducidas: bool
    capas: list[CapaSalida]
    plantas: list[PlantaSalida]
    formulario: dict | None
    datos_del_modelo: list[str]
    pisos_medidos: list[PisoMedidoSalida]
    cantidades: list[CantidadSalida]
    avisos: list[str]
    creado_en: datetime


class EstimacionResumen(Modelo):
    id: int
    tipo_archivo: str
    nombre_archivo: str
    paso: str
    creado_en: datetime
