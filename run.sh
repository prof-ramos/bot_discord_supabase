#!/bin/bash

set -e

case "$1" in
  bot)
    echo "🚀 Iniciando Bot Discord (RAG via Supabase)..."
    uv run src/bot/main.py
    ;;
  ingest)
    echo "🚀 Iniciando ingestão de documentos..."
    uv run src/ingest.py
    ;;
  dashboard)
    echo "🚀 Iniciando Dashboard Streamlit..."
    streamlit run src/dashboard.py
    ;;
  main)
    echo "🚀 Rodando main.py..."
    uv run main.py
    ;;
  *)
    echo "Uso: ./run.sh [bot|ingest|dashboard|main]"
    echo ""
    echo "Opções:"
    echo "  bot       - Roda o bot Discord (src/bot.py)"
    echo "  ingest    - Ingestão de documentos (src/ingest.py)"
    echo "  dashboard - Dashboard Streamlit (src/dashboard.py)"
    echo "  main      - Script principal (main.py)"
    exit 1
    ;;
esac
