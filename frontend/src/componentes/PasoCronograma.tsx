import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { bs, fecha } from "../formato";
import type { Cronograma, Ejecucion, Estimacion, Oficio, OficioPropuesto, Propuesta } from "../tipos";
import { Gantt } from "./Gantt";
import { IconoAlerta } from "./iconos";
import { avisar, Boton, Campo, Cargando, Entrada, MensajeError, Metrica, OpcionGrande, Pildora, Tarjeta } from "./ui";

const DIAS_SEMANA: { valor: Ejecucion["dias_semana"]; texto: string }[] = [
  { valor: 5, texto: "Lunes a viernes" },
  { valor: 6, texto: "Lunes a sábado" },
  { valor: 7, texto: "Todos los días" },
];

/** La propuesta con la forma que espera el Gantt (ids inventados: todavía no existe en la base). */
function comoCronograma(p: Propuesta): Pick<Cronograma, "fases" | "hoy" | "fecha_inicio" | "fecha_fin"> {
  const ids = new Map(p.pasos.map((paso, i) => [paso.clave, i + 1]));
  return {
    hoy: p.inicio,
    fecha_inicio: p.inicio,
    fecha_fin: p.fin,
    fases: p.fases.map((nombre, i) => ({
      id: i + 1,
      nombre,
      orden: i,
      costo_total: 0,
      actividades: p.pasos
        .filter((paso) => paso.fase === nombre)
        .map((paso) => ({
          id: ids.get(paso.clave)!,
          fase_id: i + 1,
          nombre: paso.nombre,
          duracion_dias: paso.duracion_dias,
          inicio_manual: null,
          fecha_inicio: paso.inicio,
          fecha_fin: paso.fin,
          orden: ids.get(paso.clave)!,
          predecesoras: paso.predecesoras.map((e) => ids.get(e.clave)!),
          holgura_dias: paso.holgura_dias,
          critica: paso.critica,
          recursos: [],
          costo_mano_obra: paso.costo_mano_obra,
          costo_materiales: paso.costo_materiales,
          costo_total: paso.costo_mano_obra + paso.costo_materiales,
        })),
    })),
  };
}

function dias(n: number): string {
  return `${n} ${n === 1 ? "día" : "días"}`;
}

/** Último paso del asistente: cómo se ejecuta la obra, vista previa con ruta crítica y crear el cronograma. */
export function PasoCronograma({ e, obraId }: { e: Estimacion; obraId: string }) {
  const id = String(e.id);
  const cliente = useQueryClient();
  const navegar = useNavigate();
  const [ejecucion, setEjecucion] = useState<Ejecucion | null>(null);
  const [modo, setModo] = useState<"reemplazar" | "agregar">("agregar");
  const [seguro, setSeguro] = useState(false);

  const propuesta = useQuery({
    queryKey: ["propuesta", id, ejecucion],
    queryFn: () =>
      ejecucion
        ? api<Propuesta>(`/api/estimaciones/${id}/propuesta`, "POST", ejecucion)
        : api<Propuesta>(`/api/estimaciones/${id}/propuesta`),
    placeholderData: keepPreviousData,
    retry: false,
  });

  // La primera respuesta trae la ejecución guardada (o la típica): desde ahí se edita.
  useEffect(() => {
    if (!ejecucion && propuesta.data) {
      cliente.setQueryData(["propuesta", id, propuesta.data.ejecucion], propuesta.data);
      setEjecucion(propuesta.data.ejecucion);
    }
  }, [ejecucion, propuesta.data, cliente, id]);

  const generar = useMutation({
    mutationFn: () => api<Estimacion>(`/api/estimaciones/${id}/generar`, "POST", { ...ejecucion, modo: modoFinal }),
    onSuccess: (nueva) => {
      cliente.setQueryData(["estimacion", id], nueva);
      // Cambian el cronograma, el fin de la obra y sus indicadores.
      cliente.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "estimacion" });
      avisar("Cronograma creado");
      navegar(`/obras/${obraId}?vista=cronograma`);
    },
  });

  const p = propuesta.data;
  if (!p || !ejecucion) {
    return propuesta.error ? <MensajeError error={propuesta.error} reintentar={() => propuesta.refetch()} /> : <Cargando />;
  }

  const hayActual = p.actividades_actuales > 0;
  const modoFinal = hayActual ? modo : "reemplazar";
  const cambiar = (cambio: Partial<Ejecucion>) => {
    setSeguro(false);
    setEjecucion({ ...ejecucion, ...cambio });
  };
  const cuadrillas = (o: Oficio) => ejecucion.cuadrillas[o] ?? 1;
  const ponerCuadrillas = (o: Oficio, n: number) =>
    cambiar({ cuadrillas: { ...ejecucion.cuadrillas, [o]: Math.min(10, Math.max(1, n)) } });
  const subcontratar = (o: Oficio, si: boolean) =>
    cambiar({ subcontratos: si ? [...ejecucion.subcontratos, o] : ejecucion.subcontratos.filter((x) => x !== o) });
  const mejor = p.sugerencias[0];
  const pasosPorClave = new Map(p.pasos.map((paso) => [paso.clave, paso]));
  const actualizando = propuesta.isFetching;

  return (
    <>
      {e.paso === "generada" && (
        <p className="text-sm text-stone-600">
          Ya creaste el cronograma con esta estimación. Si cambias algo, puedes volver a crearlo.
        </p>
      )}

      <Tarjeta>
        <h2 className="font-semibold text-stone-900">¿Cómo se va a trabajar?</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <Campo etiqueta="Empieza el">
            <Entrada
              type="date"
              value={ejecucion.fecha_inicio}
              onChange={(ev) => ev.target.value && cambiar({ fecha_inicio: ev.target.value })}
            />
          </Campo>
          <Campo etiqueta="Entrega que quieres" ayuda="Opcional: para saber si llegas.">
            <Entrada
              type="date"
              value={ejecucion.entrega_deseada ?? ""}
              onChange={(ev) => cambiar({ entrega_deseada: ev.target.value || null })}
            />
          </Campo>
        </div>
        <fieldset className="mt-4">
          <legend className="mb-1.5 text-sm font-medium text-stone-800">Días de trabajo</legend>
          <div className="grid grid-cols-3 gap-2">
            {DIAS_SEMANA.map((d) => (
              <OpcionGrande key={d.valor} activo={ejecucion.dias_semana === d.valor} onClick={() => cambiar({ dias_semana: d.valor })}>
                {d.texto}
              </OpcionGrande>
            ))}
          </div>
        </fieldset>
      </Tarjeta>

      <MensajeError error={propuesta.error} />

      <Tarjeta className={actualizando ? "opacity-70 transition" : "transition"}>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <div className="col-span-2 sm:col-span-1">
            <Metrica etiqueta="Entrega estimada" valor={fecha(p.fin)} grande detalle={`${p.dias_calendario} días desde el inicio`} />
            {p.dias_de_retraso !== null && (
              <div className="mt-2">
                {p.dias_de_retraso > 0 ? (
                  <Pildora tono="atencion">{dias(p.dias_de_retraso)} después de lo que quieres</Pildora>
                ) : (
                  <Pildora tono="bien">
                    {p.dias_de_retraso === 0 ? "Justo a tiempo" : `${dias(-p.dias_de_retraso)} antes de lo que quieres`}
                  </Pildora>
                )}
              </div>
            )}
          </div>
          <Metrica etiqueta="Mano de obra" valor={bs(p.costo_mano_obra)} detalle="Jornales de referencia" />
          <Metrica etiqueta="Materiales" valor={bs(p.costo_materiales)} detalle="Precios de referencia" />
        </div>
        <p className="mt-3 text-xs text-stone-500">
          Rendimientos, jornales y precios son valores típicos para empezar: corrígelos en el cronograma.
        </p>
      </Tarjeta>

      {mejor && (
        <Tarjeta className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1 basis-64">
            <p className="font-semibold text-stone-900">
              Con 1 cuadrilla más de {mejor.nombre.toLowerCase()} terminas {dias(mejor.dias_menos)} antes
            </p>
            <p className="text-sm text-stone-600">
              {mejor.costo_extra > 0
                ? `Cuesta ${bs(mejor.costo_extra)} más en jornales.`
                : "Los jornales son casi los mismos: se trabaja más gente menos días."}
            </p>
          </div>
          <Boton variante="secundario" onClick={() => ponerCuadrillas(mejor.oficio, cuadrillas(mejor.oficio) + 1)}>
            Sumar esa cuadrilla
          </Boton>
        </Tarjeta>
      )}

      <Tarjeta className="p-0">
        <div className="px-4 pb-1 pt-4">
          <h2 className="font-semibold text-stone-900">Cuadrillas por oficio</h2>
          <p className="mt-0.5 text-sm text-stone-600">
            Una cuadrilla no hace dos trabajos a la vez: si se cruzan, uno espera. Lo subcontratado no espera.
          </p>
        </div>
        <ul className="divide-y divide-stone-100">
          {p.oficios
            .filter((o) => o.clave !== "limpieza")
            .map((o) => (
              <FilaOficio
                key={o.clave}
                oficio={o}
                cuadrillas={cuadrillas(o.clave)}
                subcontrato={ejecucion.subcontratos.includes(o.clave)}
                cambiarCuadrillas={(n) => ponerCuadrillas(o.clave, n)}
                cambiarSubcontrato={(si) => subcontratar(o.clave, si)}
              />
            ))}
        </ul>
      </Tarjeta>

      <Tarjeta>
        <h2 className="mb-3 font-semibold text-stone-900">Pasos del proyecto y ruta crítica</h2>
        <Gantt cronograma={comoCronograma(p)} vistaPrevia />
        <details className="mt-3">
          <summary className="flex min-h-10 cursor-pointer items-center text-sm font-medium text-stone-700">
            Ver cada paso con su gente y de qué depende
          </summary>
          <ol className="mt-2 divide-y divide-stone-100 text-sm">
            {p.pasos.map((paso) => (
              <li key={paso.clave} className="py-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`font-medium ${paso.critica ? "text-red-800" : "text-stone-900"}`}>{paso.nombre}</span>
                  <span className="tabular-nums text-stone-600">
                    {fecha(paso.inicio)} – {fecha(paso.fin)}
                  </span>
                </div>
                <p className="mt-0.5 text-stone-600">
                  {paso.personas} personas · {dias(paso.dias_trabajo)} de trabajo
                  {paso.critica ? " · ruta crítica" : ` · puede atrasarse ${dias(paso.holgura_dias)}`}
                </p>
                {paso.predecesoras.length > 0 && (
                  <p className="mt-0.5 text-stone-500">
                    Después de:{" "}
                    {paso.predecesoras
                      .map((x) => {
                        const nombre = pasosPorClave.get(x.clave)?.nombre ?? x.clave;
                        const extra = [
                          x.desfase_dias > 0 && `+${x.desfase_dias} días de fraguado`,
                          x.origen === "cuadrilla" && "misma cuadrilla",
                        ].filter(Boolean);
                        return extra.length ? `${nombre} (${extra.join(", ")})` : nombre;
                      })
                      .join(" · ")}
                  </p>
                )}
              </li>
            ))}
          </ol>
        </details>
      </Tarjeta>

      <div className="space-y-3">
        {hayActual && (
          <fieldset>
            <legend className="mb-1.5 text-sm font-medium text-stone-800">
              La obra ya tiene {p.actividades_actuales} {p.actividades_actuales === 1 ? "actividad" : "actividades"}
            </legend>
            <div className="grid grid-cols-2 gap-2">
              <OpcionGrande activo={modo === "agregar"} onClick={() => { setModo("agregar"); setSeguro(false); }}>
                Agregar al cronograma
              </OpcionGrande>
              <OpcionGrande activo={modo === "reemplazar"} onClick={() => { setModo("reemplazar"); setSeguro(false); }}>
                Reemplazar el cronograma
              </OpcionGrande>
            </div>
          </fieldset>
        )}
        <MensajeError error={generar.error} />
        {modoFinal === "reemplazar" && hayActual && seguro ? (
          <div className="rounded-2xl border border-red-200 bg-red-50 p-4">
            <p className="flex items-center gap-2 font-semibold text-red-800">
              <IconoAlerta tamano={18} /> Se borran las {p.actividades_actuales} actividades actuales
            </p>
            <p className="mt-1 text-sm text-red-800">Con su mano de obra y materiales. No se puede deshacer.</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              <Boton variante="secundario" onClick={() => setSeguro(false)}>
                No, volver
              </Boton>
              <Boton variante="peligro" disabled={generar.isPending} onClick={() => generar.mutate()}>
                {generar.isPending ? "Creando…" : "Sí, reemplazar"}
              </Boton>
            </div>
          </div>
        ) : (
          <Boton
            grande
            className="w-full"
            disabled={generar.isPending || actualizando || !!propuesta.error}
            onClick={() => (modoFinal === "reemplazar" && hayActual ? setSeguro(true) : generar.mutate())}
          >
            {generar.isPending ? "Creando…" : `Crear cronograma (${p.pasos.length} pasos)`}
          </Boton>
        )}
      </div>
    </>
  );
}

function FilaOficio({
  oficio: o,
  cuadrillas,
  subcontrato,
  cambiarCuadrillas,
  cambiarSubcontrato,
}: {
  oficio: OficioPropuesto;
  cuadrillas: number;
  subcontrato: boolean;
  cambiarCuadrillas: (n: number) => void;
  cambiarSubcontrato: (si: boolean) => void;
}) {
  const boton =
    "flex h-10 w-10 items-center justify-center rounded-lg border border-stone-300 bg-white text-lg font-semibold text-stone-800 transition hover:bg-stone-50 active:scale-95 disabled:opacity-40";
  return (
    <li className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-4 py-3">
      <div className="min-w-0 flex-1 basis-48">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-stone-900">{o.nombre}</span>
          {o.en_ruta_critica && <Pildora tono="problema">Ruta crítica</Pildora>}
        </div>
        <p className="text-sm tabular-nums text-stone-600">
          {o.personas_por_cuadrilla} por cuadrilla · {o.pasos} {o.pasos === 1 ? "paso" : "pasos"} · {dias(o.dias_trabajo)} de trabajo
        </p>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          aria-pressed={subcontrato}
          onClick={() => cambiarSubcontrato(!subcontrato)}
          className={`min-h-10 rounded-lg border px-2.5 text-xs font-medium transition ${
            subcontrato ? "border-stone-700 bg-stone-800 text-white" : "border-stone-300 bg-white text-stone-700 hover:bg-stone-50"
          }`}
        >
          Subcontrato
        </button>
        <button type="button" className={boton} aria-label={`Una cuadrilla menos de ${o.nombre}`} disabled={cuadrillas <= 1} onClick={() => cambiarCuadrillas(cuadrillas - 1)}>
          −
        </button>
        <span className="w-6 text-center text-lg font-semibold tabular-nums text-stone-900" aria-label={`${cuadrillas} cuadrillas`}>
          {cuadrillas}
        </span>
        <button type="button" className={boton} aria-label={`Una cuadrilla más de ${o.nombre}`} disabled={cuadrillas >= 10} onClick={() => cambiarCuadrillas(cuadrillas + 1)}>
          +
        </button>
      </div>
    </li>
  );
}
