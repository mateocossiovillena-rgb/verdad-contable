import { useEffect, useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useSesion } from "../sesion";
import {
  descartarPendiente,
  enviarPendientes,
  escucharPendientes,
  leerPendientes,
  reintentarPendiente,
  type Pendiente,
} from "../cola";

/** Estructura de cada pantalla: barra superior, contenido y menú inferior. */
export function Marco({ titulo, volver, children }: { titulo: string; volver?: string; children: ReactNode }) {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();
  const esDueno = usuario?.rol === "dueno";

  return (
    <div className="mx-auto flex min-h-dvh max-w-3xl flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-3 bg-marca-600 px-4 py-3 text-white shadow">
        {volver && (
          <Link to={volver} className="-ml-1 rounded-lg px-2 py-1 text-2xl leading-none" aria-label="Volver">
            ‹
          </Link>
        )}
        <h1 className="flex-1 truncate text-lg font-semibold">{titulo}</h1>
        <button
          className="rounded-lg px-2 py-1 text-sm text-marca-100 hover:text-white"
          onClick={() => {
            salir();
            navegar("/ingresar");
          }}
        >
          Salir
        </button>
      </header>
      <AvisoPendientes />
      <main className={`flex-1 space-y-4 p-4 ${esDueno ? "pb-24" : ""}`}>{children}</main>
      {esDueno && <MenuDueno />}
    </div>
  );
}

function MenuDueno() {
  const clase = ({ isActive }: { isActive: boolean }) =>
    `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs font-medium ${isActive ? "text-marca-600" : "text-stone-500"}`;
  return (
    <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-stone-200 bg-white pb-[env(safe-area-inset-bottom)]">
      <div className="mx-auto flex max-w-3xl">
        <NavLink to="/obras" className={clase}>
          <span className="text-xl">🏗️</span>Obras
        </NavLink>
        <NavLink to="/alertas" className={clase}>
          <span className="text-xl">🔔</span>Alertas
        </NavLink>
        <NavLink to="/equipo" className={clase}>
          <span className="text-xl">👷</span>Equipo
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
    <div className={`px-4 py-2 text-sm ${conError.length ? "bg-red-100 text-red-900" : "bg-amber-100 text-amber-900"}`}>
      <button className="w-full text-left font-medium" onClick={() => setAbierto(!abierto)}>
        {conError.length
          ? `⚠️ ${conError.length} registro(s) no se pudieron guardar. Toca para ver.`
          : `📶 ${pendientes.length} registro(s) esperando señal para enviarse.`}
      </button>
      {abierto && (
        <ul className="mt-2 space-y-2">
          {pendientes.map((p) => (
            <li key={p.id} className="rounded-lg bg-white/70 p-2">
              <div>{p.descripcion}</div>
              {p.error && (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <span className="text-red-700">{p.error}</span>
                  <button className="underline" onClick={() => reintentarPendiente(p.id)}>
                    Reintentar
                  </button>
                  <button className="underline" onClick={() => descartarPendiente(p.id)}>
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
