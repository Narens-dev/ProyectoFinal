"""
Fase 2 — Embeddings y Vector Store
Vectoriza los chunks con Gemini y los persiste en ChromaDB.
"""

import os
import time
import chromadb
from google import genai
from google.genai import types
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

from ingesta import Chunk

load_dotenv()

VECTORSTORE_PATH = Path(__file__).parent.parent / "vectorstore"
COLLECTION_NAME = "reglamento_es"
BATCH_SIZE = 100  # Chroma local puede procesar lotes grandes instantáneamente


def get_genai_client():
    """Retorna cliente del nuevo SDK google-genai para uso de otras fases, aunque ya no se usa aquí."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró GEMINI_API_KEY en las variables de entorno.\n"
            "Crea un archivo .env con: GEMINI_API_KEY=tu_clave_aquí"
        )
    return genai.Client(api_key=api_key)


def get_cliente_chroma():
    """Retorna cliente ChromaDB persistente."""
    VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTORSTORE_PATH))


def get_embedding_function():
    from chromadb.utils import embedding_functions
    return embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")


def vectorstore_existe() -> bool:
    """Verifica si ya existe una vectorstore poblada."""
    cliente = get_cliente_chroma()
    colecciones = [c.name for c in cliente.list_collections()]
    if COLLECTION_NAME not in colecciones:
        return False
    col = cliente.get_collection(name=COLLECTION_NAME, embedding_function=get_embedding_function())
    return col.count() > 0


def construir_vectorstore(chunks: list[Chunk], forzar: bool = False) -> chromadb.Collection:
    """
    Vectoriza los chunks y los guarda en ChromaDB.
    Si ya existe y forzar=False, la reutiliza.
    """
    cliente = get_cliente_chroma()

    if vectorstore_existe() and not forzar:
        print("✓ Vector store existente encontrada. Cargando...")
        coleccion = cliente.get_collection(name=COLLECTION_NAME, embedding_function=get_embedding_function())
        print(f"  → {coleccion.count()} chunks cargados")
        return coleccion

    # Si existe pero queremos reconstruir, eliminar primero
    colecciones = [c.name for c in cliente.list_collections()]
    if COLLECTION_NAME in colecciones:
        cliente.delete_collection(COLLECTION_NAME)
        print("⚠ Vector store anterior eliminada.")

    coleccion = cliente.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # Similitud de coseno
        embedding_function=get_embedding_function()
    )

    print(f"\nVectorizando {len(chunks)} chunks localmente con ChromaDB...")
    print(f"(Esto tomará unos pocos segundos, sin límites de API)\n")

    # Procesar en lotes para respetar rate limits de la API
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Vectorizando lotes"):
        lote = chunks[i : i + BATCH_SIZE]

        ids = [c.chunk_id for c in lote]
        textos = [c.texto for c in lote]
        metadatos = [
            {
                "pagina": c.pagina,
                "capitulo": c.capitulo,
                "articulo": c.articulo,
            }
            for c in lote
        ]

        coleccion.add(
            ids=ids,
            documents=textos,
            metadatas=metadatos
        )

    print(f"\n✓ Vector store construida: {coleccion.count()} chunks indexados")
    print(f"  Guardada en: {VECTORSTORE_PATH}")
    return coleccion


def buscar(
    coleccion: chromadb.Collection,
    consulta: str,
    top_k: int = 4,
    umbral_distancia: float = 1.5,
) -> list[dict]:
    """
    Búsqueda semántica: retorna los top_k chunks más similares.
    Filtra resultados con distancia mayor al umbral (muy poco relevantes).
    """
    resultados = coleccion.query(
        query_texts=[consulta],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks_recuperados = []
    for doc, meta, dist in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        if dist <= umbral_distancia:
            chunks_recuperados.append(
                {
                    "texto": doc,
                    "pagina": meta.get("pagina", "?"),
                    "capitulo": meta.get("capitulo", ""),
                    "articulo": meta.get("articulo", ""),
                    "distancia": round(dist, 4),
                    "relevancia": round((1 - dist / 2) * 100, 1),  # % aproximado
                }
            )

    return chunks_recuperados


def cargar_coleccion() -> chromadb.Collection:
    """Carga la colección existente (para uso desde la app)."""
    if not vectorstore_existe():
        raise RuntimeError(
            "La vector store no existe aún.\n"
            "Ejecuta primero: python src/vectorizar.py data/Reglamento.pdf"
        )
    cliente = get_cliente_chroma()
    return cliente.get_collection(name=COLLECTION_NAME, embedding_function=get_embedding_function())


if __name__ == "__main__":
    # Prueba de búsqueda semántica
    print("Probando búsqueda semántica...")
    coleccion = cargar_coleccion()

    consultas_prueba = [
        "perder la materia",
        "cuántas materias puedo cancelar",
        "qué pasa si repito una materia",
    ]

    for consulta in consultas_prueba:
        print(f"\n🔍 Consulta: '{consulta}'")
        resultados = buscar(coleccion, consulta, top_k=2)
        for i, r in enumerate(resultados, 1):
            print(f"  [{i}] Relevancia: {r['relevancia']}% | {r['articulo']} | p.{r['pagina']}")
            print(f"      {r['texto'][:150]}...")
