import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

tables = ['documents', 'document_versions', 'ingestion_runs', 'ingestion_items', 'topics', 'document_topics', 'embeddings']

print("=== Row Counts ===")
for table in tables:
    try:
        response = supabase.table(table).select('count', count='exact').execute()
        count = response.count
        print(f'{table}: {count} rows')
    except Exception as e:
        print(f'{table}: error - {str(e)}')

print("\n=== Recent Queries Example (documents) ===")
try:
    response = supabase.table("documents").select("*").order("created_at", desc=True).limit(5).execute()
    print("Sample documents:", response.data)
except Exception as e:
    print(f"Error:", e)
