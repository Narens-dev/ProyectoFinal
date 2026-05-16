"""
Script de línea de comandos para procesar el PDF y construir la vector store.
Uso: python src/vectorizar.py data/reglamento.pdf [--forzar]
"""

import sys
import io
import argparse
from pathlib import Path

# Forzar UTF-8 en la consola de Windows para soportar emojis y símbolos unicode
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Asegurar que src/ esté en el path
sys.path.insert(0, str(Path(__file__).parent))

from ingesta import procesar_reglamento
from vectorstore import construir_vectorstore, vectorstore_existe


def main():
    parser = argparse.ArgumentParser(
        description="Procesa el reglamento PDF y construye la vector store"
    )
    parser.add_argument("pdf", help="Ruta al PDF del reglamento")
    parser.add_argument(
        "--forzar",
        action="store_true",
        help="Reconstruir la vector store aunque ya exista",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=600,
        help="Tamaño de cada chunk en caracteres (default: 600)",
    )
    parser.add_argument(
        "--solapamiento",
        type=int,
        default=100,
        help="Solapamiento entre chunks (default: 100)",
    )
    args = parser.parse_args()

    if vectorstore_existe() and not args.forzar:
        print("✓ Ya existe una vector store. Usa --forzar para reconstruirla.")
        print("  Puedes lanzar la app directamente con: streamlit run app.py")
        return

    # Fase 1: Ingesta
    chunks = procesar_reglamento(
        args.pdf,
        tamano_chunk=args.chunk_size,
        solapamiento=args.solapamiento,
    )

    # Fase 2: Vectorización
    construir_vectorstore(chunks, forzar=args.forzar)

    print("\n✅ Proceso completado.")
    print("   Lanza la app con: streamlit run app.py")


if __name__ == "__main__":
    main()
