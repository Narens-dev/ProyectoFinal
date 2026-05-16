"""
Fase 1 — Ingesta del reglamento
Carga el PDF, limpia el texto y lo divide en chunks con metadatos.
"""

import re
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass
from tqdm import tqdm


@dataclass
class Chunk:
    texto: str
    pagina: int
    capitulo: str
    articulo: str
    chunk_id: str


def cargar_pdf(ruta: str) -> list[dict]:
    """Lee el PDF página a página y retorna lista de {pagina, texto}."""
    doc = fitz.open(ruta)
    paginas = []
    for num, pagina in enumerate(doc, start=1):
        texto = pagina.get_text("text")
        texto = limpiar_texto(texto)
        if texto.strip():
            paginas.append({"pagina": num, "texto": texto})
    doc.close()
    print(f"✓ PDF cargado: {len(paginas)} páginas con contenido")
    return paginas


def limpiar_texto(texto: str) -> str:
    """Elimina ruido tipográfico del PDF."""
    # Normalizar saltos de línea múltiples
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    # Eliminar guiones de separación silábica al final de línea
    texto = re.sub(r"-\n(\w)", r"\1", texto)
    # Eliminar espacios redundantes
    texto = re.sub(r"[ \t]+", " ", texto)
    # Eliminar números de página solitarios
    texto = re.sub(r"^\s*\d+\s*$", "", texto, flags=re.MULTILINE)
    return texto.strip()


def detectar_capitulo(texto: str, capitulo_actual: str) -> str:
    """Detecta si el texto contiene un encabezado de capítulo."""
    patrones = [
        r"(?i)(cap[íi]tulo\s+[IVXLCDM\d]+[^.\n]*)",
        r"(?i)(t[íi]tulo\s+[IVXLCDM\d]+[^.\n]*)",
        r"(?i)(secci[oó]n\s+[IVXLCDM\d]+[^.\n]*)",
    ]
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            return match.group(1).strip()
    return capitulo_actual


def detectar_articulo(texto: str, articulo_actual: str) -> str:
    """Detecta si el texto contiene un número de artículo."""
    patrones = [
        r"(?i)(art[íi]culo\s+\d+[°º]?\.?)",
        r"(?i)(art\.\s*\d+[°º]?\.?)",
        r"(?i)(§\s*\d+)",
    ]
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            return match.group(1).strip()
    return articulo_actual


def dividir_en_chunks(
    paginas: list[dict],
    tamano_chunk: int = 600,
    solapamiento: int = 100,
) -> list[Chunk]:
    """
    Divide el texto en chunks con solapamiento.
    Preserva metadatos de capítulo y artículo.
    """
    texto_completo = ""
    mapa_posiciones = []  # (inicio, fin, pagina)

    for pagina in paginas:
        inicio = len(texto_completo)
        texto_completo += pagina["texto"] + "\n\n"
        fin = len(texto_completo)
        mapa_posiciones.append((inicio, fin, pagina["pagina"]))

    chunks = []
    capitulo_actual = "Sin capítulo"
    articulo_actual = "Sin artículo"
    idx = 0

    print("Generando chunks...")
    with tqdm(total=len(texto_completo), unit="chars") as pbar:
        while idx < len(texto_completo):
            fin = min(idx + tamano_chunk, len(texto_completo))

            # Intentar cortar en punto natural (párrafo o punto)
            if fin < len(texto_completo):
                corte = texto_completo.rfind("\n\n", idx, fin)
                if corte == -1:
                    corte = texto_completo.rfind(". ", idx, fin)
                if corte != -1:
                    fin = corte + 1

            fragmento = texto_completo[idx:fin].strip()

            if len(fragmento) < 50:
                idx = fin
                pbar.update(fin - idx)
                continue

            # Detectar página del chunk
            pagina_chunk = 1
            for inicio_p, fin_p, num_p in mapa_posiciones:
                if inicio_p <= idx < fin_p:
                    pagina_chunk = num_p
                    break

            # Actualizar metadatos estructurales
            capitulo_actual = detectar_capitulo(fragmento, capitulo_actual)
            articulo_actual = detectar_articulo(fragmento, articulo_actual)

            chunk_id = f"chunk_{len(chunks):04d}_p{pagina_chunk}"

            chunks.append(
                Chunk(
                    texto=fragmento,
                    pagina=pagina_chunk,
                    capitulo=capitulo_actual,
                    articulo=articulo_actual,
                    chunk_id=chunk_id,
                )
            )

            avance = fin - solapamiento
            # Garantizar un avance mínimo para evitar micro-chunks superpuestos infinitamente
            avance_minimo = idx + max(50, (fin - idx) // 2)
            avance = max(avance, avance_minimo)
            
            pbar.update(avance - idx)
            idx = avance

    print(f"✓ Total chunks generados: {len(chunks)}")
    return chunks


def procesar_reglamento(ruta_pdf: str, tamano_chunk: int = 600, solapamiento: int = 100) -> list[Chunk]:
    """Pipeline completo de ingesta."""
    ruta = Path(ruta_pdf)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el PDF en: {ruta_pdf}")

    print(f"\n{'='*50}")
    print(f"Procesando: {ruta.name}")
    print(f"{'='*50}")

    paginas = cargar_pdf(str(ruta))
    chunks = dividir_en_chunks(paginas, tamano_chunk, solapamiento)

    # Resumen
    caps = {c.capitulo for c in chunks}
    arts = {c.articulo for c in chunks if c.articulo != "Sin artículo"}
    print(f"\n📊 Resumen de ingesta:")
    print(f"   Chunks:    {len(chunks)}")
    print(f"   Capítulos: {len(caps)}")
    print(f"   Artículos: {len(arts)}")

    return chunks


if __name__ == "__main__":
    # Prueba rápida
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else "data/reglamento.pdf"
    chunks = procesar_reglamento(ruta)
    print(f"\nEjemplo de chunk #0:")
    print(f"  ID:       {chunks[0].chunk_id}")
    print(f"  Página:   {chunks[0].pagina}")
    print(f"  Capítulo: {chunks[0].capitulo}")
    print(f"  Artículo: {chunks[0].articulo}")
    print(f"  Texto:    {chunks[0].texto[:200]}...")
