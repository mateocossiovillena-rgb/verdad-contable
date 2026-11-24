export type Rol = "dueno" | "encargado";
export type Semaforo = "verde" | "amarillo" | "rojo" | "sin_dato";
export type TipoGasto = "material" | "mano_obra" | "subcontrato" | "caja_chica" | "transporte";

export const TIPOS_GASTO: Record<TipoGasto, string> = {
  material: "Material",
  mano_obra: "Mano de obra",
  subcontrato: "Subcontrato",
  caja_chica: "Caja chica",
  transporte: "Transporte",
};

export interface Usuario {
  id: number;
  nombre: string;
  correo: string | null;
  telefono: string | null;
  rol: Rol;
  activo: boolean;
}

export interface Encargado extends Usuario {
  obra_ids: number[];
}

export type Moneda = "Bs" | "USD";

export interface Obra {
  id: number;
  nombre: string;
  ubicacion: string;
  cliente: string;
  fecha_inicio: string;
  fecha_fin: string;
  moneda: Moneda;
  presupuesto_total: number | null;
  umbral_amarillo: number;
  umbral_rojo: number;
}

export interface ObraResumen extends Obra {
  gastado_hoy: number;
  presupuesto: number | null;
  gastado: number | null;
  avance_real: number | null;
  avance_planificado: number | null;
  spi: number | null;
  cpi: number | null;
  semaforo: Semaforo | null;
  alertas: number;
}

export interface Partida {
  id: number;
  obra_id: number;
  codigo: string;
  nombre: string;
  fase: string;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  presupuesto: number;
  orden: number;
  es_generales: boolean;
  /** Sale de una actividad del cronograma: se cambia desde allí, no desde Partidas. */
  desde_cronograma: boolean;
  actividad_id: number | null;
  porcentaje_avance: number;
  regla_medicion: ReglaMedicion;
}

/** Cómo se convierte el % físico en valor ganado (AACE 82R-13). */
export type ReglaMedicion = "porcentaje" | "0_100" | "50_50";

export interface Pronostico {
  clave: "atipico" | "cpi" | "cpi_spi";
  nombre: string;
  formula: string;
  supuesto: string;
  eac: number | null;
  etc: number | null;
  vac: number | null;
}

export interface Hito {
  id: number;
  obra_id: number;
  nombre: string;
  fecha_prevista: string;
  fecha_real: string | null;
}

export interface Gasto {
  id: number;
  obra_id: number;
  partida_id: number;
  partida_nombre: string;
  fecha: string;
  monto: number;
  tipo: TipoGasto;
  descripcion: string;
  con_factura: boolean;
  foto: string | null;
  usuario_id: number;
  usuario_nombre: string;
  creado_en: string;
  anulado: boolean;
  motivo_anulacion: string;
}

export interface Dia {
  obra_id: number;
  fecha: string;
  gastos: Gasto[];
  total_dia: number;
  acumulado: number;
  cerrado: boolean;
  cerrado_por: string | null;
}

export interface Indicadores {
  bac: number;
  pv: number;
  ev: number;
  ac: number;
  sv: number;
  cv: number;
  spi: number | null;
  cpi: number | null;
  eac: number | null;
  avance_planificado: number | null;
  avance_real: number | null;
  avance_esperado_por_gasto: number | null;
}

export interface Advertencia {
  codigo: string;
  mensaje: string;
}

export interface PartidaIndicadores {
  partida: Partida;
  porcentaje_avance: number;
  indicadores: Indicadores;
  semaforo: Semaforo;
  advertencias: Advertencia[];
}

export interface PuntoCurva {
  fecha: string;
  pv: number;
  ev: number | null;
  ac: number | null;
}

export interface IndicadoresObra {
  obra: Obra;
  corte: string;
  indicadores: Indicadores;
  semaforo: Semaforo;
  frases: string[];
  advertencias: Advertencia[];
  partidas: PartidaIndicadores[];
  curva: PuntoCurva[];
  hitos: Hito[];
  pronosticos: Pronostico[];
  tcpi: number | null;
  linea_base_version: number | null;
}

export interface Alerta {
  obra_id: number;
  obra_nombre: string;
  partida_id: number | null;
  nivel: "amarillo" | "rojo";
  mensaje: string;
}

export type TipoRecurso = "mano_obra" | "material";

export interface Recurso {
  id: number;
  tipo: TipoRecurso;
  descripcion: string;
  unidad: string;
  cantidad: number;
  precio_unitario: number;
  por_dia: boolean;
  costo: number;
}

export type UnidadDuracion = "dias" | "semanas" | "meses";

export interface Actividad {
  id: number;
  fase_id: number;
  nombre: string;
  duracion_dias: number;
  /** Duración tal como la escribió el usuario; `duracion_dias` es su equivalente en días calendario. */
  duracion_cantidad: number | null;
  unidad_duracion: UnidadDuracion;
  inicio_manual: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  orden: number;
  predecesoras: number[];
  holgura_dias: number;
  critica: boolean;
  recursos: Recurso[];
  costo_mano_obra: number;
  costo_materiales: number;
  costo_total: number;
}

export interface Fase {
  id: number;
  nombre: string;
  orden: number;
  actividades: Actividad[];
  costo_total: number;
}

export interface Cronograma {
  obra: Obra;
  hoy: string;
  fecha_inicio: string;
  fecha_fin: string;
  fases: Fase[];
  costo_mano_obra: number;
  costo_materiales: number;
  costo_total: number;
}

// --- Estimación desde plano ---

export type RolCapa = "muros" | "puertas" | "ventanas" | "ambientes" | "columnas" | "ignorar";
export type PasoEstimacion = "capas" | "plantas" | "formulario" | "cantidades" | "confirmada" | "generada";
export type OrigenCantidad = "plano" | "formulario" | "proporcion" | "editada";

export interface CapaPlano {
  nombre: string;
  lineas: number;
  bloques: number;
  arcos: number;
  textos: number;
  rol: RolCapa;
  rol_sugerido: RolCapa;
  recordada: boolean;
}

export interface PlantaPlano {
  indice: number;
  nombre: string;
  incluir: boolean;
  repeticiones: number;
  ancho: number | null;
  alto: number | null;
  detalle: string;
}

export interface PisoMedido {
  nombre: string;
  repeticiones: number;
  area_planta: number;
  largo_muros: number;
  perimetro_exterior: number;
  ambientes: number;
  banos: number;
  cocinas: number;
  puertas: number;
  ventanas: number;
}

export interface CantidadObra {
  clave: string;
  rubro: string;
  nombre: string;
  piso: string | null;
  unidad: string;
  cantidad: number;
  cantidad_original: number | null;
  origen: OrigenCantidad;
  origen_original: Exclude<OrigenCantidad, "editada"> | null;
  detalle: string;
}

export interface FormularioPlano {
  tipo_obra: "vivienda" | "departamentos" | "comercial";
  altura_piso: number;
  tipo_muro: "ladrillo_6h" | "bloque_cemento" | "adobe";
  espesor_exterior: number;
  espesor_interior: number;
  losa: "alivianada" | "maciza" | "viguetas";
  cubierta: "losa" | "calamina" | "teja";
  fundacion: "zapatas" | "cimiento_corrido";
  acabado: "economico" | "medio" | "alto";
  piso: "ceramica" | "porcelanato" | "cemento";
  banos: number | null;
  cocinas: number | null;
}

export interface Estimacion {
  id: number;
  obra_id: number;
  tipo_archivo: "dxf" | "ifc";
  nombre_archivo: string;
  paso: PasoEstimacion;
  pasos: PasoEstimacion[];
  unidades: number | null;
  unidades_deducidas: boolean;
  capas: CapaPlano[];
  plantas: PlantaPlano[];
  formulario: FormularioPlano | null;
  datos_del_modelo: string[];
  pisos_medidos: PisoMedido[];
  cantidades: CantidadObra[];
  avisos: string[];
  ejecucion: Ejecucion | null;
  creado_en: string;
}

export interface EstimacionResumen {
  id: number;
  tipo_archivo: "dxf" | "ifc";
  nombre_archivo: string;
  paso: PasoEstimacion;
  creado_en: string;
}

/** Segmento [x1, y1, x2, y2] en metros, con el origen abajo a la izquierda. */
export type Segmento = [number, number, number, number];

export interface PlantaDibujada {
  nombre: string;
  ancho: number;
  alto: number;
  muros: Segmento[];
  ambientes: { nombre: string; area: number; puntos: [number, number][] }[];
  aberturas: { tipo: "puerta" | "ventana"; x: number; y: number; x2: number; y2: number }[];
}

export interface GeometriaPlano {
  zonas: { indice: number; ancho: number; alto: number; muros: Segmento[] }[];
  plantas: PlantaDibujada[];
}

// --- Cronograma desde la estimación ---

export type Oficio =
  | "tierras"
  | "estructura"
  | "albanileria"
  | "pisos"
  | "electricidad"
  | "plomeria"
  | "carpinteria"
  | "techo"
  | "pintura"
  | "limpieza";

export interface Ejecucion {
  fecha_inicio: string;
  dias_semana: 5 | 6 | 7;
  entrega_deseada: string | null;
  cuadrillas: Partial<Record<Oficio, number>>;
  subcontratos: Oficio[];
}

export interface PasoPropuesto {
  clave: string;
  nombre: string;
  fase: string;
  oficio: Oficio;
  cantidad: number | null;
  unidad: string;
  dias_trabajo: number;
  duracion_dias: number;
  personas: number;
  inicio: string;
  fin: string;
  holgura_dias: number;
  critica: boolean;
  predecesoras: { clave: string; desfase_dias: number; origen: "tecnica" | "cuadrilla" }[];
  costo_mano_obra: number;
  costo_materiales: number;
}

export interface OficioPropuesto {
  clave: Oficio;
  nombre: string;
  cuadrillas: number;
  subcontrato: boolean;
  personas_por_cuadrilla: number;
  pasos: number;
  dias_trabajo: number;
  en_ruta_critica: boolean;
}

export interface Propuesta {
  ejecucion: Ejecucion;
  pasos: PasoPropuesto[];
  fases: string[];
  oficios: OficioPropuesto[];
  inicio: string;
  fin: string;
  dias_calendario: number;
  entrega_deseada: string | null;
  dias_de_retraso: number | null;
  costo_mano_obra: number;
  costo_materiales: number;
  costo_total: number;
  sugerencias: { oficio: Oficio; nombre: string; dias_menos: number; costo_extra: number }[];
  actividades_actuales: number;
}

// --- Kit TCM: estimado, clase, base del estimado y línea base ---

export type EstadoEntregable = "no" | "parcial" | "completo";

export interface ParametrosApu {
  cargas_sociales: number;
  iva_mano_obra: number;
  herramientas: number;
  gastos_generales: number;
  utilidad: number;
  impuestos: number;
}

export interface Apu {
  materiales: number;
  mano_obra: number;
  cargas_sociales: number;
  iva_mano_obra: number;
  equipo: number;
  herramientas: number;
  costo_directo: number;
  gastos_generales: number;
  utilidad: number;
  impuestos: number;
  total: number;
}

export interface InsumoEstimado {
  tipo: "material" | "mano_obra" | "equipo";
  descripcion: string;
  unidad: string;
  rendimiento: number | null;
  cantidad: number;
  precio_unitario: number;
  parcial: number;
}

export interface ActividadEstimada {
  id: number;
  codigo: string;
  nombre: string;
  unidad: string;
  computo: number | null;
  fecha_inicio: string;
  fecha_fin: string;
  apu: Apu;
  precio_unitario: number | null;
  insumos: InsumoEstimado[];
}

export interface FaseEstimada {
  id: number;
  nombre: string;
  total: number;
  actividades: ActividadEstimada[];
}

export interface ClaseEstimado {
  clase: number;
  definicion_norma: string;
  uso: string;
  metodologia: string;
  exactitud_baja: number[];
  exactitud_alta: number[];
}

export interface Clasificacion {
  entregables: { clave: string; nombre: string; peso: number; estado: EstadoEntregable }[];
  porcentaje_definicion: number;
  clase: ClaseEstimado;
  minimo: number | null;
  maximo: number | null;
  clases: ClaseEstimado[];
}

export interface BaseEstimado {
  proposito: string;
  alcance: string;
  metodologia: string;
  base_diseno: string;
  base_planificacion: string;
  fuentes_precios: string;
  fecha_precios: string | null;
  supuestos: string;
  exclusiones: string;
  riesgos_oportunidades: string;
  contingencia_porcentaje: number;
  contingencia_nota: string;
  contingencia_monto: number;
}

export interface LineaBaseResumen {
  id: number;
  version: number;
  aprobada_en: string;
  aprobada_por_nombre: string;
  motivo: string;
  bac: number;
  fecha_inicio: string;
  fecha_fin: string;
  clase: number | null;
  vigente: boolean;
}

export interface SemanaPv {
  numero: number;
  inicio: string;
  fin: string;
  pv: number;
  pv_acumulado: number;
  porcentaje_acumulado: number | null;
}

export interface LineaBaseDetalle extends LineaBaseResumen {
  partidas: {
    partida_id: number | null;
    codigo: string;
    nombre: string;
    fase: string;
    fecha_inicio: string | null;
    fecha_fin: string | null;
    presupuesto: number;
  }[];
  semanas: SemanaPv[];
}

export interface EstimadoObra {
  obra: Obra;
  parametros: ParametrosApu;
  fases: FaseEstimada[];
  totales: Apu;
  clasificacion: Clasificacion;
  base: BaseEstimado;
  lineas_base: LineaBaseResumen[];
  vigente: LineaBaseDetalle | null;
  plan_distinto_de_base: boolean;
  riesgos_abiertos: number;
  riesgos_valor_esperado: number;
  riesgos_porcentaje: number | null;
}

export interface ProblemaImportacion {
  hoja: string;
  fila: number | null;
  columna: string;
  mensaje: string;
}

export interface VistaPrevia {
  valida: boolean;
  errores: ProblemaImportacion[];
  advertencias: ProblemaImportacion[];
  resumen: {
    nombre: string;
    fecha_inicio: string | null;
    moneda: string;
    fases: number;
    actividades: number;
    insumos: number;
    total_estimado: number;
    porcentaje_definicion: number;
    clase: number;
  } | null;
}

export interface ObraImportada {
  obra: Obra;
  advertencias: ProblemaImportacion[];
}

// --- Kit TCM: registro de riesgos (AACE 44R-08) ---

export type EstadoRiesgo = "abierto" | "ocurrido" | "cerrado";
export type EstrategiaRiesgo = "evitar" | "mitigar" | "transferir" | "aceptar";

export interface Riesgo {
  id: number;
  numero: number;
  codigo: string;
  descripcion: string;
  causa: string;
  probabilidad: number;
  impacto_costo: number;
  impacto_dias: number;
  responsable: string;
  estrategia: EstrategiaRiesgo;
  respuesta: string;
  estado: EstadoRiesgo;
  valor_esperado: number;
  dias_esperados: number;
  nivel: "bajo" | "medio" | "alto";
}

export interface RegistroRiesgos {
  moneda: string;
  total_estimado: number;
  riesgos: Riesgo[];
  abiertos: number;
  valor_esperado: number;
  dias_esperados: number;
  porcentaje_del_estimado: number | null;
  contingencia_actual_porcentaje: number;
}
