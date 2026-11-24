import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import { dinero, fecha, leerMonto, pct } from "../formato";
import type { IndicadoresObra, ReglaMedicion } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoCheck, IconoLadrillos, IconoMas } from "../componentes/iconos";
import {
  avisar,
  BarraAvance,
  Boton,
  Campo,
  Cargando,
  Entrada,
  EstadoVacio,
  MensajeError,
  Pildora,
  PildoraSemaforo,
  Selector,
  Tarjeta,
} from "../componentes/ui";

export function useIndicadores(obraId: string | undefined) {
  return useQuery({
    queryKey: ["indicadores", obraId],
    queryFn: () => api<IndicadoresObra>(`/api/obras/${obraId}/indicadores`),
  });
}

/** Partidas (presupuesto, gasto y avance) e hitos de la obra. */
export function Partidas() {
  const { obraId } = useParams();
  const datos = useIndicadores(obraId);
  const d = datos.data;
  const moneda = d?.obra.moneda ?? "Bs";

  return (
    <Marco titulo={`Partidas · ${d?.obra.nombre ?? ""}`} volver={`/obras/${obraId}`} ancho>
      {datos.isLoading && <Cargando />}
      <MensajeError error={datos.error} reintentar={() => datos.refetch()} />
      {d && (
        <div className="space-y-4 lg:grid lg:grid-cols-3 lg:gap-4 lg:space-y-0">
          <div className="space-y-4 lg:col-span-2">
            {d.partidas.length === 0 ? (
              <Tarjeta>
                <EstadoVacio icono={<IconoLadrillos tamano={28} />} texto="Todavía no hay partidas. Agrega la primera abajo." />
              </Tarjeta>
            ) : (
              <Tarjeta className="p-0">
                <ul className="divide-y divide-stone-100">
                  {d.partidas.map(({ partida: p, indicadores: i, semaforo, advertencias, porcentaje_avance }) => (
                    <li key={p.id} className="space-y-2 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate font-medium text-stone-900">
                            {p.codigo && <span className="mr-1 tabular-nums text-stone-500">{p.codigo}</span>}
                            {p.nombre}
                          </div>
                          <div className="text-sm text-stone-600">
                            {p.desde_cronograma && "Cronograma · "}
                            {p.fase && `${p.fase} · `}
                            {p.fecha_inicio ? (
                              <span className="tabular-nums">
                                {fecha(p.fecha_inicio)} – {fecha(p.fecha_fin)}
                              </span>
                            ) : (
                              "Sin fechas"
                            )}
                          </div>
                        </div>
                        {!p.es_generales && <PildoraSemaforo valor={semaforo} />}
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-sm tabular-nums">
                        <Dato
                          titulo={d.linea_base_version ? `BAC (línea base v${d.linea_base_version})` : "Presupuesto"}
                          valor={dinero(i.bac, moneda)}
                        />
                        <Dato titulo="Gastado" valor={dinero(i.ac, moneda)} />
                        <Dato titulo="Avance" valor={p.es_generales ? "—" : `${Math.round(porcentaje_avance)} %`} />
                      </div>
                      {!p.es_generales && <BarraAvance real={porcentaje_avance / 100} plan={i.avance_planificado} semaforo={semaforo} />}
                      {!p.es_generales && (
                        <ReglaPartida obraId={obraId!} partidaId={p.id} regla={p.regla_medicion} ev={dinero(i.ev, moneda)} />
                      )}
                      {advertencias.map((a) => (
                        <p key={a.codigo} className="text-sm text-amber-800">
                          {a.mensaje}
                        </p>
                      ))}
                    </li>
                  ))}
                </ul>
              </Tarjeta>
            )}
            <p className="text-sm text-stone-600">
              Cada actividad del cronograma aparece aquí sola, con sus fechas y su costo como presupuesto: se cambia
              desde el cronograma. Agrega una partida suelta solo para lo que no está en el cronograma.
            </p>
            <NuevaPartida obraId={obraId!} />
          </div>

          <div className="space-y-4">
            <Tarjeta className="space-y-3">
              <h2 className="font-semibold text-stone-900">Hitos</h2>
              {d.hitos.length === 0 ? (
                <p className="text-sm text-stone-600">Sin hitos todavía.</p>
              ) : (
                <ul className="divide-y divide-stone-100">
                  {d.hitos.map((h) => (
                    <li key={h.id} className="flex items-center justify-between gap-3 py-2.5">
                      <div className="min-w-0">
                        <div className="truncate font-medium text-stone-900">{h.nombre}</div>
                        <div className="text-sm tabular-nums text-stone-600">Previsto {fecha(h.fecha_prevista)}</div>
                      </div>
                      {h.fecha_real ? (
                        <Pildora tono="bien">Cumplido {fecha(h.fecha_real)}</Pildora>
                      ) : h.fecha_prevista < d.corte ? (
                        <Pildora tono="problema">Vencido</Pildora>
                      ) : (
                        <Pildora tono="neutro">Pendiente</Pildora>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <NuevoHito obraId={obraId!} />
            </Tarjeta>
            <p className="text-sm text-stone-600">
              Avance planificado de la obra al {fecha(d.corte)}: <span className="tabular-nums">{pct(d.indicadores.avance_planificado)}</span>
            </p>
          </div>
        </div>
      )}
    </Marco>
  );
}

const REGLAS: { valor: ReglaMedicion; texto: string }[] = [
  { valor: "porcentaje", texto: "% físico" },
  { valor: "0_100", texto: "0/100" },
  { valor: "50_50", texto: "50/50" },
];

/** Regla de medición del avance (AACE 82R-13): cómo el % físico se convierte en valor ganado. */
function ReglaPartida({ obraId, partidaId, regla, ev }: { obraId: string; partidaId: number; regla: ReglaMedicion; ev: string }) {
  const cliente = useQueryClient();
  const cambiar = useMutation({
    mutationFn: (r: ReglaMedicion) => api(`/api/partidas/${partidaId}/medicion`, "PUT", { regla_medicion: r }),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["indicadores", obraId] });
      cliente.invalidateQueries({ queryKey: ["obras"] });
      avisar("Regla de medición cambiada");
    },
  });
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <label
        className="flex items-center gap-2 text-stone-600"
        title="0/100: se gana al terminar · 50/50: mitad al empezar y mitad al terminar · % físico: según el avance"
      >
        Medición
        <Selector
          className="min-h-10 w-28 py-1 text-sm"
          value={regla}
          disabled={cambiar.isPending}
          onChange={(e) => cambiar.mutate(e.target.value as ReglaMedicion)}
        >
          {REGLAS.map((r) => (
            <option key={r.valor} value={r.valor}>
              {r.texto}
            </option>
          ))}
        </Selector>
      </label>
      <span className="tabular-nums text-stone-600">EV {ev}</span>
      <MensajeError error={cambiar.error} />
    </div>
  );
}

function Dato({ titulo, valor }: { titulo: string; valor: string }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-stone-600">{titulo}</div>
      <div className="truncate font-medium text-stone-900">{valor}</div>
    </div>
  );
}

function NuevaPartida({ obraId }: { obraId: string }) {
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState({ codigo: "", nombre: "", fase: "", presupuesto: "", fecha_inicio: "", fecha_fin: "" });
  const cliente = useQueryClient();
  const crear = useMutation({
    mutationFn: () =>
      api(`/api/obras/${obraId}/partidas`, "POST", {
        ...datos,
        presupuesto: leerMonto(datos.presupuesto) ?? "0",
        fecha_inicio: datos.fecha_inicio || null,
        fecha_fin: datos.fecha_fin || null,
      }),
    onSuccess: () => {
      cliente.invalidateQueries();
      avisar(`Partida «${datos.nombre}» agregada`);
      setDatos({ codigo: "", nombre: "", fase: "", presupuesto: "", fecha_inicio: "", fecha_fin: "" });
      setAbierto(false);
    },
  });
  const cambiar = (campo: keyof typeof datos) => (e: { target: { value: string } }) =>
    setDatos({ ...datos, [campo]: e.target.value });

  function enviar(e: FormEvent) {
    e.preventDefault();
    crear.mutate();
  }

  if (!abierto) {
    return (
      <Boton variante="secundario" className="w-full" onClick={() => setAbierto(true)}>
        <IconoMas />
        Nueva partida
      </Boton>
    );
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="space-y-3">
        <h2 className="font-semibold text-stone-900">Nueva partida</h2>
        <div className="grid grid-cols-3 gap-3">
          <Campo etiqueta="Código">
            <Entrada value={datos.codigo} onChange={cambiar("codigo")} placeholder="02.01" />
          </Campo>
          <div className="col-span-2">
            <Campo etiqueta="Nombre">
              <Entrada value={datos.nombre} onChange={cambiar("nombre")} placeholder="Muros de ladrillo" required autoFocus />
            </Campo>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Fase">
            <Entrada value={datos.fase} onChange={cambiar("fase")} placeholder="Obra gruesa" />
          </Campo>
          <Campo etiqueta="Presupuesto">
            <Entrada inputMode="decimal" value={datos.presupuesto} onChange={cambiar("presupuesto")} placeholder="0,00" className="tabular-nums" />
          </Campo>
          <Campo etiqueta="Inicio">
            <Entrada type="date" value={datos.fecha_inicio} onChange={cambiar("fecha_inicio")} />
          </Campo>
          <Campo etiqueta="Fin">
            <Entrada type="date" value={datos.fecha_fin} onChange={cambiar("fecha_fin")} />
          </Campo>
        </div>
        <MensajeError error={crear.error} />
        <div className="flex gap-2">
          <Boton type="submit" disabled={crear.isPending}>
            {crear.isPending ? "Guardando…" : "Agregar partida"}
          </Boton>
          <Boton type="button" variante="secundario" onClick={() => setAbierto(false)}>
            Cancelar
          </Boton>
        </div>
      </form>
    </Tarjeta>
  );
}

function NuevoHito({ obraId }: { obraId: string }) {
  const [nombre, setNombre] = useState("");
  const [prevista, setPrevista] = useState("");
  const cliente = useQueryClient();
  const crear = useMutation({
    mutationFn: () => api(`/api/obras/${obraId}/hitos`, "POST", { nombre, fecha_prevista: prevista }),
    onSuccess: () => {
      cliente.invalidateQueries();
      avisar(`Hito «${nombre}» agregado`);
      setNombre("");
      setPrevista("");
    },
  });

  function enviar(e: FormEvent) {
    e.preventDefault();
    crear.mutate();
  }

  return (
    <form onSubmit={enviar} className="space-y-2 border-t border-stone-100 pt-3">
      <Entrada value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Nuevo hito (ej. Losa vaciada)" required aria-label="Nombre del hito" />
      <div className="flex gap-2">
        <Entrada type="date" value={prevista} onChange={(e) => setPrevista(e.target.value)} required aria-label="Fecha prevista" />
        <Boton type="submit" variante="secundario" disabled={crear.isPending} className="shrink-0">
          <IconoCheck tamano={18} />
          Agregar
        </Boton>
      </div>
      <MensajeError error={crear.error} />
    </form>
  );
}
