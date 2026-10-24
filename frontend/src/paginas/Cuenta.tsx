import { useNavigate } from "react-router-dom";
import { useSesion } from "../sesion";
import { Marco } from "../componentes/Marco";
import { IconoAdelante, IconoCuenta, IconoSalir } from "../componentes/iconos";
import { Boton, BotonEnlace, Tarjeta } from "../componentes/ui";

const ROLES = { dueno: "Dueño / constructor", encargado: "Encargado de obra" };

/** Datos del usuario y salida de la sesión (fuera de la cabecera para no tocarla sin querer). */
export function Cuenta() {
  const { usuario, salir } = useSesion();
  const navegar = useNavigate();
  if (!usuario) return null;

  return (
    <Marco titulo="Cuenta">
      <Tarjeta className="space-y-3">
        <div>
          <p className="text-lg font-semibold tracking-tight text-stone-900">{usuario.nombre}</p>
          <p className="text-sm text-stone-600">{ROLES[usuario.rol]}</p>
        </div>
        <dl className="divide-y divide-stone-100 text-sm">
          {usuario.correo && (
            <div className="flex justify-between gap-3 py-2">
              <dt className="text-stone-600">Correo</dt>
              <dd className="truncate text-stone-900">{usuario.correo}</dd>
            </div>
          )}
          {usuario.telefono && (
            <div className="flex justify-between gap-3 py-2">
              <dt className="text-stone-600">Celular</dt>
              <dd className="tabular-nums text-stone-900">{usuario.telefono}</dd>
            </div>
          )}
        </dl>
      </Tarjeta>
      {usuario.rol === "dueno" && (
        <BotonEnlace a="/equipo" variante="secundario" className="w-full justify-between">
          <span className="flex items-center gap-2">
            <IconoCuenta />
            Equipo: encargados de obra
          </span>
          <IconoAdelante />
        </BotonEnlace>
      )}
      <Boton
        variante="secundario"
        className="w-full"
        onClick={() => {
          salir();
          navegar("/ingresar");
        }}
      >
        <IconoSalir />
        Salir de la cuenta
      </Boton>
    </Marco>
  );
}
