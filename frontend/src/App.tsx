import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ErrorApi } from "./api";
import { ProveedorSesion, useSesion } from "./sesion";
import { Ingresar, Registro } from "./paginas/Ingresar";
import { Inicio, MisObras } from "./paginas/Obras";
import { CierreDia, Hoy } from "./paginas/Hoy";
import { NuevoAvance, NuevoGasto } from "./paginas/Registrar";
import { DetalleObra } from "./paginas/DetalleObra";
import { FormObra } from "./paginas/FormObra";
import { Partidas } from "./paginas/Partidas";
import { Gastos } from "./paginas/Gastos";
import { Alertas } from "./paginas/Alertas";
import { Cuenta } from "./paginas/Cuenta";
import { EstimarObra } from "./paginas/EstimarObra";

const cliente = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // Un 4xx no se arregla reintentando; un corte de señal sí.
      retry: (intentos, error) => !(error instanceof ErrorApi && error.estado < 500) && intentos < 2,
    },
  },
});

function ConSesion({ children }: { children: ReactNode }) {
  const { usuario } = useSesion();
  if (!usuario) return <Navigate to="/ingresar" replace />;
  return <>{children}</>;
}

function SoloDueno({ children }: { children: ReactNode }) {
  const { usuario } = useSesion();
  if (!usuario) return <Navigate to="/ingresar" replace />;
  if (usuario.rol !== "dueno") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={cliente}>
      <ProveedorSesion>
        <BrowserRouter>
          <Routes>
            <Route path="/ingresar" element={<Ingresar />} />
            <Route path="/registro" element={<Registro />} />

            <Route path="/" element={<ConSesion><Inicio /></ConSesion>} />
            <Route path="/obras" element={<ConSesion><MisObras /></ConSesion>} />
            <Route path="/obras/:obraId/hoy" element={<ConSesion><Hoy /></ConSesion>} />
            <Route path="/obras/:obraId/gasto" element={<ConSesion><NuevoGasto /></ConSesion>} />
            <Route path="/obras/:obraId/avance" element={<ConSesion><NuevoAvance /></ConSesion>} />
            <Route path="/obras/:obraId/cierre" element={<ConSesion><CierreDia /></ConSesion>} />
            <Route path="/cuenta" element={<ConSesion><Cuenta /></ConSesion>} />

            <Route path="/obras/nueva" element={<SoloDueno><FormObra /></SoloDueno>} />
            <Route path="/obras/:obraId" element={<SoloDueno><DetalleObra /></SoloDueno>} />
            <Route path="/obras/:obraId/editar" element={<SoloDueno><FormObra /></SoloDueno>} />
            <Route path="/obras/:obraId/partidas" element={<SoloDueno><Partidas /></SoloDueno>} />
            <Route path="/obras/:obraId/gastos" element={<SoloDueno><Gastos /></SoloDueno>} />
            <Route path="/obras/:obraId/estimar" element={<SoloDueno><EstimarObra /></SoloDueno>} />
            <Route path="/alertas" element={<SoloDueno><Alertas /></SoloDueno>} />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ProveedorSesion>
    </QueryClientProvider>
  );
}
