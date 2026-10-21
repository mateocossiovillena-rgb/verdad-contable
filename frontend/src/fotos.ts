/** Achica la foto en el celular antes de subirla (ahorra datos y espacio). */
export async function comprimirFoto(archivo: File, ladoMaximo = 1280, calidad = 0.7): Promise<string> {
  const url = URL.createObjectURL(archivo);
  try {
    const imagen = await new Promise<HTMLImageElement>((resolver, rechazar) => {
      const img = new Image();
      img.onload = () => resolver(img);
      img.onerror = () => rechazar(new Error("No se pudo leer la foto"));
      img.src = url;
    });
    const escala = Math.min(1, ladoMaximo / Math.max(imagen.width, imagen.height));
    const lienzo = document.createElement("canvas");
    lienzo.width = Math.round(imagen.width * escala);
    lienzo.height = Math.round(imagen.height * escala);
    lienzo.getContext("2d")!.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
    return lienzo.toDataURL("image/jpeg", calidad);
  } finally {
    URL.revokeObjectURL(url);
  }
}
