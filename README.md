# ProyectoFinal
Naren Santiago Rojas Sanchez
David Santiago Prieto Beltran

# Guía de Instalación y Ejecución: Asistente RAG del Reglamento Estudiantil

¡Bienvenido! Esta guía te explicará paso a paso cómo instalar, configurar y ejecutar el Asistente de Inteligencia Artificial (RAG) basado en el Reglamento Estudiantil en tu propia computadora.

> [!IMPORTANT]
> Antes de empezar, asegúrate de tener una conexión a internet estable, ya que el sistema necesitará descargar algunas librerías de Inteligencia Artificial (modelos locales y de Google).

## 🛠️ Requisitos Previos

1. **Python 3.10 o superior**: Asegúrate de tener Python instalado en tu computadora. Puedes descargarlo desde [python.org](https://www.python.org/downloads/).
   * *Nota para Windows:* Durante la instalación de Python, asegúrate de marcar la casilla **"Add Python to PATH"** en el instalador.
2. **Git (Opcional pero recomendado)**: Para clonar el repositorio fácilmente.

---

## 🚀 Paso 1: Preparar la Carpeta del Proyecto

Si te enviaron el proyecto comprimido en un archivo ZIP:
1. Descomprime el archivo en una carpeta de tu elección (por ejemplo: `Documentos/rag_reglamento`).
2. Abre la terminal (Símbolo del sistema o PowerShell en Windows, o Terminal en Mac/Linux) y navega hasta esa carpeta.

Si usas Git:
```bash
git clone <URL_DEL_REPOSITORIO>
cd rag_reglamento_v2
```

---

## 📦 Paso 2: Crear un Entorno Virtual

El entorno virtual (venv) aísla las librerías de este proyecto para que no interfieran con otros programas en tu computadora.

1. **Crear el entorno virtual:**
   ```bash
   python -m venv venv
   ```
   *(Esto creará una carpeta llamada `venv` dentro de tu proyecto. Puede tardar unos segundos).*

2. **Activar el entorno virtual:**
   * **En Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **En Windows (CMD clásico):**
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   * **En Mac / Linux:**
     ```bash
     source venv/bin/activate
     ```

> [!TIP]
> Sabrás que el entorno virtual está activado porque verás el prefijo `(venv)` al inicio de la línea de tu terminal. ¡Debes activar este entorno cada vez que vayas a trabajar en el proyecto!

---

## ⚙️ Paso 3: Instalar las Dependencias

Con el entorno virtual activado, vamos a instalar todas las librerías necesarias (como Streamlit, ChromaDB, Sentence-Transformers y Google GenAI).

1. Ejecuta el siguiente comando en la terminal:
   ```bash
   pip install -r requirements.txt
   ```
2. Espera a que termine. Descargará varias librerías pesadas (especialmente para los embeddings de IA locales y procesamiento de visión).

---

## 🔑 Paso 4: Configurar la Clave de la API (Gemini)

El asistente utiliza la IA de Google (Gemini) para leer los artículos y generar la respuesta final.

1. En la carpeta raíz del proyecto, busca el archivo `.env` (si no existe, crea un archivo de texto llamado exactamente `.env`).
2. Entra a [Google AI Studio](https://aistudio.google.com/app/apikey) con tu cuenta de Google y genera una API Key gratuita.
3. Abre el archivo `.env` con el Bloc de notas o cualquier editor de texto y pega tu clave con este formato exacto (sin espacios alrededor del signo igual):
   ```env
   GEMINI_API_KEY=AIzaSyTuClaveAqui...
   ```

---

## 🧠 Paso 5: (Opcional) Construir la Base de Datos Vectorial

> [!NOTE]
> Si el proyecto ya incluye la carpeta `chroma_db` con los archivos adentro, puedes saltarte este paso.

Si cambiaste el PDF del reglamento (ubicado en `data/Reglamento.pdf`) o es la primera vez que vas a crear la base de datos de memoria semántica de la IA, debes ejecutar el proceso de vectorización:

1. Ejecuta en la terminal:
   ```bash
   python src/vectorizar.py data/Reglamento.pdf --forzar
   ```
2. Verás una barra de progreso. La primera vez tardará unos minutos porque descargará el modelo de lenguaje local (`paraphrase-multilingual-MiniLM-L12-v2`) para leer el reglamento.
3. Al finalizar, te dirá cuántos "fragmentos" guardó en ChromaDB.

---

## 🏃 Paso 6: ¡Ejecutar la Aplicación!

¡Ya está todo listo! Ahora levantaremos la interfaz gráfica.

1. Asegúrate de tener el entorno virtual activado `(venv)` y ejecuta:
   ```bash
   streamlit run app.py
   ```
2. Si Windows te pide permisos de Firewall, dale a "Permitir".
3. Se abrirá automáticamente una pestaña en tu navegador web apuntando a `http://localhost:8501`.

> [!TIP]
> **¿La aplicación se queda cargando eternamente o lanza un error rojo de "Streamlit Watcher" la primera vez?**
> A veces Streamlit tarda en reconocer los modelos la primera vez que se ejecuta. Si crashea o se queda cargando, simplemente presiona `Ctrl + C` en tu terminal para detenerlo y vuelve a ejecutar `streamlit run app.py`.

### 💡 Uso General del Sistema
- Escribe tu pregunta en el chat de la parte inferior.
- El sistema analizará tu pregunta, buscará los artículos más parecidos matemáticamente en la base de datos local y le enviará el contexto a Gemini para darte la respuesta exacta con su fuente.
- En la barra lateral izquierda podrás ver el historial de desempeño (métricas de recuperación).
