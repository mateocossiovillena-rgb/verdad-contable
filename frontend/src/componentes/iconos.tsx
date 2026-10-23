import type { ReactNode, SVGProps } from "react";

/** Íconos de trazo fino, todos del mismo grosor. Heredan el color del texto. */
type Props = SVGProps<SVGSVGElement> & { tamano?: number };

function Icono({ tamano = 20, children, ...props }: Props & { children: ReactNode }) {
  return (
    <svg
      width={tamano}
      height={tamano}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      {children}
    </svg>
  );
}

export const IconoObras = (p: Props) => (
  <Icono {...p}>
    <path d="M3 21h18" />
    <path d="M5 21V10l7-5 7 5v11" />
    <path d="M9 21v-6h6v6" />
  </Icono>
);

export const IconoCampana = (p: Props) => (
  <Icono {...p}>
    <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
  </Icono>
);

export const IconoCuenta = (p: Props) => (
  <Icono {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21a8 8 0 0 1 16 0" />
  </Icono>
);

export const IconoAtras = (p: Props) => (
  <Icono {...p}>
    <path d="m15 18-6-6 6-6" />
  </Icono>
);

export const IconoAdelante = (p: Props) => (
  <Icono {...p}>
    <path d="m9 18 6-6-6-6" />
  </Icono>
);

export const IconoMas = (p: Props) => (
  <Icono {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icono>
);

export const IconoBillete = (p: Props) => (
  <Icono {...p}>
    <rect x="2" y="6" width="20" height="12" rx="2" />
    <circle cx="12" cy="12" r="2.5" />
    <path d="M6 12h.01M18 12h.01" />
  </Icono>
);

export const IconoLadrillos = (p: Props) => (
  <Icono {...p}>
    <rect x="3" y="4" width="18" height="16" rx="1.5" />
    <path d="M3 9.33h18M3 14.67h18M9 4v5.33M15 9.33v5.34M9 14.67V20" />
  </Icono>
);

export const IconoCierre = (p: Props) => (
  <Icono {...p}>
    <rect x="5" y="4" width="14" height="17" rx="2" />
    <path d="M9 4V3h6v1" />
    <path d="m9 13 2 2 4-4" />
  </Icono>
);

export const IconoCamara = (p: Props) => (
  <Icono {...p}>
    <path d="M14.5 4h-5L7.5 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3.5z" />
    <circle cx="12" cy="13" r="3.5" />
  </Icono>
);

export const IconoLapiz = (p: Props) => (
  <Icono {...p}>
    <path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" />
  </Icono>
);

export const IconoBasura = (p: Props) => (
  <Icono {...p}>
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
  </Icono>
);

export const IconoArriba = (p: Props) => (
  <Icono {...p}>
    <path d="m18 15-6-6-6 6" />
  </Icono>
);

export const IconoAbajo = (p: Props) => (
  <Icono {...p}>
    <path d="m6 9 6 6 6-6" />
  </Icono>
);

export const IconoCerrar = (p: Props) => (
  <Icono {...p}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Icono>
);

export const IconoCheck = (p: Props) => (
  <Icono {...p}>
    <path d="M20 6 9 17l-5-5" />
  </Icono>
);

export const IconoAlerta = (p: Props) => (
  <Icono {...p}>
    <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0" />
    <path d="M12 9v4M12 17h.01" />
  </Icono>
);

export const IconoSinSenal = (p: Props) => (
  <Icono {...p}>
    <path d="M12 20h.01M8.5 16.4a5 5 0 0 1 7 0M2 8.8a15 15 0 0 1 4.2-2.6M22 8.8a15 15 0 0 0-11.3-3.7M5 12.9a10 10 0 0 1 5-2.7M19 12.9a10 10 0 0 0-1.4-1.1" />
    <path d="m2 2 20 20" />
  </Icono>
);

export const IconoDescargar = (p: Props) => (
  <Icono {...p}>
    <path d="M12 3v12M7 10l5 5 5-5M5 21h14" />
  </Icono>
);

export const IconoSalir = (p: Props) => (
  <Icono {...p}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" />
  </Icono>
);

export const IconoRecibo = (p: Props) => (
  <Icono {...p}>
    <path d="M5 3v18l2.5-1.5L10 21l2-1.5 2 1.5 2.5-1.5L19 21V3l-2.5 1.5L14 3l-2 1.5L10 3 7.5 4.5z" />
    <path d="M9 9h6M9 13h6" />
  </Icono>
);

export const IconoLista = (p: Props) => (
  <Icono {...p}>
    <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
  </Icono>
);
