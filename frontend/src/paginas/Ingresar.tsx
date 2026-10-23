import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useSesion } from "../sesion";
import type { Usuario } from "../tipos";
import { Boton, Campo, Entrada, MensajeError, Tarjeta } from "../componentes/ui";

interface RespuestaSesion {
  token: string;
  usuario: Usuario;
}

function Portada({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-6 p-6">
      <div className="text-center">
        <img src="/icono.svg" alt="" className="mx-auto h-16 w-16" />
        <h1 className="mt-4 text-2xl font-semibold tracking-tight text-stone-900">Verdad Contable</h1>
        <p className="mt-1 text-stone-600">Cuánto gastaste de verdad y cómo va tu obra.</p>
      </div>
      {children}
    </div>
  );
}

export function Ingresar() {
  const { usuario, entrar } = useSesion();
  const navegar = useNavigate();
  const [datos, setDatos] = useState({ usuario: "", clave: "" });
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to="/" replace />;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const r = await api<RespuestaSesion>("/api/sesion/ingreso", "POST", datos);
      entrar(r.token, r.usuario);
      navegar("/", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Portada>
      <Tarjeta>
        <form onSubmit={enviar} className="space-y-4">
          <Campo etiqueta="Correo o número de celular">
            <Entrada
              value={datos.usuario}
              onChange={(e) => setDatos({ ...datos, usuario: e.target.value })}
              autoComplete="username"
              required
            />
          </Campo>
          <Campo etiqueta="Clave o PIN">
            <Entrada
              type="password"
              value={datos.clave}
              onChange={(e) => setDatos({ ...datos, clave: e.target.value })}
              autoComplete="current-password"
              required
            />
          </Campo>
          <MensajeError error={error} />
          <Boton type="submit" grande className="w-full" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </Boton>
        </form>
      </Tarjeta>
      <p className="text-center text-sm text-stone-600">
        ¿Eres constructor y no tienes cuenta?{" "}
        <Link to="/registro" className="inline-flex min-h-10 items-center font-semibold text-marca-700 underline-offset-2 hover:underline">
          Crear cuenta
        </Link>
      </p>
    </Portada>
  );
}

export function Registro() {
  const { usuario, entrar } = useSesion();
  const navegar = useNavigate();
  const [datos, setDatos] = useState({ nombre: "", correo: "", clave: "" });
  const [error, setError] = useState<unknown>(null);
  const [enviando, setEnviando] = useState(false);

  if (usuario) return <Navigate to="/" replace />;

  async function enviar(e: FormEvent) {
    e.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      const r = await api<RespuestaSesion>("/api/sesion/registro", "POST", datos);
      entrar(r.token, r.usuario);
      navegar("/obras/nueva", { replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Portada>
      <Tarjeta>
        <form onSubmit={enviar} className="space-y-4">
          <Campo etiqueta="Tu nombre o el de tu empresa">
            <Entrada value={datos.nombre} onChange={(e) => setDatos({ ...datos, nombre: e.target.value })} required />
          </Campo>
          <Campo etiqueta="Correo">
            <Entrada
              type="email"
              value={datos.correo}
              onChange={(e) => setDatos({ ...datos, correo: e.target.value })}
              autoComplete="email"
              required
            />
          </Campo>
          <Campo etiqueta="Clave" ayuda="Mínimo 8 caracteres">
            <Entrada
              type="password"
              minLength={8}
              value={datos.clave}
              onChange={(e) => setDatos({ ...datos, clave: e.target.value })}
              autoComplete="new-password"
              required
            />
          </Campo>
          <MensajeError error={error} />
          <Boton type="submit" grande className="w-full" disabled={enviando}>
            {enviando ? "Creando…" : "Crear cuenta"}
          </Boton>
        </form>
      </Tarjeta>
      <p className="text-center text-sm text-stone-600">
        ¿Ya tienes cuenta?{" "}
        <Link to="/ingresar" className="inline-flex min-h-10 items-center font-semibold text-marca-700 underline-offset-2 hover:underline">
          Entrar
        </Link>
      </p>
    </Portada>
  );
}
