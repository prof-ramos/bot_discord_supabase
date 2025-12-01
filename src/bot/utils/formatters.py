from typing import List, Dict


def format_results_for_discord(results: List[Dict], query: str) -> str:
    if not results:
        return f"❌ Nada encontrado para: \"{query}\""

    parts = [f"📚 **Resultados para \"{query}\"**"]
    for i, r in enumerate(results[:3]):
        preview = (r.get("chunk") or "")[:300]
        sim = r.get("similarity", 0) * 100
        parts.append(f"**{i+1}.** {preview}...\n*Similaridade: {sim:.1f}%*")

    body = "\n\n".join(parts)
    if len(body) > 1900:
        body = body[:1897] + "..."
    return body
