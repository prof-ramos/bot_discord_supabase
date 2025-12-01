import streamlit as st
import pandas as pd
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
from ingest import ingest_documents

# Load env
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ Configure SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no .env")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Gestão de Documentos Jurídicos", layout="wide")

st.title("📚 Dashboard de Gestão de Documentos")

# Sidebar - Upload
st.sidebar.header("📤 Upload de Arquivos")
uploaded_files = st.sidebar.file_uploader("Arraste arquivos .md aqui", type=["md"], accept_multiple_files=True)

if uploaded_files:
    if st.sidebar.button("Processar Uploads"):
        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for uploaded_file in uploaded_files:
            file_path = upload_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            saved_files.append(file_path)

        st.sidebar.success(f"{len(saved_files)} arquivos salvos! Iniciando ingestão...")

        with st.spinner("Ingerindo documentos..."):
            # Run ingestion async
            result = asyncio.run(ingest_documents(str(upload_dir)))

            if "error" in result:
                st.error(f"Erro na ingestão: {result['error']}")
            else:
                st.success(f"Ingestão concluída! Sucesso: {result['succeeded']}, Falhas: {result['failed']}")

# Main Content - Stats & Tables
col1, col2, col3 = st.columns(3)

# Fetch stats via optimized RPC
try:
    stats = supabase.rpc("get_db_stats").execute().data[0]
    docs_count = stats.get('documents', 0)
    chunks_count = stats.get('embeddings', 0)
    runs_count = stats.get('ingestion_runs', 0)
except Exception as e:
    docs_count = chunks_count = runs_count = 0
    st.error(f"Erro ao buscar stats: {e}")

col1.metric("Documentos", docs_count)
col2.metric("Chunks (Vetores)", chunks_count)
col3.metric("Execuções de Ingestão", runs_count)

st.divider()

# Tabs
tab1, tab2 = st.tabs(["📄 Documentos", "⚙️ Logs de Ingestão"])

with tab1:
    st.subheader("Documentos Ingeridos")
    try:
        response = supabase.table("documents").select("*").order("created_at", desc=True).limit(50).execute()
        df_docs = pd.DataFrame(response.data)
        if not df_docs.empty:
            st.dataframe(
                df_docs[["title", "category", "status", "created_at", "slug"]],
                width='stretch',
                column_config={
                    "created_at": st.column_config.DatetimeColumn("Data Criação", format="DD/MM/YYYY HH:mm"),
                    "status": st.column_config.TextColumn("Status"),
                }
            )
        else:
            st.info("Nenhum documento encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar documentos: {e}")

with tab2:
    st.subheader("Histórico de Ingestão")
    try:
        response = supabase.table("ingestion_runs").select("*").order("started_at", desc=True).limit(20).execute()
        df_runs = pd.DataFrame(response.data)
        if not df_runs.empty:
            st.dataframe(
                df_runs[["id", "status", "started_at", "succeeded", "failed", "notes"]],
                width='stretch',
                column_config={
                    "started_at": st.column_config.DatetimeColumn("Início", format="DD/MM/YYYY HH:mm"),
                    "status": st.column_config.TextColumn("Status"),
                }
            )
        else:
            st.info("Nenhuma execução encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar logs: {e}")
