import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api, subirArchivo } from "../api";
import { fecha } from "../formato";
import type {
  CapaPlano,
  Estimacion,
  EstimacionResumen,
  FormularioPlano,
  GeometriaPlano,
  Obra,
  PasoEstimacion,
  PlantaPlano,
  RolCapa,
} from "../tipos";
import { Marco } from "../componentes/Marco";
import { PasoCronograma } from "../componentes/PasoCronograma";
import { leerCantidad, TablaCantidades, textoCantidad } from "../componentes/TablaCantidades";
import { LeyendaPlano, VistaPlano } from "../componentes/VistaPlano";
import { IconoAdelante, IconoAlerta, IconoBasura, IconoCheck } from "../componentes/iconos";
import {
  avisar,
  Boton,
  BotonIcono,
  Campo,
  Cargando,
  Entrada,
  EstadoVacio,
  Interruptor,
  MensajeError,
  OpcionGrande,
  Pildora,
  Selector,
  Tarjeta,
} from "../componentes/ui";

const TITULO_PASO: Record<PasoEstimacion, string> = {
  capas: "Capas",
  plantas: "Plantas",
  formulario: "Datos de la obra",
  cantidades: "Cantidades",
  confirmada: "Cronograma",
  generada: "Cronograma",
};

const ROLES: { valor: RolCapa; texto: string }[] = [
  { valor: "muros", texto: "Muros" },
  { valor: "puertas", texto: "Puertas" },
  { valor: "ventanas", texto: "Ventanas" },
  { valor: "ambientes", texto: "Ambientes" },
  { valor: "columnas", texto: "Columnas" },
  { valor: "ignorar", texto: "No usar" },
];

const UNIDADES: { valor: number; texto: string }[] = [
  { valor: 4, texto: "Milímetros" },
  { valor: 5, texto: "Centímetros" },
  { valor: 6, texto: "Metros" },
  { valor: 1, texto: "Pulgadas" },
  { valor: 2, texto: "Pies" },
];

/** Estimar desde plano: subir un DXF (CAD) o IFC (BIM) y confirmar paso a paso lo que se leyó. */
export function EstimarObra() {
  const { obraId } = useParams();
  const [parametros, setParametros] = useSearchParams();
  const id = parametros.get("id");
  const obra = useQuery({ queryKey: ["obra", obraId], queryFn: () => api<Obra>(`/api/obras/${obraId}`) });

  return (
    <Marco titulo={obra.data ? `Estimar · ${obra.data.nombre}` : "Estimar desde plano"} volver={`/obras/${obraId}?vista=cronograma`}>
      {id ? (
        <Asistente id={id} obraId={obraId!} />
      ) : (
        <SubirPlano obraId={obraId!} abrir={(nuevo) => setParametros({ id: String(nuevo) })} />
      )}
    </Marco>
  );
}

// --- Paso 1: subir ---

function SubirPlano({ obraId, abrir }: { obraId: string; abrir: (id: number) => void }) {
  const cliente = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const anteriores = useQuery({
    queryKey: ["estimaciones", obraId],
    queryFn: () => api<EstimacionResumen[]>(`/api/obras/${obraId}/estimaciones`),
  });
  const subir = useMutation({
    mutationFn: (archivo: File) =>
      subirArchivo<Estimacion>(`/api/obras/${obraId}/estimaciones?nombre=${encodeURIComponent(archivo.name)}`, archivo),
    onSuccess: (e) => {
      cliente.setQueryData(["estimacion", String(e.id)], e);
      cliente.invalidateQueries({ queryKey: ["estimaciones", obraId] });
      abrir(e.id);
    },
  });

  function elegir(archivo: File | undefined) {
    if (!archivo) return;
    subir.mutate(archivo);
    if (entrada.current) entrada.current.value = "";
  }

  return (
    <>
      <Tarjeta>
        <h2 className="text-lg font-semibold tracking-tight text-stone-900">Sube el plano de la obra</h2>
        <p className="mt-1 text-stone-600">
          Medimos muros, ambientes, puertas y ventanas para calcular las cantidades de la obra. Tú revisas cada
          paso antes de seguir.
        </p>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div className="rounded-xl border border-stone-200 p-3">
            <dt className="font-semibold text-stone-900">CAD · archivo .dxf</dt>
            <dd className="mt-0.5 text-stone-600">
              AutoCAD, BricsCAD, LibreCAD. Te pediremos algunos datos que el dibujo no trae (altura, tipo de
              muro, losa). Si tienes un .dwg, ábrelo y guárdalo como DXF.
            </dd>
          </div>
          <div className="rounded-xl border border-stone-200 p-3">
            <dt className="font-semibold text-stone-900">BIM · archivo .ifc</dt>
            <dd className="mt-0.5 text-stone-600">
              Revit, ArchiCAD, Allplan. El modelo ya trae alturas y materiales: no hay formulario. Desde Revit,
              exporta a IFC.
            </dd>
          </div>
        </dl>
        <input
          ref={entrada}
          type="file"
          accept=".dxf,.ifc"
          className="hidden"
          onChange={(e) => elegir(e.target.files?.[0])}
        />
        <Boton grande className="mt-4 w-full" disabled={subir.isPending} onClick={() => entrada.current?.click()}>
          {subir.isPending ? "Leyendo el plano…" : "Elegir plano"}
        </Boton>
        <p className="mt-2 text-center text-xs text-stone-500">
          Hasta 25 MB. El plano queda privado: solo se usa para medir y no se comparte.
        </p>
        <div className="mt-3">
          <MensajeError error={subir.error} />
        </div>
      </Tarjeta>

      {anteriores.data && anteriores.data.length > 0 && (
        <Tarjeta className="p-0">
          <h2 className="px-4 pb-1 pt-4 font-semibold text-stone-900">Estimaciones anteriores</h2>
          <ul className="divide-y divide-stone-100">
            {anteriores.data.map((e) => (
              <li key={e.id}>
                <Link
                  to={`?id=${e.id}`}
                  className="flex min-h-14 items-center justify-between gap-3 px-4 py-2 hover:bg-stone-50"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-stone-900">{e.nombre_archivo}</span>
                    <span className="text-sm text-stone-600">
                      {e.tipo_archivo === "dxf" ? "CAD" : "BIM"} · {fecha(e.creado_en)}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    {e.paso === "generada" ? (
                      <Pildora tono="bien">Cronograma creado</Pildora>
                    ) : (
                      <Pildora tono="neutro">En {TITULO_PASO[e.paso].toLowerCase()}</Pildora>
                    )}
                    <IconoAdelante tamano={18} className="text-stone-400" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}
    </>
  );
}

// --- Asistente ---

function useEstimacion(id: string) {
  return useQuery({ queryKey: ["estimacion", id], queryFn: () => api<Estimacion>(`/api/estimaciones/${id}`) });
}

function useGuardar(id: string, ruta: string, alTerminar?: (e: Estimacion) => void) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: unknown) => api<Estimacion>(`/api/estimaciones/${id}/${ruta}`, "PUT", cuerpo),
    onSuccess: (e) => {
      cliente.setQueryData(["estimacion", id], e);
      cliente.invalidateQueries({ queryKey: ["geometria", id] });
      cliente.invalidateQueries({ queryKey: ["estimaciones", String(e.obra_id)] });
      alTerminar?.(e);
    },
  });
}

function Asistente({ id, obraId }: { id: string; obraId: string }) {
  const estimacion = useEstimacion(id);
  const e = estimacion.data;
  // Paso que se está mirando: por defecto el último al que se llegó; se puede volver a uno anterior.
  const [visto, setVisto] = useState<PasoEstimacion | null>(null);
  useEffect(() => setVisto(null), [e?.paso]);

  if (estimacion.isLoading) return <Cargando />;
  if (!e) return <MensajeError error={estimacion.error} reintentar={() => estimacion.refetch()} />;

  // "confirmada" es el paso del cronograma; "generada" quiere decir que ya se creó.
  const pasos = e.pasos.filter((p) => p !== "generada");
  const actual = e.paso === "generada" ? "confirmada" : e.paso;
  const mostrado = visto ?? actual;
  const nombrePaso = (p: PasoEstimacion) => (p === "plantas" && e.tipo_archivo === "ifc" ? "Pisos" : TITULO_PASO[p]);

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-medium text-stone-900">{e.nombre_archivo}</p>
          <p className="text-sm text-stone-600">
            {e.tipo_archivo === "dxf" ? "Plano CAD (DXF)" : "Modelo BIM (IFC): sin formulario"}
          </p>
        </div>
        <BorrarEstimacion id={id} obraId={obraId} />
      </div>

      <ol className="flex gap-1.5" aria-label="Pasos">
        {pasos.map((p, i) => {
          const alcanzado = pasos.indexOf(actual) >= i;
          const hecho = pasos.indexOf(actual) > i || e.paso === "generada";
          return (
            <li key={p} className="min-w-0 flex-1">
              <button
                type="button"
                disabled={!alcanzado}
                onClick={() => setVisto(p)}
                aria-current={mostrado === p ? "step" : undefined}
                className="block w-full text-left disabled:cursor-default"
              >
                <span
                  className={`block h-1.5 rounded-full ${
                    mostrado === p ? "bg-marca-600" : hecho ? "bg-stone-700" : alcanzado ? "bg-stone-400" : "bg-stone-200"
                  }`}
                />
                <span
                  className={`mt-1.5 flex items-center gap-1 truncate text-xs font-medium ${
                    mostrado === p ? "text-stone-900" : "text-stone-600"
                  }`}
                >
                  {hecho && <IconoCheck tamano={14} className="text-emerald-700" />}
                  {i + 1}. {nombrePaso(p)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      {e.avisos.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <p className="flex items-center gap-2 font-semibold">
            <IconoAlerta tamano={18} /> Revisa esto
          </p>
          <ul className="mt-1.5 list-disc space-y-1 pl-5">
            {e.avisos.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {mostrado === "capas" && <PasoCapas e={e} />}
      {mostrado === "plantas" && <PasoPlantas e={e} />}
      {mostrado === "formulario" && <PasoFormulario e={e} />}
      {mostrado === "cantidades" && <PasoCantidades e={e} irAlCronograma={() => setVisto("confirmada")} />}
      {mostrado === "confirmada" && <PasoCronograma e={e} obraId={obraId} />}
    </>
  );
}

function BorrarEstimacion({ id, obraId }: { id: string; obraId: string }) {
  const cliente = useQueryClient();
  const [, setParametros] = useSearchParams();
  const [seguro, setSeguro] = useState(false);
  const borrar = useMutation({
    mutationFn: () => api(`/api/estimaciones/${id}`, "DELETE"),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["estimaciones", obraId] });
      avisar("Estimación borrada");
      setParametros({});
    },
  });
  if (seguro) {
    return (
      <div className="flex shrink-0 gap-2">
        <Boton variante="fantasma" onClick={() => setSeguro(false)}>
          No
        </Boton>
        <Boton variante="peligro" disabled={borrar.isPending} onClick={() => borrar.mutate()}>
          Borrar
        </Boton>
      </div>
    );
  }
  return (
    <BotonIcono titulo="Borrar esta estimación y su plano" onClick={() => setSeguro(true)}>
      <IconoBasura />
    </BotonIcono>
  );
}

function PieDePaso({ children, error }: { children: ReactNode; error?: unknown }) {
  return (
    <div className="space-y-3">
      <MensajeError error={error} />
      {children}
    </div>
  );
}

// --- Paso: capas (solo CAD) ---

function PasoCapas({ e }: { e: Estimacion }) {
  const [roles, setRoles] = useState<Record<string, RolCapa>>(() =>
    Object.fromEntries(e.capas.map((c) => [c.nombre, c.rol])),
  );
  const [unidades, setUnidades] = useState(e.unidades ?? 6);
  const guardar = useGuardar(String(e.id), "capas");
  const hayMuros = Object.values(roles).includes("muros");
  const ordenadas = [...e.capas].sort((a, b) => Number(roles[b.nombre] !== "ignorar") - Number(roles[a.nombre] !== "ignorar"));

  return (
    <>
      <Tarjeta>
        <h2 className="font-semibold text-stone-900">¿En qué unidades está dibujado?</h2>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Selector value={unidades} onChange={(ev) => setUnidades(Number(ev.target.value))} className="max-w-48">
            {UNIDADES.map((u) => (
              <option key={u.valor} value={u.valor}>
                {u.texto}
              </option>
            ))}
          </Selector>
          {e.unidades_deducidas ? (
            <Pildora tono="atencion">Deducido por el tamaño del dibujo</Pildora>
          ) : (
            <Pildora tono="bien">Lo dice el archivo</Pildora>
          )}
        </div>
      </Tarjeta>

      <Tarjeta className="p-0">
        <div className="px-4 pb-2 pt-4">
          <h2 className="font-semibold text-stone-900">¿Qué hay en cada capa?</h2>
          <p className="mt-0.5 text-sm text-stone-600">
            Lo sugerimos por el nombre de la capa. Corrige lo que no esté bien: la próxima vez lo recordamos.
          </p>
        </div>
        <ul className="divide-y divide-stone-100">
          {ordenadas.map((c) => (
            <FilaCapa key={c.nombre} capa={c} rol={roles[c.nombre]} cambiar={(r) => setRoles({ ...roles, [c.nombre]: r })} />
          ))}
        </ul>
      </Tarjeta>

      <PieDePaso error={guardar.error}>
        {!hayMuros && <p className="text-sm text-amber-800">Marca al menos una capa como muros para poder medir.</p>}
        <Boton grande className="w-full" disabled={!hayMuros || guardar.isPending} onClick={() => guardar.mutate({ capas: roles, unidades })}>
          {guardar.isPending ? "Buscando plantas…" : "Confirmar capas"}
        </Boton>
      </PieDePaso>
    </>
  );
}

function FilaCapa({ capa, rol, cambiar }: { capa: CapaPlano; rol: RolCapa; cambiar: (r: RolCapa) => void }) {
  const conteo = [
    capa.lineas && `${capa.lineas} líneas`,
    capa.bloques && `${capa.bloques} bloques`,
    capa.arcos && `${capa.arcos} arcos`,
    capa.textos && `${capa.textos} textos`,
  ].filter(Boolean);
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3">
      <div className="min-w-0 flex-1 basis-40">
        <p className="truncate font-mono text-sm font-medium text-stone-900">{capa.nombre}</p>
        <p className="text-xs tabular-nums text-stone-600">
          {conteo.join(" · ")}
          {capa.recordada && " · como la última vez"}
        </p>
      </div>
      <Selector
        value={rol}
        onChange={(ev) => cambiar(ev.target.value as RolCapa)}
        aria-label={`Contenido de la capa ${capa.nombre}`}
        className={`w-40 ${rol === "ignorar" ? "text-stone-500" : "font-medium"}`}
      >
        {ROLES.map((r) => (
          <option key={r.valor} value={r.valor}>
            {r.texto}
          </option>
        ))}
      </Selector>
    </li>
  );
}

// --- Paso: plantas o pisos ---

function useGeometria(e: Estimacion) {
  return useQuery({
    queryKey: ["geometria", String(e.id)],
    queryFn: () => api<GeometriaPlano>(`/api/estimaciones/${e.id}/geometria`),
    enabled: e.tipo_archivo === "dxf",
    staleTime: Infinity,
  });
}

function PasoPlantas({ e }: { e: Estimacion }) {
  const [plantas, setPlantas] = useState<PlantaPlano[]>(e.plantas);
  const geometria = useGeometria(e);
  const guardar = useGuardar(String(e.id), "plantas");
  const esCad = e.tipo_archivo === "dxf";
  const cambiar = (indice: number, cambio: Partial<PlantaPlano>) =>
    setPlantas(plantas.map((p) => (p.indice === indice ? { ...p, ...cambio } : p)));
  const incluidas = plantas.filter((p) => p.incluir);
  const nombres = incluidas.map((p) => p.nombre.trim().toLowerCase());
  const problema =
    incluidas.length === 0
      ? "Elige al menos una planta."
      : nombres.some((n) => !n) || new Set(nombres).size !== nombres.length
        ? "Cada planta necesita un nombre distinto."
        : null;

  return (
    <>
      <p className="text-stone-700">
        {esCad
          ? "Encontramos estas zonas dibujadas. Marca cuáles son plantas de la obra y ponles nombre, de abajo hacia arriba."
          : "Estos son los pisos del modelo. Desmarca los que no se construyen (terreno, niveles de referencia)."}
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {plantas.map((p) => {
          const zona = geometria.data?.zonas[p.indice];
          return (
            <Tarjeta key={p.indice} className={p.incluir ? "" : "opacity-70"}>
              {esCad &&
                (zona ? (
                  <VistaPlano ancho={zona.ancho} alto={zona.alto} muros={zona.muros} className="mb-3 max-h-56" />
                ) : (
                  <div className="mb-3 h-40 animate-pulse rounded-xl bg-stone-100" />
                ))}
              <p className="mb-3 text-sm tabular-nums text-stone-600">
                {p.ancho !== null && p.alto !== null
                  ? `${textoCantidad(p.ancho)} × ${textoCantidad(p.alto)} m · ${p.detalle}`
                  : p.detalle}
              </p>
              <div className="space-y-3">
                <Interruptor etiqueta="Es una planta de la obra" activo={p.incluir} cambiar={(v) => cambiar(p.indice, { incluir: v })} />
                {p.incluir && (
                  <div className="grid grid-cols-[1fr_6rem] gap-3">
                    <Campo etiqueta="Nombre">
                      <Entrada value={p.nombre} maxLength={60} onChange={(ev) => cambiar(p.indice, { nombre: ev.target.value })} />
                    </Campo>
                    <Campo etiqueta="Se repite">
                      <Entrada
                        type="number"
                        min={1}
                        max={60}
                        inputMode="numeric"
                        value={p.repeticiones}
                        onChange={(ev) => cambiar(p.indice, { repeticiones: Math.max(1, Math.min(60, Number(ev.target.value) || 1)) })}
                        className="text-right tabular-nums"
                      />
                    </Campo>
                  </div>
                )}
              </div>
            </Tarjeta>
          );
        })}
      </div>
      <PieDePaso error={guardar.error}>
        {problema && <p className="text-sm text-amber-800">{problema}</p>}
        <p className="text-xs text-stone-500">"Se repite" sirve para una planta tipo de departamentos que se construye varias veces.</p>
        <Boton grande className="w-full" disabled={!!problema || guardar.isPending} onClick={() => guardar.mutate(plantas)}>
          {guardar.isPending ? "Midiendo…" : esCad ? "Medir plantas" : "Calcular cantidades"}
        </Boton>
      </PieDePaso>
    </>
  );
}

// --- Paso: formulario (solo CAD) ---

type Opciones<K extends keyof FormularioPlano> = { valor: FormularioPlano[K]; texto: string }[];

const TIPO_OBRA: Opciones<"tipo_obra"> = [
  { valor: "vivienda", texto: "Vivienda" },
  { valor: "departamentos", texto: "Departamentos" },
  { valor: "comercial", texto: "Comercial" },
];
const TIPO_MURO: Opciones<"tipo_muro"> = [
  { valor: "ladrillo_6h", texto: "Ladrillo 6 huecos" },
  { valor: "bloque_cemento", texto: "Bloque de cemento" },
  { valor: "adobe", texto: "Adobe" },
];
const LOSA: Opciones<"losa"> = [
  { valor: "alivianada", texto: "Alivianada" },
  { valor: "maciza", texto: "Maciza" },
  { valor: "viguetas", texto: "Viguetas" },
];
const CUBIERTA: Opciones<"cubierta"> = [
  { valor: "losa", texto: "Losa" },
  { valor: "calamina", texto: "Calamina" },
  { valor: "teja", texto: "Teja" },
];
const FUNDACION: Opciones<"fundacion"> = [
  { valor: "zapatas", texto: "Zapatas" },
  { valor: "cimiento_corrido", texto: "Cimiento corrido" },
];
const ACABADO: Opciones<"acabado"> = [
  { valor: "economico", texto: "Económico" },
  { valor: "medio", texto: "Medio" },
  { valor: "alto", texto: "Alto" },
];
const PISO: Opciones<"piso"> = [
  { valor: "ceramica", texto: "Cerámica" },
  { valor: "porcelanato", texto: "Porcelanato" },
  { valor: "cemento", texto: "Cemento pulido" },
];

function Eleccion<K extends keyof FormularioPlano>({
  etiqueta,
  opciones,
  valor,
  cambiar,
}: {
  etiqueta: string;
  opciones: Opciones<K>;
  valor: FormularioPlano[K];
  cambiar: (v: FormularioPlano[K]) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium text-stone-800">{etiqueta}</legend>
      <div className={`grid gap-2 ${opciones.length === 2 ? "grid-cols-2" : "grid-cols-3"}`}>
        {opciones.map((o) => (
          <OpcionGrande key={String(o.valor)} activo={valor === o.valor} onClick={() => cambiar(o.valor)}>
            {o.texto}
          </OpcionGrande>
        ))}
      </div>
    </fieldset>
  );
}

/** Número con coma decimal; vacío = null. Guarda el texto para no pelear con lo que se está escribiendo. */
function CampoNumero({
  etiqueta,
  valor,
  cambiar,
  unidad,
  ayuda,
  placeholder,
}: {
  etiqueta: string;
  valor: string;
  cambiar: (v: string) => void;
  unidad: string;
  ayuda?: string;
  placeholder?: string;
}) {
  return (
    <Campo etiqueta={etiqueta} ayuda={ayuda}>
      <div className="flex items-center gap-2">
        <Entrada
          inputMode="decimal"
          value={valor}
          placeholder={placeholder}
          onChange={(ev) => cambiar(ev.target.value)}
          className="text-right tabular-nums"
        />
        <span className="w-8 shrink-0 text-sm text-stone-600">{unidad}</span>
      </div>
    </Campo>
  );
}

const coma = (v: number | null) => (v === null ? "" : String(v).replace(".", ","));

function PasoFormulario({ e }: { e: Estimacion }) {
  const inicial = e.formulario!;
  const [f, setF] = useState<FormularioPlano>(inicial);
  const [textos, setTextos] = useState({
    altura: coma(inicial.altura_piso),
    exterior: coma(Math.round(inicial.espesor_exterior * 100)),
    interior: coma(Math.round(inicial.espesor_interior * 100)),
    banos: coma(inicial.banos),
    cocinas: coma(inicial.cocinas),
  });
  const guardar = useGuardar(String(e.id), "formulario");
  const banosPlano = e.pisos_medidos.reduce((s, p) => s + p.banos * p.repeticiones, 0);
  const cocinasPlano = e.pisos_medidos.reduce((s, p) => s + p.cocinas * p.repeticiones, 0);
  const poner = <K extends keyof FormularioPlano>(campo: K) => (v: FormularioPlano[K]) => setF({ ...f, [campo]: v });

  const altura = leerCantidad(textos.altura);
  const exterior = leerCantidad(textos.exterior);
  const interior = leerCantidad(textos.interior);
  const conteo = (t: string) => (t.trim() === "" ? null : Math.round(leerCantidad(t) ?? -1));
  const banos = conteo(textos.banos);
  const cocinas = conteo(textos.cocinas);
  const problema =
    altura === null || altura < 2 || altura > 6
      ? "La altura de piso a techo va entre 2 y 6 m."
      : exterior === null || exterior < 8 || exterior > 60 || interior === null || interior < 5 || interior > 40
        ? "Revisa los espesores de muro (en centímetros)."
        : (banos !== null && banos < 0) || (cocinas !== null && cocinas < 0)
          ? "Revisa la cantidad de baños y cocinas."
          : null;

  function enviar() {
    guardar.mutate({
      ...f,
      altura_piso: altura,
      espesor_exterior: exterior! / 100,
      espesor_interior: interior! / 100,
      banos,
      cocinas,
    });
  }

  return (
    <>
      <ResumenMedido e={e} />
      <Tarjeta>
        <h2 className="font-semibold text-stone-900">Lo que el plano no dice</h2>
        <p className="mt-0.5 text-sm text-stone-600">Ya viene con lo más común en Bolivia. Cambia solo lo que sea distinto.</p>
        <div className="mt-4 space-y-5">
          <Eleccion etiqueta="Tipo de obra" opciones={TIPO_OBRA} valor={f.tipo_obra} cambiar={poner("tipo_obra")} />
          <div className="grid grid-cols-3 gap-3">
            <CampoNumero etiqueta="Altura de piso" unidad="m" valor={textos.altura} cambiar={(v) => setTextos({ ...textos, altura: v })} />
            <CampoNumero etiqueta="Muro exterior" unidad="cm" valor={textos.exterior} cambiar={(v) => setTextos({ ...textos, exterior: v })} />
            <CampoNumero etiqueta="Muro interior" unidad="cm" valor={textos.interior} cambiar={(v) => setTextos({ ...textos, interior: v })} />
          </div>
          <Eleccion etiqueta="Muros de" opciones={TIPO_MURO} valor={f.tipo_muro} cambiar={poner("tipo_muro")} />
          <Eleccion etiqueta="Losa" opciones={LOSA} valor={f.losa} cambiar={poner("losa")} />
          <Eleccion etiqueta="Techo" opciones={CUBIERTA} valor={f.cubierta} cambiar={poner("cubierta")} />
          <Eleccion etiqueta="Fundación" opciones={FUNDACION} valor={f.fundacion} cambiar={poner("fundacion")} />
          <Eleccion etiqueta="Piso" opciones={PISO} valor={f.piso} cambiar={poner("piso")} />
          <Eleccion etiqueta="Acabados" opciones={ACABADO} valor={f.acabado} cambiar={poner("acabado")} />
          <div className="grid grid-cols-2 gap-3">
            <CampoNumero
              etiqueta="Baños"
              unidad=""
              placeholder={String(banosPlano)}
              ayuda={`En el plano: ${banosPlano}. Déjalo vacío si está bien.`}
              valor={textos.banos}
              cambiar={(v) => setTextos({ ...textos, banos: v })}
            />
            <CampoNumero
              etiqueta="Cocinas"
              unidad=""
              placeholder={String(cocinasPlano)}
              ayuda={`En el plano: ${cocinasPlano}. Déjalo vacío si está bien.`}
              valor={textos.cocinas}
              cambiar={(v) => setTextos({ ...textos, cocinas: v })}
            />
          </div>
        </div>
      </Tarjeta>
      <PieDePaso error={guardar.error}>
        {problema && <p className="text-sm text-amber-800">{problema}</p>}
        <Boton grande className="w-full" disabled={!!problema || guardar.isPending} onClick={enviar}>
          {guardar.isPending ? "Calculando…" : "Calcular cantidades"}
        </Boton>
      </PieDePaso>
    </>
  );
}

function ResumenMedido({ e }: { e: Estimacion }) {
  if (e.pisos_medidos.length === 0) return null;
  return (
    <Tarjeta className="p-0">
      <h2 className="px-4 pb-1 pt-4 font-semibold text-stone-900">Lo que medimos</h2>
      <ul className="divide-y divide-stone-100">
        {e.pisos_medidos.map((p) => (
          <li key={p.nombre} className="px-4 py-3">
            <p className="font-medium text-stone-900">
              {p.nombre}
              {p.repeticiones > 1 && <span className="font-normal text-stone-600"> · se repite {p.repeticiones} veces</span>}
            </p>
            <dl className="mt-1 grid grid-cols-3 gap-2 text-sm sm:grid-cols-6">
              <Medida titulo="Planta" valor={`${textoCantidad(p.area_planta)} m²`} />
              <Medida titulo="Muros" valor={`${textoCantidad(p.largo_muros)} m`} />
              <Medida titulo="Fachada" valor={`${textoCantidad(p.perimetro_exterior)} m`} />
              <Medida titulo="Ambientes" valor={String(p.ambientes)} />
              <Medida titulo="Puertas" valor={String(p.puertas)} />
              <Medida titulo="Ventanas" valor={String(p.ventanas)} />
            </dl>
          </li>
        ))}
      </ul>
    </Tarjeta>
  );
}

function Medida({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div>
      <dt className="text-stone-600">{titulo}</dt>
      <dd className="font-semibold tabular-nums text-stone-900">{valor}</dd>
    </div>
  );
}

// --- Paso: cantidades ---

function valoresIniciales(e: Estimacion): Record<string, string> {
  return Object.fromEntries(
    e.cantidades.filter((c) => c.origen === "editada").map((c) => [c.clave, textoCantidad(c.cantidad)]),
  );
}

function PasoCantidades({ e, irAlCronograma }: { e: Estimacion; irAlCronograma: () => void }) {
  const [valores, setValores] = useState<Record<string, string>>(() => valoresIniciales(e));
  const geometria = useGeometria(e);
  const confirmada = e.paso === "confirmada" || e.paso === "generada";
  const guardar = useGuardar(String(e.id), "cantidades", (nueva) => {
    setValores(valoresIniciales(nueva));
    avisar(nueva.paso === "cantidades" ? "Cambios guardados" : "Cantidades confirmadas");
  });

  const calculada = (clave: string) => {
    const c = e.cantidades.find((x) => x.clave === clave)!;
    return c.cantidad_original ?? c.cantidad;
  };
  const ediciones: Record<string, number> = {};
  let invalidas = 0;
  for (const [clave, texto] of Object.entries(valores)) {
    const valor = leerCantidad(texto);
    if (valor === null) invalidas++;
    else if (valor !== calculada(clave)) ediciones[clave] = valor;
  }
  const guardadas = Object.fromEntries(
    e.cantidades.filter((c) => c.origen === "editada").map((c) => [c.clave, c.cantidad]),
  );
  const hayCambios = JSON.stringify(ediciones, Object.keys(ediciones).sort()) !== JSON.stringify(guardadas, Object.keys(guardadas).sort());
  const tipicas = e.cantidades.filter((c) => (c.origen_original ?? c.origen) === "proporcion").length;

  function cambiar(clave: string, valor: string | null) {
    const nuevos = { ...valores };
    if (valor === null) delete nuevos[clave];
    else nuevos[clave] = valor;
    setValores(nuevos);
  }

  return (
    <>
      <ResumenMedido e={e} />
      {geometria.data && geometria.data.plantas.length > 0 && (
        <Tarjeta>
          <h2 className="mb-3 font-semibold text-stone-900">Así leímos el plano</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {geometria.data.plantas.map((p) => (
              <figure key={p.nombre}>
                <VistaPlano ancho={p.ancho} alto={p.alto} muros={p.muros} planta={p} />
                <figcaption className="mt-1.5 text-sm font-medium text-stone-800">{p.nombre}</figcaption>
              </figure>
            ))}
          </div>
          <div className="mt-3">
            <LeyendaPlano />
          </div>
        </Tarjeta>
      )}

      {e.tipo_archivo === "ifc" && e.datos_del_modelo.length > 0 && (
        <p className="text-sm text-stone-600">
          Altura, espesores y materiales salieron del modelo. Lo que el modelo no trae se completó con valores típicos.
        </p>
      )}

      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight text-stone-900">Cantidades de obra</h2>
        {tipicas > 0 && (
          <p className="text-sm text-stone-600">
            {tipicas} {tipicas === 1 ? "es un valor típico" : "son valores típicos"}: revísalos con tu experiencia.
          </p>
        )}
      </div>
      {e.cantidades.length === 0 ? (
        <Tarjeta>
          <EstadoVacio texto="No salió ninguna cantidad. Revisa las capas de muros y las plantas elegidas." />
        </Tarjeta>
      ) : (
        <TablaCantidades cantidades={e.cantidades} valores={valores} cambiar={cambiar} />
      )}

      <PieDePaso error={guardar.error}>
        {invalidas > 0 && <p className="text-sm text-amber-800">Hay cantidades que no son un número válido.</p>}
        {confirmada && !hayCambios ? (
          <Tarjeta className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex min-w-0 flex-1 basis-60 items-start gap-3">
              <IconoCheck className="mt-0.5 shrink-0 text-emerald-700" />
              <div>
                <p className="font-semibold text-stone-900">Cantidades confirmadas</p>
                <p className="text-sm text-stone-600">Puedes seguir corrigiéndolas cuando quieras.</p>
              </div>
            </div>
            <Boton onClick={irAlCronograma}>Armar el cronograma</Boton>
          </Tarjeta>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            <Boton
              variante="secundario"
              disabled={!hayCambios || invalidas > 0 || guardar.isPending}
              onClick={() => guardar.mutate({ ediciones, confirmar: false })}
            >
              Guardar cambios
            </Boton>
            <Boton disabled={invalidas > 0 || guardar.isPending} onClick={() => guardar.mutate({ ediciones, confirmar: true })}>
              {guardar.isPending ? "Guardando…" : "Confirmar cantidades"}
            </Boton>
          </div>
        )}
      </PieDePaso>
    </>
  );
}
