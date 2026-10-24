import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api";
import type { Encargado, ObraResumen } from "../tipos";
import { Marco } from "../componentes/Marco";
import { IconoCuenta, IconoLapiz, IconoMas } from "../componentes/iconos";
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
  Pildora,
  Tarjeta,
} from "../componentes/ui";
import { useObras } from "./Obras";

/** Encargados de obra del dueño: crearlos, darles PIN y elegir qué obras ven. */
export function Equipo() {
  const equipo = useQuery({ queryKey: ["equipo"], queryFn: () => api<Encargado[]>("/api/equipo") });
  const obras = useObras();
  const [editando, setEditando] = useState<number | null>(null);
  const nombres = new Map((obras.data ?? []).map((o) => [o.id, o.nombre]));

  return (
    <Marco titulo="Equipo" volver="/cuenta">
      <p className="text-sm text-stone-600">
        El encargado entra con su número de celular y un PIN de 6 dígitos. Solo ve las obras que le asignes.
      </p>
      {equipo.isLoading && <Cargando />}
      <MensajeError error={equipo.error} reintentar={() => equipo.refetch()} />
      {equipo.data && equipo.data.length === 0 && (
        <Tarjeta>
          <EstadoVacio icono={<IconoCuenta tamano={28} />} texto="Todavía no tienes encargados. Agrega el primero abajo." />
        </Tarjeta>
      )}
      {equipo.data && equipo.data.length > 0 && (
        <Tarjeta className="p-0">
          <ul className="divide-y divide-stone-100">
            {equipo.data.map((e) =>
              editando === e.id ? (
                <li key={e.id} className="p-4">
                  <EditarEncargado encargado={e} obras={obras.data ?? []} cerrar={() => setEditando(null)} />
                </li>
              ) : (
                <li key={e.id} className="flex items-start justify-between gap-3 px-4 py-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate font-medium text-stone-900">{e.nombre}</span>
                      {!e.activo && <Pildora tono="neutro">Sin acceso</Pildora>}
                    </div>
                    <div className="text-sm tabular-nums text-stone-600">{e.telefono}</div>
                    <div className="text-sm text-stone-600">
                      {e.obra_ids.length === 0
                        ? "Sin obras asignadas"
                        : e.obra_ids.map((id) => nombres.get(id) ?? `Obra ${id}`).join(" · ")}
                    </div>
                  </div>
                  <BotonIcono titulo={`Editar a ${e.nombre}`} onClick={() => setEditando(e.id)}>
                    <IconoLapiz />
                  </BotonIcono>
                </li>
              ),
            )}
          </ul>
        </Tarjeta>
      )}
      <NuevoEncargado obras={obras.data ?? []} />
    </Marco>
  );
}

function ElegirObras({
  obras,
  elegidas,
  cambiar,
}: {
  obras: ObraResumen[];
  elegidas: number[];
  cambiar: (ids: number[]) => void;
}) {
  if (obras.length === 0) return <p className="text-sm text-stone-600">Primero crea una obra para asignarla.</p>;
  return (
    <fieldset className="space-y-2">
      <legend className="mb-1.5 text-sm font-medium text-stone-800">Obras que puede ver</legend>
      {obras.map((o) => (
        <Interruptor
          key={o.id}
          etiqueta={o.nombre}
          activo={elegidas.includes(o.id)}
          cambiar={(si) => cambiar(si ? [...elegidas, o.id] : elegidas.filter((id) => id !== o.id))}
        />
      ))}
    </fieldset>
  );
}

const PIN = { inputMode: "numeric" as const, pattern: "[0-9]{6}", maxLength: 6, autoComplete: "off" };

function NuevoEncargado({ obras }: { obras: ObraResumen[] }) {
  const vacio = { nombre: "", telefono: "", pin: "", obra_ids: [] as number[] };
  const [abierto, setAbierto] = useState(false);
  const [datos, setDatos] = useState(vacio);
  const cliente = useQueryClient();
  const crear = useMutation({
    mutationFn: () => api<Encargado>("/api/equipo", "POST", datos),
    onSuccess: (e) => {
      cliente.invalidateQueries({ queryKey: ["equipo"] });
      avisar(`${e.nombre} ya puede entrar con su celular y PIN`);
      setDatos(vacio);
      setAbierto(false);
    },
  });

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    crear.mutate();
  }

  if (!abierto) {
    return (
      <Boton className="w-full" onClick={() => setAbierto(true)}>
        <IconoMas />
        Nuevo encargado
      </Boton>
    );
  }

  return (
    <Tarjeta>
      <form onSubmit={enviar} className="space-y-3">
        <h2 className="font-semibold text-stone-900">Nuevo encargado</h2>
        <Campo etiqueta="Nombre">
          <Entrada value={datos.nombre} onChange={(e) => setDatos({ ...datos, nombre: e.target.value })} required minLength={2} autoFocus />
        </Campo>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Celular">
            <Entrada
              type="tel"
              inputMode="tel"
              value={datos.telefono}
              onChange={(e) => setDatos({ ...datos, telefono: e.target.value })}
              placeholder="70000000"
              required
              className="tabular-nums"
            />
          </Campo>
          <Campo etiqueta="PIN" ayuda="6 números">
            <Entrada {...PIN} value={datos.pin} onChange={(e) => setDatos({ ...datos, pin: e.target.value })} required className="tabular-nums" />
          </Campo>
        </div>
        <ElegirObras obras={obras} elegidas={datos.obra_ids} cambiar={(obra_ids) => setDatos({ ...datos, obra_ids })} />
        <MensajeError error={crear.error} />
        <div className="flex gap-3">
          <Boton type="button" variante="secundario" className="flex-1" onClick={() => setAbierto(false)}>
            Cancelar
          </Boton>
          <Boton type="submit" className="flex-1" disabled={crear.isPending}>
            {crear.isPending ? "Guardando…" : "Guardar"}
          </Boton>
        </div>
      </form>
    </Tarjeta>
  );
}

function EditarEncargado({ encargado, obras, cerrar }: { encargado: Encargado; obras: ObraResumen[]; cerrar: () => void }) {
  const [datos, setDatos] = useState({
    nombre: encargado.nombre,
    pin: "",
    activo: encargado.activo,
    obra_ids: encargado.obra_ids,
  });
  const cliente = useQueryClient();
  const guardar = useMutation({
    // El PIN solo se envía si se escribió uno nuevo.
    mutationFn: () => api<Encargado>(`/api/equipo/${encargado.id}`, "PATCH", { ...datos, pin: datos.pin || null }),
    onSuccess: () => {
      cliente.invalidateQueries({ queryKey: ["equipo"] });
      avisar("Cambios guardados");
      cerrar();
    },
  });

  function enviar(ev: FormEvent) {
    ev.preventDefault();
    guardar.mutate();
  }

  return (
    <form onSubmit={enviar} className="space-y-3">
      <div className="text-sm tabular-nums text-stone-600">{encargado.telefono}</div>
      <Campo etiqueta="Nombre">
        <Entrada value={datos.nombre} onChange={(e) => setDatos({ ...datos, nombre: e.target.value })} required minLength={2} />
      </Campo>
      <Campo etiqueta="PIN nuevo" ayuda="Déjalo vacío para mantener el actual">
        <Entrada {...PIN} value={datos.pin} onChange={(e) => setDatos({ ...datos, pin: e.target.value })} className="tabular-nums" />
      </Campo>
      <ElegirObras obras={obras} elegidas={datos.obra_ids} cambiar={(obra_ids) => setDatos({ ...datos, obra_ids })} />
      <Interruptor etiqueta="Puede entrar a la app" activo={datos.activo} cambiar={(activo) => setDatos({ ...datos, activo })} />
      <MensajeError error={guardar.error} />
      <div className="flex gap-3">
        <Boton type="button" variante="secundario" className="flex-1" onClick={cerrar}>
          Cancelar
        </Boton>
        <Boton type="submit" className="flex-1" disabled={guardar.isPending}>
          {guardar.isPending ? "Guardando…" : "Guardar"}
        </Boton>
      </div>
    </form>
  );
}
