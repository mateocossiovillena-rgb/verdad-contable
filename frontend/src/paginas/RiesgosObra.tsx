import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api";
import { dinero, leerMonto } from "../formato";
import type { EstadoRiesgo, EstimadoObra, EstrategiaRiesgo, RegistroRiesgos, Riesgo } from "../tipos";
import { ExcelRegistros } from "./CambiosObra";
import {
  AreaTexto,
  Boton,
  Campo,
  Cargando,
  Entrada,
  MensajeError,
  Metrica,
  Pildora,
  Selector,
  Tarjeta,
  avisar,
  type Tono,
} from "../componentes/ui";

// Registro de riesgos (AACE 44R-08): valor esperado P × I y contingencia sugerida.

const ESTRATEGIAS: { valor: EstrategiaRiesgo; texto: string }[] = [
  { valor: "evitar", texto: "Evitar" },
  { valor: "mitigar", texto: "Mitigar" },
  { valor: "transferir", texto: "Transferir" },
  { valor: "aceptar", texto: "Aceptar" },
];
const ESTADOS: { valor: EstadoRiesgo; texto: string }[] = [
  { valor: "abierto", texto: "Abierto" },
  { valor: "ocurrido", texto: "Ocurrido" },
  { valor: "cerrado", texto: "Cerrado" },
];
const TONO_NIVEL: Record<Riesgo["nivel"], Tono> = { bajo: "bien", medio: "atencion", alto: "problema" };
const TEXTO_NIVEL: Record<Riesgo["nivel"], string> = { bajo: "Nivel bajo", medio: "Nivel medio", alto: "Nivel alto" };

function useRiesgos(obraId: string) {
  return useQuery({ queryKey: ["riesgos", obraId], queryFn: () => api<RegistroRiesgos>(`/api/obras/${obraId}/riesgos`) });
}

function useCambioRiesgo(obraId: string) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ ruta, metodo, cuerpo }: { ruta: string; metodo: string; cuerpo?: unknown }) =>
      api<RegistroRiesgos>(ruta, metodo, cuerpo),
    onSuccess: (r) => {
      cliente.setQueryData(["riesgos", obraId], r);
      cliente.invalidateQueries({ queryKey: ["estimado", obraId] });
    },
  });
}

/** Botón que copia la suma P × I de los riesgos abiertos a la contingencia de la Base del estimado. */
export function BotonContingencia({ obraId, deshabilitado }: { obraId: string; deshabilitado?: boolean }) {
  const cliente = useQueryClient();
  const usar = useMutation({
    mutationFn: () => api<EstimadoObra>(`/api/obras/${obraId}/riesgos/contingencia`, "POST"),
    onSuccess: (e) => {
      cliente.setQueryData(["estimado", obraId], e);
      cliente.invalidateQueries({ queryKey: ["riesgos", obraId] });
      avisar("Contingencia actualizada en la Base del estimado");
    },
  });
  return (
    <>
      <Boton variante="secundario" onClick={() => usar.mutate()} disabled={usar.isPending || deshabilitado}>
        {usar.isPending ? "Guardando…" : "Usar como contingencia"}
      </Boton>
      <MensajeError error={usar.error} />
    </>
  );
}

export function VistaRiesgos({ obraId }: { obraId: string }) {
  const registro = useRiesgos(obraId);
  const [editando, setEditando] = useState<Riesgo | "nuevo" | null>(null);
  const r = registro.data;
  if (registro.isLoading) return <Cargando filas={3} />;
  if (!r) return <MensajeError error={registro.error} reintentar={() => registro.refetch()} />;
  const m = r.moneda;
  const pct = (n: number | null) => (n === null ? "—" : `${n.toLocaleString("es-BO")} %`);

  return (
    <>
      <Tarjeta className="space-y-4">
        <div>
          <h2 className="font-semibold text-stone-900">Registro de riesgos</h2>
          <p className="text-sm text-stone-600">
            AACE 44R-08. Valor esperado = probabilidad × impacto. La suma de los riesgos abiertos es la contingencia que el
            registro sugiere para el estimado.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Metrica etiqueta="Riesgos abiertos" valor={r.abiertos} />
          <Metrica etiqueta="Contingencia sugerida (Σ P × I)" valor={dinero(r.valor_esperado, m)} detalle={`${pct(r.porcentaje_del_estimado)} del estimado`} />
          <Metrica etiqueta="Días esperados (Σ P × días)" valor={r.dias_esperados.toLocaleString("es-BO")} />
          <Metrica etiqueta="Contingencia actual (Base)" valor={pct(r.contingencia_actual_porcentaje)} />
        </div>
        <div className="flex flex-wrap gap-2">
          <BotonContingencia obraId={obraId} deshabilitado={r.abiertos === 0 || r.total_estimado === 0} />
        </div>
      </Tarjeta>

      {editando === null ? (
        <Boton className="w-full" onClick={() => setEditando("nuevo")}>
          Agregar riesgo
        </Boton>
      ) : (
        <FormRiesgo obraId={obraId} riesgo={editando === "nuevo" ? null : editando} cerrar={() => setEditando(null)} />
      )}

      {r.riesgos.length === 0 ? (
        <Tarjeta>
          <p className="text-sm text-stone-600">Todavía no hay riesgos. Piensa qué podría subir el costo o atrasar la obra.</p>
        </Tarjeta>
      ) : (
        <Tarjeta className="p-0">
          <ul className="divide-y divide-stone-100">
            {r.riesgos.map((x) => (
              <li key={x.id}>
                <button
                  type="button"
                  onClick={() => setEditando(x)}
                  className={`w-full space-y-1.5 px-4 py-3 text-left transition hover:bg-stone-50 ${x.estado !== "abierto" ? "opacity-70" : ""}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <span className="mr-2 font-mono text-xs text-stone-500">{x.codigo}</span>
                      <span className="font-medium text-stone-900">{x.descripcion}</span>
                      {x.causa && <div className="text-sm text-stone-600">Causa: {x.causa}</div>}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1">
                      {x.estado === "abierto" ? (
                        <Pildora tono={TONO_NIVEL[x.nivel]}>{TEXTO_NIVEL[x.nivel]}</Pildora>
                      ) : (
                        <Pildora tono="neutro">{ESTADOS.find((e) => e.valor === x.estado)?.texto}</Pildora>
                      )}
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm tabular-nums sm:grid-cols-4">
                    <span className="text-stone-600">
                      P <span className="text-stone-900">{x.probabilidad.toLocaleString("es-BO")} %</span>
                    </span>
                    <span className="text-stone-600">
                      I <span className="text-stone-900">{dinero(x.impacto_costo, m)}</span> · {x.impacto_dias} d
                    </span>
                    <span className="text-stone-600">
                      P × I <span className="font-semibold text-stone-900">{dinero(x.valor_esperado, m)}</span>
                    </span>
                    <span className="text-stone-600">
                      {ESTRATEGIAS.find((e) => e.valor === x.estrategia)?.texto}
                      {x.responsable && ` · ${x.responsable}`}
                    </span>
                  </div>
                  {x.respuesta && <div className="text-sm text-stone-700">Respuesta: {x.respuesta}</div>}
                </button>
              </li>
            ))}
          </ul>
        </Tarjeta>
      )}

      <ExcelRegistros obraId={obraId} />
    </>
  );
}

function FormRiesgo({ obraId, riesgo, cerrar }: { obraId: string; riesgo: Riesgo | null; cerrar: () => void }) {
  const cambio = useCambioRiesgo(obraId);
  const [d, setD] = useState({
    descripcion: riesgo?.descripcion ?? "",
    causa: riesgo?.causa ?? "",
    probabilidad: riesgo ? String(riesgo.probabilidad).replace(".", ",") : "",
    impacto_costo: riesgo ? String(riesgo.impacto_costo).replace(".", ",") : "",
    impacto_dias: riesgo ? String(riesgo.impacto_dias) : "0",
    responsable: riesgo?.responsable ?? "",
    estrategia: riesgo?.estrategia ?? ("mitigar" as EstrategiaRiesgo),
    respuesta: riesgo?.respuesta ?? "",
    estado: riesgo?.estado ?? ("abierto" as EstadoRiesgo),
  });
  const campo = (clave: keyof typeof d) => (e: { target: { value: string } }) => setD({ ...d, [clave]: e.target.value });

  function enviar(e: FormEvent) {
    e.preventDefault();
    const cuerpo = {
      ...d,
      probabilidad: leerMonto(d.probabilidad) ?? "0",
      impacto_costo: leerMonto(d.impacto_costo) ?? "0",
      impacto_dias: Number(d.impacto_dias || 0),
    };
    cambio.mutate(
      riesgo
        ? { ruta: `/api/riesgos/${riesgo.id}`, metodo: "PUT", cuerpo }
        : { ruta: `/api/obras/${obraId}/riesgos`, metodo: "POST", cuerpo },
      {
        onSuccess: () => {
          avisar(riesgo ? "Riesgo actualizado" : "Riesgo agregado");
          cerrar();
        },
      },
    );
  }

  function borrar() {
    if (!riesgo) return;
    cambio.mutate({ ruta: `/api/riesgos/${riesgo.id}`, metodo: "DELETE" }, { onSuccess: () => cerrar() });
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="space-y-3">
        <h2 className="font-semibold text-stone-900">{riesgo ? `Editar ${riesgo.codigo}` : "Nuevo riesgo"}</h2>
        <Campo etiqueta="Descripción">
          <Entrada required minLength={3} value={d.descripcion} onChange={campo("descripcion")} placeholder="Suba del precio del fierro" />
        </Campo>
        <Campo etiqueta="Causa">
          <Entrada value={d.causa} onChange={campo("causa")} placeholder="Escasez de dólares" />
        </Campo>
        <div className="grid grid-cols-3 gap-3">
          <Campo etiqueta="Probabilidad (%)">
            <Entrada required inputMode="decimal" className="text-right tabular-nums" value={d.probabilidad} onChange={campo("probabilidad")} />
          </Campo>
          <Campo etiqueta="Impacto (Bs)">
            <Entrada inputMode="decimal" className="text-right tabular-nums" value={d.impacto_costo} onChange={campo("impacto_costo")} />
          </Campo>
          <Campo etiqueta="Impacto (días)">
            <Entrada inputMode="numeric" className="text-right tabular-nums" value={d.impacto_dias} onChange={campo("impacto_dias")} />
          </Campo>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Estrategia">
            <Selector value={d.estrategia} onChange={campo("estrategia")}>
              {ESTRATEGIAS.map((x) => (
                <option key={x.valor} value={x.valor}>
                  {x.texto}
                </option>
              ))}
            </Selector>
          </Campo>
          <Campo etiqueta="Estado">
            <Selector value={d.estado} onChange={campo("estado")}>
              {ESTADOS.map((x) => (
                <option key={x.valor} value={x.valor}>
                  {x.texto}
                </option>
              ))}
            </Selector>
          </Campo>
        </div>
        <Campo etiqueta="Responsable">
          <Entrada value={d.responsable} onChange={campo("responsable")} placeholder="Residente de obra" />
        </Campo>
        <Campo etiqueta="Respuesta (qué se hará)">
          <AreaTexto value={d.respuesta} onChange={campo("respuesta")} />
        </Campo>
        <MensajeError error={cambio.error} />
        <div className="flex flex-wrap gap-2">
          <Boton type="submit" disabled={cambio.isPending}>
            {cambio.isPending ? "Guardando…" : "Guardar"}
          </Boton>
          <Boton type="button" variante="fantasma" onClick={cerrar}>
            Cancelar
          </Boton>
          {riesgo && (
            <Boton type="button" variante="fantasma" className="ml-auto text-red-700" onClick={borrar} disabled={cambio.isPending}>
              Borrar (error de carga)
            </Boton>
          )}
        </div>
        {riesgo && <p className="text-xs text-stone-600">Si el riesgo ya no aplica, márcalo “Cerrado” en vez de borrarlo: así queda el historial.</p>}
      </form>
    </Tarjeta>
  );
}
