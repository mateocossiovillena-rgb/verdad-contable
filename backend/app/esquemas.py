"""Formas de los datos que entran y salen de la API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.calculos import cronograma as cr

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
    desde_cronograma: bool = False
    actividad_id: int | None = None
    porcentaje_avance: float = 0
    regla_medicion: str = "porcentaje"


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


ReglaMedicion = Literal["porcentaje", "0_100", "50_50"]


class MedicionEntrada(BaseModel):
    regla_medicion: ReglaMedicion


class PronosticoSalida(BaseModel):
    clave: str
    nombre: str
    formula: str
    supuesto: str
    eac: DineroOpcional
    etc: DineroOpcional
    vac: DineroOpcional


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
    # Pronóstico AACE 80R-13 y contra qué se mide (línea base vigente o plan sin aprobar).
    pronosticos: list[PronosticoSalida] = []
    tcpi: float | None = None
    linea_base_version: int | None = None


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


UnidadDuracion = Literal["dias", "semanas", "meses"]


class ActividadEntrada(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    duracion: Decimal | None = Field(default=None, ge=Decimal("0.5"), le=3650, decimal_places=1)
    unidad_duracion: UnidadDuracion = "semanas"
    # Alternativa en días (compatibilidad); si viene `duracion`, se calcula a partir de ella.
    duracion_dias: int | None = Field(default=None, ge=1, le=3650)
    inicio_manual: date | None = Field(default=None, description="Se ignora si hay predecesoras")
    predecesoras: list[int] = []
    fase_id: int | None = Field(default=None, description="Solo al editar, para mover de fase")
    # None = no tocar los recursos que ya tiene; [] = quitarlos todos.
    recursos: list[RecursoEntrada] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def _duracion(self):
        if self.duracion is not None:
            self.duracion_dias = cr.a_dias(self.duracion, self.unidad_duracion)
            if self.duracion_dias > 3650:
                raise ValueError("La duración no puede pasar de 10 años")
        elif self.duracion_dias is not None:
            self.duracion, self.unidad_duracion = Decimal(self.duracion_dias), "dias"
        else:
            raise ValueError("Falta la duración")
        return self


class ActividadSalida(BaseModel):
    id: int
    fase_id: int
    nombre: str
    duracion_dias: int
    duracion_cantidad: float | None
    unidad_duracion: str
    inicio_manual: date | None
    fecha_inicio: date
    fecha_fin: date
    orden: int
    predecesoras: list[int]
    holgura_dias: int = Field(description="Días que puede atrasarse sin mover el fin de la obra")
    critica: bool = Field(description="En la ruta crítica (holgura 0)")
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
PasoEstimacion = Literal["capas", "plantas", "formulario", "cantidades", "confirmada", "generada"]
Oficio = Literal[
    "tierras",
    "estructura",
    "albanileria",
    "pisos",
    "electricidad",
    "plomeria",
    "carpinteria",
    "techo",
    "pintura",
    "limpieza",
]


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
    ejecucion: dict | None
    creado_en: datetime


class EstimacionResumen(Modelo):
    id: int
    tipo_archivo: str
    nombre_archivo: str
    paso: str
    creado_en: datetime


class EjecucionEntrada(BaseModel):
    fecha_inicio: date
    dias_semana: Literal[5, 6, 7] = 6
    entrega_deseada: date | None = None
    cuadrillas: dict[Oficio, Annotated[int, Field(ge=1, le=10)]] = Field(default_factory=dict)
    subcontratos: list[Oficio] = Field(default_factory=list, description="Oficios que no compiten por cuadrilla")

    @model_validator(mode="after")
    def _fechas(self):
        if self.entrega_deseada and self.entrega_deseada <= self.fecha_inicio:
            raise ValueError("La entrega deseada debe ser después del inicio")
        return self


class GenerarEntrada(EjecucionEntrada):
    modo: Literal["reemplazar", "agregar"]


class EnlacePasoSalida(BaseModel):
    clave: str
    desfase_dias: int
    origen: Literal["tecnica", "cuadrilla"]


class PasoSalida(BaseModel):
    clave: str
    nombre: str
    fase: str
    oficio: Oficio
    cantidad: float | None
    unidad: str
    dias_trabajo: int
    duracion_dias: int
    personas: int
    inicio: date
    fin: date
    holgura_dias: int
    critica: bool
    predecesoras: list[EnlacePasoSalida]
    costo_mano_obra: Dinero
    costo_materiales: Dinero


class OficioSalida(BaseModel):
    clave: Oficio
    nombre: str
    cuadrillas: int
    subcontrato: bool
    personas_por_cuadrilla: int
    pasos: int
    dias_trabajo: int
    en_ruta_critica: bool


class SugerenciaSalida(BaseModel):
    oficio: Oficio
    nombre: str
    dias_menos: int
    costo_extra: Dinero


class PropuestaSalida(BaseModel):
    ejecucion: EjecucionEntrada
    pasos: list[PasoSalida]
    fases: list[str]
    oficios: list[OficioSalida]
    inicio: date
    fin: date
    dias_calendario: int
    entrega_deseada: date | None
    dias_de_retraso: int | None
    costo_mano_obra: Dinero
    costo_materiales: Dinero
    costo_total: Dinero
    sugerencias: list[SugerenciaSalida]
    actividades_actuales: int = Field(description="Actividades que ya tiene el cronograma de la obra")


# --- Kit TCM: estimado, clase, base del estimado y línea base ---

Porcentaje = Annotated[Decimal, Field(ge=0, le=100, max_digits=6, decimal_places=2)]
EstadoEntregable = Literal["no", "parcial", "completo"]


class ParametrosApuEntrada(BaseModel):
    cargas_sociales: Porcentaje = Decimal("0")
    iva_mano_obra: Porcentaje = Decimal("0")
    herramientas: Porcentaje = Decimal("0")
    gastos_generales: Porcentaje = Decimal("0")
    utilidad: Porcentaje = Decimal("0")
    impuestos: Porcentaje = Decimal("0")


class ParametrosApuSalida(BaseModel):
    cargas_sociales: float
    iva_mano_obra: float
    herramientas: float
    gastos_generales: float
    utilidad: float
    impuestos: float


class ApuSalida(BaseModel):
    materiales: Dinero
    mano_obra: Dinero
    cargas_sociales: Dinero
    iva_mano_obra: Dinero
    equipo: Dinero
    herramientas: Dinero
    costo_directo: Dinero
    gastos_generales: Dinero
    utilidad: Dinero
    impuestos: Dinero
    total: Dinero


class InsumoSalida(BaseModel):
    tipo: str
    descripcion: str
    unidad: str
    rendimiento: float | None
    cantidad: float
    precio_unitario: Dinero
    parcial: Dinero


class ActividadEstimadaSalida(BaseModel):
    id: int
    codigo: str
    nombre: str
    unidad: str
    computo: float | None
    fecha_inicio: date
    fecha_fin: date
    apu: ApuSalida
    precio_unitario: DineroOpcional
    insumos: list[InsumoSalida]


class FaseEstimadaSalida(BaseModel):
    id: int
    nombre: str
    total: Dinero
    actividades: list[ActividadEstimadaSalida]


class EntregableSalida(BaseModel):
    clave: str
    nombre: str
    peso: float
    estado: EstadoEntregable


class ClaseSalida(BaseModel):
    clase: int
    definicion_norma: str
    uso: str
    metodologia: str
    exactitud_baja: list[int]
    exactitud_alta: list[int]


class ClasificacionSalida(BaseModel):
    entregables: list[EntregableSalida]
    porcentaje_definicion: float
    clase: ClaseSalida
    minimo: DineroOpcional
    maximo: DineroOpcional
    clases: list[ClaseSalida]


class ClasificacionEntrada(BaseModel):
    entregables: dict[str, EstadoEntregable]


class BaseEstimadoEntrada(BaseModel):
    proposito: str = Field(default="", max_length=5000)
    alcance: str = Field(default="", max_length=5000)
    metodologia: str = Field(default="", max_length=5000)
    base_diseno: str = Field(default="", max_length=5000)
    base_planificacion: str = Field(default="", max_length=5000)
    fuentes_precios: str = Field(default="", max_length=5000)
    fecha_precios: date | None = None
    supuestos: str = Field(default="", max_length=5000)
    exclusiones: str = Field(default="", max_length=5000)
    riesgos_oportunidades: str = Field(default="", max_length=5000)
    contingencia_porcentaje: Porcentaje = Decimal("0")
    contingencia_nota: str = Field(default="", max_length=5000)


class BaseEstimadoSalida(BaseEstimadoEntrada, Modelo):
    contingencia_porcentaje: Dinero
    contingencia_monto: Dinero = Decimal("0")


class LineaBaseEntrada(BaseModel):
    motivo: str = Field(default="", max_length=2000)


class LineaBasePartidaSalida(Modelo):
    partida_id: int | None
    codigo: str
    nombre: str
    fase: str
    fecha_inicio: date | None
    fecha_fin: date | None
    presupuesto: Dinero


class SemanaSalida(BaseModel):
    numero: int
    inicio: date
    fin: date
    pv: Dinero
    pv_acumulado: Dinero
    porcentaje_acumulado: float | None


class LineaBaseResumen(Modelo):
    id: int
    version: int
    aprobada_en: datetime
    aprobada_por_nombre: str = ""
    motivo: str
    bac: Dinero
    fecha_inicio: date
    fecha_fin: date
    clase: int | None
    vigente: bool


class LineaBaseDetalle(LineaBaseResumen):
    partidas: list[LineaBasePartidaSalida]
    semanas: list[SemanaSalida]


class EstimadoObra(BaseModel):
    obra: ObraSalida
    parametros: ParametrosApuSalida
    fases: list[FaseEstimadaSalida]
    totales: ApuSalida
    clasificacion: ClasificacionSalida
    base: BaseEstimadoSalida
    lineas_base: list[LineaBaseResumen]
    vigente: LineaBaseDetalle | None
    # True si el plan cambió desde la línea base vigente (otro BAC o fechas): hay que aprobar una nueva.
    plan_distinto_de_base: bool = False


class ProblemaSalida(BaseModel):
    hoja: str
    fila: int | None
    columna: str
    mensaje: str


class ResumenImportacion(BaseModel):
    nombre: str
    fecha_inicio: date | None
    moneda: str
    fases: int
    actividades: int
    insumos: int
    total_estimado: Dinero
    porcentaje_definicion: float
    clase: int


class VistaPrevia(BaseModel):
    valida: bool
    errores: list[ProblemaSalida]
    advertencias: list[ProblemaSalida]
    resumen: ResumenImportacion | None


class ObraImportada(BaseModel):
    obra: ObraSalida
    advertencias: list[ProblemaSalida]
