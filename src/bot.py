import os
import time
import hashlib
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import create_client, Client
from typing import Optional, List, Tuple
from functools import lru_cache

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, OPENAI_API_KEY, DISCORD_TOKEN]):
    print("❌ Defina todas as vars em .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, DISCORD_TOKEN")
    exit(1)

# Initialize clients with optimizations
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Discord setup
intents = discord.Intents.default()
intents.guilds = True
client = commands.Bot(command_prefix="!", intents=intents)

# ============================================================================
# CACHING LAYER
# ============================================================================

class EmbeddingCache:
    """Cache for query embeddings to reduce OpenAI API calls"""

    def __init__(self, max_size: int = 1000, ttl: int = 1800):
        self._cache = {}
        self._max_size = max_size
        self._ttl = ttl  # 30 minutes default

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from query text"""
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    async def get_or_compute_embedding(self, text: str) -> List[float]:
        """Get cached embedding or compute new one"""
        key = self._get_cache_key(text)

        # Check cache
        if key in self._cache:
            cached_value, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl:
                print(f"✅ Cache HIT for query")
                return cached_value

        # Compute new embedding
        print(f"⚡ Cache MISS - computing embedding")
        embedding_response = await openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = embedding_response.data[0].embedding

        # Store in cache
        self._cache[key] = (embedding, time.time())

        # Cleanup old entries if cache is too large
        if len(self._cache) > self._max_size:
            self._cleanup_cache()

        return embedding

    def _cleanup_cache(self):
        """Remove oldest 20% of cache entries"""
        sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
        cutoff = int(len(sorted_items) * 0.2)
        for key, _ in sorted_items[:cutoff]:
            del self._cache[key]
        print(f"🧹 Cache cleanup: removed {cutoff} old entries")

# Initialize cache
embedding_cache = EmbeddingCache()

# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def format_search_results(
    results: List[dict],
    query: str,
    include_metadata: bool = True
) -> str:
    """Format search results for Discord display"""

    if not results:
        return "❌ Nenhum documento relevante encontrado. Tente reformular!"

    formatted_results = []
    seen_documents = set()

    for i, r in enumerate(results):
        doc_id = r.get('document_id')

        # Skip duplicate documents
        if doc_id in seen_documents:
            continue
        seen_documents.add(doc_id)

        # Extract fields
        content_preview = r['content'][:400]
        similarity = r['similarity'] * 100
        doc_title = r.get('document_title', 'Sem título')
        doc_category = r.get('document_category', 'Geral')

        # Format result
        result_text = f"**{i + 1}. {doc_title}**\n"
        result_text += f"📂 Categoria: {doc_category}\n"
        result_text += f"📄 {content_preview}...\n"

        if include_metadata:
            result_text += f"*Similaridade: {similarity:.1f}%*"

        formatted_results.append(result_text)

        # Limit to 3 results to avoid Discord message length issues
        if len(formatted_results) >= 3:
            break

    header = f"📚 **Resultados para: \"{query}\"**\n\n"
    body = "\n\n".join(formatted_results)
    footer = "\n\n*Fonte: Banco de leis administrativas.*"

    response_text = header + body + footer

    # Discord has a 2000 char limit
    if len(response_text) > 2000:
        response_text = response_text[:1997] + "..."

    return response_text

# ============================================================================
# OPTIMIZED SEARCH FUNCTIONS
# ============================================================================

async def vector_search(
    query_embedding: List[float],
    match_threshold: float = 0.78,
    match_count: int = 5,
    filter_category: Optional[str] = None
) -> List[dict]:
    """
    Perform optimized vector search using the enhanced match_documents function

    Args:
        query_embedding: Query embedding vector
        match_threshold: Similarity threshold (0-1)
        match_count: Number of results to return
        filter_category: Optional category filter

    Returns:
        List of search results with document metadata
    """
    try:
        # Use optimized RPC function with filters
        response = supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_threshold": match_threshold,
            "match_count": match_count,
            "filter_status": "published",
            "filter_category": filter_category
        }).execute()

        return response.data

    except Exception as e:
        print(f"❌ Error in vector_search: {e}")
        return []

async def hybrid_search(
    query_text: str,
    query_embedding: List[float],
    match_threshold: float = 0.75,
    match_count: int = 5
) -> List[dict]:
    """
    Perform hybrid search (vector + full-text)

    Args:
        query_text: Original query text
        query_embedding: Query embedding vector
        match_threshold: Similarity threshold
        match_count: Number of results

    Returns:
        List of search results ranked by combined score
    """
    try:
        response = supabase.rpc("hybrid_search_documents", {
            "query_embedding": query_embedding,
            "query_text": query_text,
            "match_threshold": match_threshold,
            "match_count": match_count,
            "vector_weight": 0.7,
            "text_weight": 0.3
        }).execute()

        return response.data

    except Exception as e:
        print(f"❌ Error in hybrid_search: {e}")
        # Fallback to regular vector search
        return await vector_search(query_embedding, match_threshold, match_count)

# ============================================================================
# DISCORD BOT COMMANDS
# ============================================================================

@client.event
async def on_ready():
    print(f'✅ Bot {client.user} online!')
    try:
        synced = await client.tree.sync()
        print(f"✅ {len(synced)} comandos slash sincronizados!")
    except Exception as e:
        print(f"❌ Erro ao sincronizar comandos: {e}")

@client.tree.command(name="ask", description="Pergunte sobre documentos jurídicos")
@app_commands.describe(
    query="Sua pergunta",
    threshold="Limiar de similaridade (0.0-1.0, padrão: 0.78)",
    results="Número de resultados (1-10, padrão: 5)",
    category="Categoria para filtrar (opcional)"
)
async def ask(
    interaction: discord.Interaction,
    query: str,
    threshold: Optional[float] = 0.78,
    results: Optional[int] = 5,
    category: Optional[str] = None
):
    """Optimized ask command with caching and enhanced search"""
    await interaction.response.defer()

    start_time = time.time()
    print(f"🔍 Query: {query}")

    try:
        # Validate inputs
        threshold = max(0.0, min(1.0, threshold))
        results = max(1, min(10, results))

        # Get embedding (with caching)
        query_embedding = await embedding_cache.get_or_compute_embedding(query)

        # Perform vector search
        search_results = await vector_search(
            query_embedding=query_embedding,
            match_threshold=threshold,
            match_count=results,
            filter_category=category
        )

        # Format and send response
        response_text = format_search_results(search_results, query)

        elapsed_time = (time.time() - start_time) * 1000
        response_text += f"\n\n⚡ *Tempo de resposta: {elapsed_time:.0f}ms*"

        await interaction.followup.send(response_text)

        print(f"✅ Query processada em {elapsed_time:.0f}ms")

    except Exception as e:
        print(f"💥 Erro RAG: {e}")
        await interaction.followup.send("❌ Erro ao processar pergunta. Verifique logs.")

@client.tree.command(name="hybrid_search", description="Busca híbrida (vetorial + texto)")
@app_commands.describe(
    query="Sua pergunta",
    threshold="Limiar de similaridade (0.0-1.0, padrão: 0.75)"
)
async def hybrid_search_command(
    interaction: discord.Interaction,
    query: str,
    threshold: Optional[float] = 0.75
):
    """Hybrid search command combining vector and full-text search"""
    await interaction.response.defer()

    start_time = time.time()
    print(f"🔍 Hybrid search: {query}")

    try:
        # Validate threshold
        threshold = max(0.0, min(1.0, threshold))

        # Get embedding
        query_embedding = await embedding_cache.get_or_compute_embedding(query)

        # Perform hybrid search
        search_results = await hybrid_search(
            query_text=query,
            query_embedding=query_embedding,
            match_threshold=threshold,
            match_count=5
        )

        # Format response
        response_text = format_search_results(search_results, query)

        elapsed_time = (time.time() - start_time) * 1000
        response_text += f"\n\n⚡ *Busca híbrida - Tempo: {elapsed_time:.0f}ms*"

        await interaction.followup.send(response_text)

        print(f"✅ Hybrid search processada em {elapsed_time:.0f}ms")

    except Exception as e:
        print(f"💥 Erro hybrid search: {e}")
        await interaction.followup.send("❌ Erro ao processar busca híbrida.")

@client.tree.command(name="cache_stats", description="Estatísticas do cache de embeddings")
async def cache_stats(interaction: discord.Interaction):
    """Display cache statistics"""
    cache_size = len(embedding_cache._cache)
    max_size = embedding_cache._max_size
    usage_percent = (cache_size / max_size) * 100

    stats_text = f"📊 **Estatísticas do Cache**\n\n"
    stats_text += f"Entradas: {cache_size}/{max_size}\n"
    stats_text += f"Uso: {usage_percent:.1f}%\n"
    stats_text += f"TTL: {embedding_cache._ttl}s ({embedding_cache._ttl // 60}min)"

    await interaction.response.send_message(stats_text, ephemeral=True)

@client.tree.command(name="clear_cache", description="Limpa o cache de embeddings")
async def clear_cache(interaction: discord.Interaction):
    """Clear embedding cache"""
    old_size = len(embedding_cache._cache)
    embedding_cache._cache.clear()

    await interaction.response.send_message(
        f"🧹 Cache limpo! Removidas {old_size} entradas.",
        ephemeral=True
    )

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🚀 Starting optimized Discord bot...")
    print(f"📦 Cache: max_size={embedding_cache._max_size}, ttl={embedding_cache._ttl}s")
    client.run(DISCORD_TOKEN)
