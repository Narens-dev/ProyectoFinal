import os, sys, requests, time, json
from dotenv import load_dotenv; load_dotenv()
sys.path.insert(0, 'src')
from ingesta import procesar_reglamento
from vectorstore import get_cliente_chroma, COLLECTION_NAME

PROGRESS_FILE = "vectorizar_progress.json"

def main():
    chunks = procesar_reglamento('data/Reglamento.pdf')
    cliente = get_cliente_chroma()
    api_key = os.environ.get('GEMINI_API_KEY')
    batch_size = 100
    
    # Cargar progreso previo si existe
    start_batch = 0
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            data = json.load(f)
            start_batch = data.get('last_batch', 0)
        print(f"Reanudando desde lote {start_batch}...")
        coleccion = cliente.get_collection(COLLECTION_NAME)
    else:
        if COLLECTION_NAME in [c.name for c in cliente.list_collections()]:
            cliente.delete_collection(COLLECTION_NAME)
        coleccion = cliente.create_collection(name=COLLECTION_NAME, metadata={'hnsw:space': 'cosine'})

    total_batches = (len(chunks) + batch_size - 1) // batch_size

    for batch_idx in range(start_batch, total_batches):
        i = batch_idx * batch_size
        lote = chunks[i:i+batch_size]
        req = {
            'requests': [
                {'model': 'models/gemini-embedding-2',
                 'content': {'parts': [{'text': c.texto}]},
                 'taskType': 'RETRIEVAL_DOCUMENT'}
                for c in lote
            ]
        }
        
        while True:
            resp = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={api_key}',
                json=req
            )
            if resp.status_code == 200:
                embs = [e['values'] for e in resp.json()['embeddings']]
                coleccion.add(
                    ids=[c.chunk_id for c in lote],
                    documents=[c.texto for c in lote],
                    metadatas=[{'pagina': c.pagina, 'capitulo': c.capitulo, 'articulo': c.articulo} for c in lote],
                    embeddings=embs
                )
                print(f"Lote {batch_idx+1}/{total_batches} completado. ({coleccion.count()} chunks en DB)")
                # Guardar progreso
                with open(PROGRESS_FILE, 'w') as f:
                    json.dump({'last_batch': batch_idx + 1}, f)
                break
            elif resp.status_code == 429:
                espera = 65
                try:
                    retry_info = resp.json()
                    # Intentar extraer el retryDelay de la respuesta
                    details = retry_info.get('error', {}).get('details', [])
                    for d in details:
                        if 'retryDelay' in str(d):
                            s = str(d.get('retryDelay', '65s')).replace('s','')
                            espera = int(s) + 5
                except:
                    pass
                print(f"Rate limit en lote {batch_idx+1}. Esperando {espera}s...")
                time.sleep(espera)
            else:
                print(f"Error inesperado: {resp.status_code} - {resp.text[:300]}")
                sys.exit(1)

    print(f"\n✅ Vectorización completa! {coleccion.count()} chunks indexados.")
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

if __name__ == '__main__':
    main()
