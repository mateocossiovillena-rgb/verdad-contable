import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { api, descargar, subirArchivo } from "../api";
import { dinero, fecha, hoyISO, leerMonto } from "../formato";
import type { BitacoraCambios, Cambio, EstadoCambio, RegistrosImportados, VistaPreviaRegistros } from "../tipos";
import { TablaProblemas } from "./ImportarObra";
import {
  AreaTexto,
  Boton,
  Campo,
  Cargando,
  Entrada,
  Interruptor,
  MensajeError,
  Metrica,
  Pildora,
  Tarjeta,
  avisar,
  type Tono,
} from "../componentes/ui";

// Bitácora de cambios: solo un cambio aprobado genera una nueva versión de la línea base.

const TONO_ESTADO: Record<EstadoCambio, Tono> = { pendiente: "atencion", aprobado: "bien", rechazado: "neutro" };
const TEXTO_ESTADO: Record<EstadoCambio, string> = { pendiente: "Pendiente", aprobado: "Aprobado", rechazado: "Rechazado" };

function useBitacora(obraId: string) {
  return useQuery({ queryKey: ["cambios", obraId], queryFn: () => api<BitacoraCambios>(`/api/obras/${obraId}/cambios`) });
}

function useCambioBitacora(obraId: string) {
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ ruta, metodo, cuerpo }: { ruta: string; metodo: string; cuerpo?: unknown }) =>
      api<BitacoraCambios>(ruta, metodo, cuerpo),
    onSuccess: (b) => {
      cliente.setQueryData(["cambios", obraId], b);
      // Aprobar crea una versión de la línea base y puede agregar una partida.
      for (const clave of ["estimado", "indicadores", "cronograma"]) cliente.invalidateQueries({ queryKey: [clave, obraId] });
      cliente.invalidateQueries({ queryKey: ["obras"] });
    },
  });
}

function signo(n: number, texto: string): string {
  return n > 0 ? `+${texto}` : texto;
}

export function VistaCambios({ obraId }: { obraId: string }) {
  const bitacora = useBitacora(obraId);
  const [editando, setEditando] = useState<Cambio | "nuevo" | null>(null);
  const b = bitacora.data;
  if (bitacora.isLoading) return <Cargando filas={3} />;
  if (!b) return <MensajeError error={bitacora.error} reintentar={() => bitacora.refetch()} />;
  const m = b.moneda;

  return (
    <>
      <Tarjeta className="space-y-4">
        <div>
          <h2 className="font-semibold text-stone-900">Bitácora de cambios</h2>
          <p className="text-sm text-stone-600">
            Todo cambio de alcance, costo o plazo se registra aquí. Solo un cambio aprobado crea una versión nueva de la
            línea base, y esa versión queda ligada al cambio que la originó.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Metrica etiqueta="Línea base vigente" valor={b.linea_base_version ? `v${b.linea_base_version}` : "Sin aprobar"} />
          <Metrica etiqueta="Pendientes" valor={b.pendientes} detalle={dinero(b.costo_pendiente, m)} />
          <Metrica etiqueta="Aprobados (costo)" valor={signo(b.costo_aprobado, dinero(b.costo_aprobado, m))} />
          <Metrica etiqueta="Aprobados (plazo)" valor={`${signo(b.dias_aprobados, String(b.dias_aprobados))} días`} />
        </div>
        {!b.linea_base_version && (
          <p className="text-sm text-amber-800">Aprueba primero la línea base inicial (pestaña Línea base) para poder aprobar cambios.</p>
        )}
      </Tarjeta>

      {editando === null ? (
        <Boton className="w-full" onClick={() => setEditando("nuevo")}>
          Registrar cambio
        </Boton>
      ) : (
        <FormCambio obraId={obraId} cambio={editando === "nuevo" ? null : editando} cerrar={() => setEditando(null)} />
      )}

      {b.cambios.length === 0 ? (
        <Tarjeta>
          <p className="text-sm text-stone-600">Todavía no hay cambios registrados.</p>
        </Tarjeta>
      ) : (
        <Tarjeta className="p-0">
          <ul className="divide-y divide-stone-100">
            {[...b.cambios].reverse().map((c) => (
              <FilaCambio
                key={c.id}
                obraId={obraId}
                c={c}
                moneda={m}
                puedeAprobar={!!b.linea_base_version}
                editar={() => setEditando(c)}
              />
            ))}
          </ul>
        </Tarjeta>
      )}

      <ExcelRegistros obraId={obraId} />
    </>
  );
}

function FilaCambio({
  obraId,
  c,
  moneda,
  puedeAprobar,
  editar,
}: {
  obraId: string;
  c: Cambio;
  moneda: string;
  puedeAprobar: boolean;
  editar: () => void;
}) {
  const [resolviendo, setResolviendo] = useState<"aprobar" | "rechazar" | null>(null);
  return (
    <li className="space-y-2 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <span className="mr-2 font-mono text-xs text-stone-500">{c.codigo}</span>
          <span className="font-medium text-stone-900">{c.descripcion}</span>
          <div className="text-sm text-stone-600">
            <span className="tabular-nums">{fecha(c.fecha)}</span> · Pide: {c.solicitante}
          </div>
        </div>
        <Pildora tono={TONO_ESTADO[c.estado as EstadoCambio]}>{TEXTO_ESTADO[c.estado as EstadoCambio]}</Pildora>
      </div>
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-sm tabular-nums text-stone-700">
        <span>Costo {signo(c.impacto_costo, dinero(c.impacto_costo, moneda))}</span>
        <span>Plazo {signo(c.impacto_dias, String(c.impacto_dias))} días</span>
        {c.linea_base_version && <span className="font-medium text-emerald-700">Generó la línea base v{c.linea_base_version}</span>}
      </div>
      {c.estado !== "pendiente" && (
        <p className="text-sm text-stone-600">
          {TEXTO_ESTADO[c.estado as EstadoCambio]} por {c.aprobador} el <span className="tabular-nums">{fecha(c.fecha_resolucion)}</span>
          {c.comentario_resolucion && ` · ${c.comentario_resolucion}`}
        </p>
      )}
      {c.estado === "pendiente" && resolviendo === null && (
        <div className="flex flex-wrap gap-2">
          <Boton variante="secundario" onClick={() => setResolviendo("aprobar")} disabled={!puedeAprobar}>
            Aprobar
          </Boton>
          <Boton variante="secundario" onClick={() => setResolviendo("rechazar")}>
            Rechazar
          </Boton>
          <Boton variante="fantasma" onClick={editar}>
            Editar
          </Boton>
        </div>
      )}
      {resolviendo && <Resolucion obraId={obraId} c={c} accion={resolviendo} cerrar={() => setResolviendo(null)} />}
    </li>
  );
}

function Resolucion({
  obraId,
  c,
  accion,
  cerrar,
}: {
  obraId: string;
  c: Cambio;
  accion: "aprobar" | "rechazar";
  cerrar: () => void;
}) {
  const cambio = useCambioBitacora(obraId);
  const [aprobador, setAprobador] = useState("");
  const [comentario, setComentario] = useState("");
  const [comoPartida, setComoPartida] = useState(c.impacto_costo > 0);

  function enviar(e: FormEvent) {
    e.preventDefault();
    cambio.mutate(
      { ruta: `/api/cambios/${c.id}/${accion}`, metodo: "POST", cuerpo: { aprobador, comentario, agregar_partida: comoPartida } },
      {
        onSuccess: (b) => {
          const v = b.cambios.find((x) => x.id === c.id)?.linea_base_version;
          avisar(accion === "aprobar" ? `${c.codigo} aprobado: línea base v${v}` : `${c.codigo} rechazado`);
          cerrar();
        },
      },
    );
  }

  return (
    <form onSubmit={enviar} className="space-y-3 rounded-xl bg-stone-50 p-3">
      <Campo etiqueta={accion === "aprobar" ? "Aprobado por" : "Rechazado por"}>
        <Entrada required minLength={2} value={aprobador} onChange={(e) => setAprobador(e.target.value)} placeholder="Ing. residente" />
      </Campo>
      <Campo etiqueta="Comentario">
        <Entrada value={comentario} onChange={(e) => setComentario(e.target.value)} />
      </Campo>
      {accion === "aprobar" && (
        <div className="space-y-1">
          <Interruptor etiqueta="Agregar como partida nueva" activo={comoPartida} cambiar={setComoPartida} />
          <p className="text-xs text-stone-600">
            {comoPartida
              ? `Se crea la partida ${c.codigo} con ${c.impacto_costo.toLocaleString("es-BO")} de presupuesto.`
              : "La versión nueva congela el cronograma tal como lo ajustaste a mano."}
          </p>
        </div>
      )}
      <MensajeError error={cambio.error} />
      <div className="flex gap-2">
        <Boton type="submit" disabled={cambio.isPending}>
          {cambio.isPending ? "Guardando…" : accion === "aprobar" ? "Aprobar y crear nueva línea base" : "Rechazar"}
        </Boton>
        <Boton type="button" variante="fantasma" onClick={cerrar}>
          Cancelar
        </Boton>
      </div>
    </form>
  );
}

function FormCambio({ obraId, cambio, cerrar }: { obraId: string; cambio: Cambio | null; cerrar: () => void }) {
  const guardar = useCambioBitacora(obraId);
  const [d, setD] = useState({
    fecha: cambio?.fecha ?? hoyISO(),
    solicitante: cambio?.solicitante ?? "",
    descripcion: cambio?.descripcion ?? "",
    impacto_costo: cambio ? String(cambio.impacto_costo).replace(".", ",") : "",
    impacto_dias: cambio ? String(cambio.impacto_dias) : "0",
  });
  const campo = (clave: keyof typeof d) => (e: { target: { value: string } }) => setD({ ...d, [clave]: e.target.value });

  function enviar(e: FormEvent) {
    e.preventDefault();
    const cuerpo = { ...d, impacto_costo: leerMonto(d.impacto_costo) ?? "0", impacto_dias: Number(d.impacto_dias || 0) };
    guardar.mutate(
      cambio ? { ruta: `/api/cambios/${cambio.id}`, metodo: "PUT", cuerpo } : { ruta: `/api/obras/${obraId}/cambios`, metodo: "POST", cuerpo },
      {
        onSuccess: () => {
          avisar(cambio ? "Cambio actualizado" : "Cambio registrado como pendiente");
          cerrar();
        },
      },
    );
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="space-y-3">
        <h2 className="font-semibold text-stone-900">{cambio ? `Editar ${cambio.codigo}` : "Nuevo cambio"}</h2>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Fecha">
            <Entrada type="date" required value={d.fecha} onChange={campo("fecha")} />
          </Campo>
          <Campo etiqueta="Solicitante">
            <Entrada required minLength={2} value={d.solicitante} onChange={campo("solicitante")} placeholder="Cliente" />
          </Campo>
        </div>
        <Campo etiqueta="Descripción">
          <AreaTexto required minLength={3} value={d.descripcion} onChange={campo("descripcion")} placeholder="Agregar baño de visitas" />
        </Campo>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Impacto en costo" ayuda="Negativo si quita alcance">
            <Entrada inputMode="decimal" className="text-right tabular-nums" value={d.impacto_costo} onChange={campo("impacto_costo")} />
          </Campo>
          <Campo etiqueta="Impacto en plazo (días)" ayuda="Negativo si acorta">
            <Entrada inputMode="numeric" className="text-right tabular-nums" value={d.impacto_dias} onChange={campo("impacto_dias")} />
          </Campo>
        </div>
        <MensajeError error={guardar.error} />
        <div className="flex flex-wrap gap-2">
          <Boton type="submit" disabled={guardar.isPending}>
            {guardar.isPending ? "Guardando…" : "Guardar"}
          </Boton>
          <Boton type="button" variante="fantasma" onClick={cerrar}>
            Cancelar
          </Boton>
          {cambio && (
            <Boton
              type="button"
              variante="fantasma"
              className="ml-auto text-red-700"
              disabled={guardar.isPending}
              onClick={() => guardar.mutate({ ruta: `/api/cambios/${cambio.id}`, metodo: "DELETE" }, { onSuccess: cerrar })}
            >
              Borrar (error de carga)
            </Boton>
          )}
        </div>
      </form>
    </Tarjeta>
  );
}

/** Descargar riesgos y cambios a Excel, editarlos y volver a importarlos con vista previa. */
export function ExcelRegistros({ obraId }: { obraId: string }) {
  const cliente = useQueryClient();
  const entrada = useRef<HTMLInputElement>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const descarga = useMutation({
    mutationFn: () => descargar(`/api/obras/${obraId}/registros.xlsx`, `riesgos-y-cambios-obra-${obraId}.xlsx`),
  });
  const revisar = useMutation({
    mutationFn: (a: File) => subirArchivo<VistaPreviaRegistros>(`/api/obras/${obraId}/registros/previa`, a),
  });
  const importar = useMutation({
    mutationFn: (a: File) => subirArchivo<RegistrosImportados>(`/api/obras/${obraId}/registros/importar`, a),
    onSuccess: (r) => {
      cliente.setQueryData(["riesgos", obraId], r.riesgos);
      cliente.setQueryData(["cambios", obraId], r.cambios);
      cliente.invalidateQueries({ queryKey: ["estimado", obraId] });
      revisar.reset();
      setArchivo(null);
      avisar("Riesgos y cambios importados");
    },
  });
  const p = revisar.data;

  return (
    <Tarjeta className="space-y-3">
      <div>
        <h2 className="font-semibold text-stone-900">Riesgos y cambios en Excel</h2>
        <p className="text-sm text-stone-600">
          Descarga el libro con lo ya cargado, edítalo y súbelo. Filas sin código = registros nuevos. Los cambios nuevos
          entran pendientes: se aprueban aquí.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Boton variante="secundario" onClick={() => descarga.mutate()} disabled={descarga.isPending}>
          {descarga.isPending ? "Descargando…" : "Descargar .xlsx"}
        </Boton>
        <Boton variante="secundario" onClick={() => entrada.current?.click()} disabled={revisar.isPending}>
          {revisar.isPending ? "Revisando…" : "Subir .xlsx"}
        </Boton>
        <input
          ref={entrada}
          type="file"
          accept=".xlsx"
          className="hidden"
          onChange={(e) => {
            const a = e.target.files?.[0];
            if (a) {
              setArchivo(a);
              importar.reset();
              revisar.mutate(a);
            }
            e.target.value = "";
          }}
        />
      </div>
      <MensajeError error={descarga.error ?? revisar.error} />
      {p && (
        <div className="space-y-3">
          <p className="text-sm tabular-nums text-stone-700">
            Riesgos: {p.riesgos_nuevos} nuevos, {p.riesgos_actualizados} actualizados · Cambios: {p.cambios_nuevos} nuevos,{" "}
            {p.cambios_actualizados} actualizados
          </p>
          {p.errores.length > 0 && <TablaProblemas titulo="Errores: corrígelos y vuelve a subir el archivo" lista={p.errores} tono="problema" />}
          {p.advertencias.length > 0 && <TablaProblemas titulo="Advertencias" lista={p.advertencias} tono="atencion" />}
          {p.valida && archivo && (
            <Boton onClick={() => importar.mutate(archivo)} disabled={importar.isPending}>
              {importar.isPending ? "Importando…" : "Confirmar e importar"}
            </Boton>
          )}
          <MensajeError error={importar.error} />
        </div>
      )}
    </Tarjeta>
  );
}
