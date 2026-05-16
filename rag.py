"""
Fase 3 — Pipeline RAG
Recupera contexto relevante e inyecta en Gemini para generar la respuesta.
"""

import os
import chromadb
from google import genai
from google.genai import types
from dotenv import load_dotenv

from vectorstore import buscar

load_dotenv()

# ──────────────────────────────────────────────
# Configuración del LLM
# ──────────────────────────────────────────────

MODEL_NAME = "gemini-2.5-flash-lite"

SYSTEM_PROMPT = """Eres un asistente experto en el reglamento estudiantil de la universidad.
Tu única fuente de información es el contexto del reglamento que se te proporciona en cada consulta.

REGLAS ESTRICTAS que SIEMPRE debes seguir:
1. Responde ÚNICAMENTE con base en el contexto proporcionado.
2. Si la respuesta NO está en el contexto, responde EXACTAMENTE:
   "No encuentro esa información en el reglamento."
   No intentes adivinar, inferir ni completar con conocimiento propio.
3. Cuando encuentres la respuesta, cita el artículo o sección relevante.
4. Responde en español, de forma clara y directa.
5. No saludes ni hagas comentarios innecesarios; ve directo a la respuesta.
6. Si el contexto es parcialmente relevante, responde solo lo que puedas confirmar
   y aclara que el resto no está en el reglamento."""


def configurar_gemini() -> genai.Client:
    """Inicializa el cliente de Gemini con el nuevo SDK."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró GEMINI_API_KEY.\n"
            "Agrega tu clave en el archivo .env"
        )
    return genai.Client(api_key=api_key)


def construir_prompt_aumentado(consulta: str, chunks_recuperados: list[dict]) -> str:
    """Construye el prompt con el contexto inyectado."""
    if not chunks_recuperados:
        contexto_texto = "[No se encontraron fragmentos relevantes en el reglamento]"
    else:
        secciones = []
        for i, chunk in enumerate(chunks_recuperados, 1):
            seccion = f"""--- Fragmento {i} ---
Artículo: {chunk['articulo']}
Capítulo: {chunk['capitulo']}
Página: {chunk['pagina']}
Contenido:
{chunk['texto']}"""
            secciones.append(seccion)
        contexto_texto = "\n\n".join(secciones)

    return f"""CONTEXTO DEL REGLAMENTO:
{contexto_texto}

PREGUNTA DEL ESTUDIANTE:
{consulta}

RESPUESTA:"""


def generar_respuesta(
    cliente: genai.Client,
    coleccion: chromadb.Collection,
    consulta: str,
    top_k: int = 4,
) -> dict:
    """
    Pipeline RAG completo:
    1. Búsqueda semántica
    2. Construcción del prompt aumentado
    3. Generación con Gemini
    4. Retorna respuesta + fuentes
    """
    # Paso 1: Recuperación semántica
    chunks = buscar(coleccion, consulta, top_k=top_k)

    # Paso 2: Prompt aumentado
    prompt = construir_prompt_aumentado(consulta, chunks)

    # Paso 3: Generación con el nuevo SDK
    respuesta = cliente.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            top_p=0.8,
            max_output_tokens=1024,
        ),
    )

    texto_respuesta = respuesta.text.strip()

    return {
        "respuesta": texto_respuesta,
        "fuentes": chunks,
        "consulta": consulta,
        "prompt_usado": prompt,
        "chunks_encontrados": len(chunks),
    }


if __name__ == "__main__":
    from vectorstore import cargar_coleccion

    print("Iniciando prueba del pipeline RAG...\n")
    coleccion = cargar_coleccion()
    cliente = configurar_gemini()

    preguntas_prueba = [
        "¿Cuántas materias puedo perder antes de ser expulsado?",
        "¿Cómo puedo cancelar una materia?",
        "¿Qué es la nota mínima para aprobar?",
        "¿Cuál es el precio de una hamburguesa en la cafetería?",  # Pregunta trampa
    ]

    for pregunta in preguntas_prueba:
        print(f"{'='*60}")
        print(f"❓ {pregunta}")
        resultado = generar_respuesta(cliente, coleccion, pregunta)
        print(f"🤖 {resultado['respuesta']}")
        print(f"📚 Fuentes usadas: {resultado['chunks_encontrados']} fragmentos")
        if resultado['fuentes']:
            for f in resultado['fuentes']:
                print(f"   • {f['articulo']} (p.{f['pagina']}) — relevancia {f['relevancia']}%")
        print()
