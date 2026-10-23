import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useSesion } from "../sesion";
import type { Alerta } from "../tipos";
import {
  descartarPendiente,
  enviarPendientes,
  escucharPendientes,
  leerPendientes,
  reintentarPendiente,
  type Pendiente,
} from "../cola";
import { IconoAlerta, IconoAtras, IconoCampana, IconoCuenta, IconoObras, IconoSinSenal } from "./iconos";
import { Avisos } from "./ui";

/** Estructura de cada pantalla: barra superior, contenido y menú inferior. */
export function Marco({
  titulo,
  volver,
  accion,
  ancho = false,
  children,
}: {
  titulo: string;
  volver?: string;
  accion?: ReactNode;
  ancho?: boolean;
  children: ReactNode;
}) {
  const maximo = ancho ? "max-w-3xl lg:max-w-6xl" : "max-w-3xl";
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 backdrop-blur">
        <div className={`mx-auto flex h-14 items-center gap-1 px-2 ${maximo}`}>
          {volver ? (
            <Link
              to={volver}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-stone-700 hover:bg-stone-100"
              aria-label="Volver"
            >
              <IconoAtras tamano={22} />
            </Link>
          ) : (
            <span className="w-2" />
          )}
          <h1 className="min-w-0 flex-1 truncate text-lg font-semibold tracking-tight text-stone-900">{titulo}</h1>
          {accion}
        </div>
      </header>
      <AvisoPendientes />
      <main className={`mx-auto w-full flex-1 space-y-4 p-4 pb-28 ${maximo}`}>{children}</main>
      <MenuInferior />
      <Avisos />
    </div>
  );
}

function MenuInferior() {
  const { usuario } = useSesion();
  const esDueno = usuario?.rol === "dueno";
  const alertas = useQuery({
    queryKey: ["alertas"],
    queryFn: () => api<Alerta[]>("/api/alertas"),
    enabled: esDueno,
  });
  const cantidad = alertas.data?.length ?? 0;

  const clase = ({ isActive }: { isActive: boolean }) =>
    `relative flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-xs font-medium transition ${
      isActive ? "text-marca-700" : "text-stone-600 hover:text-stone-900"
    }`;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)]">
      <div className="mx-auto flex max-w-3xl">
        <NavLink to="/obras" className={clase}>
          <IconoObras tamano={22} />
          Obras
        </NavLink>
        {esDueno && (
          <NavLink to="/alertas" className={clase}>
            <span className="relative">
              <IconoCampana tamano={22} />
              {cantidad > 0 && (
                <span className="absolute -right-2.5 -top-1.5 min-w-[18px] rounded-full bg-red-600 px-1 text-center text-[11px] font-semibold leading-[18px] text-white tabular-nums">
                  {cantidad > 99 ? "99+" : cantidad}
                </span>
              )}
            </span>
            Alertas
          </NavLink>
        )}
        <NavLink to="/cuenta" className={clase}>
          <IconoCuenta tamano={22} />
          Cuenta
        </NavLink>
      </div>
    </nav>
  );
}

/** Muestra los registros guardados sin señal y los envía cuando vuelve la conexión. */
function AvisoPendientes() {
  const [pendientes, setPendientes] = useState<Pendiente[]>(leerPendientes);
  const [abierto, setAbierto] = useState(false);
  const cliente = useQueryClient();

  useEffect(() => {
    const quitar = escucharPendientes(setPendientes);
    const enviar = () =>
      enviarPendientes().then((n) => {
        if (n > 0) cliente.invalidateQueries();
      });
    enviar();
    window.addEventListener("online", enviar);
    const intervalo = window.setInterval(enviar, 30000);
    return () => {
      quitar();
      window.removeEventListener("online", enviar);
      window.clearInterval(intervalo);
    };
  }, [cliente]);

  if (pendientes.length === 0) return null;
  const conError = pendientes.filter((p) => p.error);

  return (
    <div
      className={`border-b px-4 py-2 text-sm ${
        conError.length ? "border-red-200 bg-red-50 text-red-800" : "border-amber-200 bg-amber-50 text-amber-900"
      }`}
    >
      <button className="mx-auto flex min-h-8 w-full max-w-3xl items-center gap-2 text-left font-medium" onClick={() => setAbierto(!abierto)}>
        {conError.length ? <IconoAlerta tamano={18} /> : <IconoSinSenal tamano={18} />}
        <span className="flex-1">
          {conError.length
            ? `${conError.length} registro(s) no se pudieron guardar. Toca para ver.`
            : `${pendientes.length} registro(s) guardados en el celular, se enviarán con señal.`}
        </span>
      </button>
      {abierto && (
        <ul className="mx-auto mt-2 max-w-3xl space-y-2">
          {pendientes.map((p) => (
            <li key={p.id} className="rounded-lg border border-stone-200 bg-white p-2 text-stone-800">
              <div>{p.descripcion}</div>
              {p.error && (
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <span className="text-red-700">{p.error}</span>
                  <button className="min-h-8 font-semibold underline" onClick={() => reintentarPendiente(p.id)}>
                    Reintentar
                  </button>
                  <button className="min-h-8 font-semibold underline" onClick={() => descartarPendiente(p.id)}>
                    Descartar
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
