"""
Fase 4 — Interfaz Gráfica con Streamlit
RAG sobre el reglamento estudiantil.
"""

import sys
from pathlib import Path
import streamlit as st

# Asegurar imports locales
sys.path.insert(0, str(Path(__file__).parent / "src"))

from vectorstore import cargar_coleccion, vectorstore_existe
from rag import configurar_gemini, generar_respuesta  # configurar_gemini retorna genai.Client

# ──────────────────────────────────────────────
# Configuración de la página
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Asistente del Reglamento",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Burbuja del asistente */
.msg-asistente {
    background: #f0f4ff;
    border-left: 4px solid #4f6ef7;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    color: #1a1a2e;
}
/* Burbuja del usuario */
.msg-usuario {
    background: #e8f5e9;
    border-left: 4px solid #43a047;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    color: #1a1a2e;
    text-align: right;
}
/* Tarjeta de fuente */
.fuente-card {
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 10px 14px;
    margin: 6px 0;
    font-size: 0.85em;
}
.relevancia-alta { border-left: 4px solid #43a047; }
.relevancia-media { border-left: 4px solid #fb8c00; }
.relevancia-baja { border-left: 4px solid #e53935; }
</style>
""", unsafe_allow_html=True)


# ──────────────────────────────────────────────
# Estado de sesión
# ──────────────────────────────────────────────

if "historial" not in st.session_state:
    st.session_state.historial = []  # [{rol, contenido, fuentes}]
if "coleccion" not in st.session_state:
    st.session_state.coleccion = None
if "modelo" not in st.session_state:
    st.session_state.modelo = None
if "ultima_fuentes" not in st.session_state:
    st.session_state.ultima_fuentes = []


# ──────────────────────────────────────────────
# Inicialización (cacheada para no recargar en cada interacción)
# ──────────────────────────────────────────────

@st.cache_resource(show_spinner="Cargando vector store...")
def inicializar_sistema():
    if not vectorstore_existe():
        return None, None
    coleccion = cargar_coleccion()
    modelo = configurar_gemini()
    return coleccion, modelo


# ──────────────────────────────────────────────
# Sidebar — Controles y configuración
# ──────────────────────────────────────────────

with st.sidebar:
    st.title("⚙️ Configuración")

    top_k = st.slider(
        "Fragmentos a recuperar (top-k)",
        min_value=1, max_value=8, value=4,
        help="Más fragmentos = más contexto, pero respuestas más lentas",
    )

    st.divider()
    st.markdown("**Sobre el sistema**")
    st.markdown("""
    - 🧠 LLM: Gemini 1.5 Flash
    - 📐 Embeddings: text-embedding-004
    - 🗄️ Vector Store: ChromaDB (coseno)
    - 🌡️ Temperatura: 0.1 (conservador)
    """)

    st.divider()
    if st.button("🗑️ Limpiar conversación", use_container_width=True):
        st.session_state.historial = []
        st.session_state.ultima_fuentes = []
        st.rerun()

    st.divider()
    st.markdown("**Fuentes consultadas** (última respuesta)")

    if st.session_state.ultima_fuentes:
        for fuente in st.session_state.ultima_fuentes:
            rel = fuente["relevancia"]
            clase = (
                "relevancia-alta" if rel >= 70
                else "relevancia-media" if rel >= 40
                else "relevancia-baja"
            )
            st.markdown(f"""
            <div class="fuente-card {clase}">
                <b>{fuente['articulo'] or 'Sin artículo'}</b><br>
                {fuente['capitulo'][:60] if fuente['capitulo'] else ''}<br>
                <small>Página {fuente['pagina']} · Relevancia {rel}%</small>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Ver fragmento"):
                st.caption(fuente["texto"][:500] + ("..." if len(fuente["texto"]) > 500 else ""))
    else:
        st.caption("Las fuentes aparecerán aquí después de tu primera pregunta.")


# ──────────────────────────────────────────────
# Panel principal — Chat
# ──────────────────────────────────────────────

st.title("📖 Asistente del Reglamento Estudiantil")
st.caption("Haz preguntas sobre el reglamento. Solo respondo con información del documento oficial.")

# Verificar sistema
coleccion, modelo = inicializar_sistema()

if coleccion is None:
    st.error("""
    ⚠️ La vector store no está construida aún.

    **Pasos para activar el sistema:**
    1. Coloca tu PDF en la carpeta `data/` con el nombre `reglamento.pdf`
    2. Ejecuta en la terminal:
       ```
       python src/vectorizar.py data/reglamento.pdf
       ```
    3. Recarga esta página
    """)
    st.stop()

# Mostrar historial
for mensaje in st.session_state.historial:
    with st.chat_message(mensaje["rol"], avatar="🎓" if mensaje["rol"] == "user" else "🤖"):
        st.markdown(mensaje["contenido"])


# Input del usuario
if consulta := st.chat_input("Escribe tu pregunta sobre el reglamento..."):

    # Mostrar mensaje del usuario
    with st.chat_message("user", avatar="🎓"):
        st.markdown(consulta)

    st.session_state.historial.append({"rol": "user", "contenido": consulta})

    # Generar respuesta
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Buscando en el reglamento..."):
            resultado = generar_respuesta(
                cliente=modelo,
                coleccion=coleccion,
                consulta=consulta,
                top_k=top_k,
            )

        respuesta = resultado["respuesta"]
        fuentes = resultado["fuentes"]

        st.markdown(respuesta)

        # Mostrar indicador de fuentes bajo la respuesta
        if fuentes:
            st.caption(f"📚 Basado en {len(fuentes)} fragmento(s) del reglamento")
        else:
            st.caption("⚠️ No se encontraron fragmentos relevantes en el reglamento")

    # Guardar en historial
    st.session_state.historial.append({
        "rol": "assistant",
        "contenido": respuesta,
    })
    st.session_state.ultima_fuentes = fuentes

    # Actualizar sidebar con nuevas fuentes
    st.rerun()
