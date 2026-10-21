import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, ErrorApi, token } from "./api";
import type { Usuario } from "./tipos";

const CLAVE_USUARIO = "vc_usuario";

interface ContextoSesion {
  usuario: Usuario | null;
  entrar: (nuevoToken: string, usuario: Usuario) => void;
  salir: () => void;
}

const Contexto = createContext<ContextoSesion | null>(null);

function usuarioGuardado(): Usuario | null {
  if (!token.leer()) return null;
  try {
    return JSON.parse(localStorage.getItem(CLAVE_USUARIO) ?? "null");
  } catch {
    return null;
  }
}

export function ProveedorSesion({ children }: { children: ReactNode }) {
  // Se recuerda el usuario para que la app abra aunque no haya señal.
  const [usuario, setUsuario] = useState<Usuario | null>(usuarioGuardado);
  const cliente = useQueryClient();

  const salir = useCallback(() => {
    token.borrar();
    localStorage.removeItem(CLAVE_USUARIO);
    cliente.clear();
    setUsuario(null);
  }, [cliente]);

  useEffect(() => {
    if (!token.leer()) return;
    api<Usuario>("/api/sesion/yo")
      .then((u) => {
        localStorage.setItem(CLAVE_USUARIO, JSON.stringify(u));
        setUsuario(u);
      })
      .catch((e) => {
        if (e instanceof ErrorApi && e.estado === 401) salir();
      });
  }, [salir]);

  const entrar = useCallback((nuevoToken: string, u: Usuario) => {
    token.guardar(nuevoToken);
    localStorage.setItem(CLAVE_USUARIO, JSON.stringify(u));
    setUsuario(u);
  }, []);

  return <Contexto.Provider value={{ usuario, entrar, salir }}>{children}</Contexto.Provider>;
}

export function useSesion() {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error("useSesion fuera de ProveedorSesion");
  return contexto;
}
