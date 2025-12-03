import asyncio
import os
import sys
from dotenv import load_dotenv

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.bot.rag.supabase_store import SupabaseStore

async def main():
    load_dotenv()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        print("❌ Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
        return

    print(f"🔄 Connecting to Supabase at {url}...")
    if "nhuwujcxzkbvpfxoqkqm" not in url:
        print("⚠️ WARNING: SUPABASE_URL does not match the expected project ID 'nhuwujcxzkbvpfxoqkqm'")
    else:
        print("✅ SUPABASE_URL matches project ID.")

    try:
        store = SupabaseStore(url, key)
        stats = await store.stats()
        print("✅ Connection successful!")
        print("📊 Database Stats:")
        print(f"   - Documents: {stats.get('documents', 'N/A')}")
        print(f"   - Chunks: {stats.get('chunks', 'N/A')}")

        print("\n🔍 Testing Search (RPC match_documents)...")
        # Dummy embedding (1536 dimensions)
        dummy_embedding = [0.0] * 1536
        try:
            results = await store.search(dummy_embedding, match_count=1, match_threshold=0.0)
            print(f"✅ Search successful! Found {len(results)} results (expected 0 for empty DB).")
        except Exception as e:
            print(f"❌ Search failed: {e}")
            print("   (This might indicate 'match_documents' function is missing or incompatible)")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
