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
  porcentaje_avance: number;
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

export interface Actividad {
  id: number;
  fase_id: number;
  nombre: string;
  duracion_dias: number;
  inicio_manual: string | null;
  fecha_inicio: string;
  fecha_fin: string;
  orden: number;
  predecesoras: number[];
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
export type PasoEstimacion = "capas" | "plantas" | "formulario" | "cantidades" | "confirmada";
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
