import os, requests
from dotenv import load_dotenv; load_dotenv()
req = {'requests': [{'model': 'models/gemini-embedding-2', 'content': {'parts': [{'text': 'hello'}]}}]}
api_key = os.environ.get('GEMINI_API_KEY')
res = requests.post(f'https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={api_key}', json=req)
print(res.status_code)
print(res.json())
