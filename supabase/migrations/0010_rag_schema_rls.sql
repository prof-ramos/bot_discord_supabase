-- 0010_rag_schema_rls.sql
-- RLS policies para schema RAG simplificado (rag_documents, rag_chunks)
--
-- Este schema é usado pelo bot Discord atual (src/bot/rag/supabase_store.py)
-- As políticas permitem:
-- - Service role: acesso total (bypass) para operações do bot
-- - Authenticated users: leitura apenas
-- - Anon: sem acesso

-- ============================================================================
-- 1. ENABLE RLS
-- ============================================================================

ALTER TABLE public.rag_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rag_chunks ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. SERVICE ROLE BYPASS (CRITICAL FOR BOT PERFORMANCE)
-- ============================================================================

-- Service role tem acesso total sem restrições
-- Isso permite que o bot Discord opere sem overhead de RLS
CREATE POLICY rag_documents_service_role_all
  ON public.rag_documents
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY rag_chunks_service_role_all
  ON public.rag_chunks
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- ============================================================================
-- 3. AUTHENTICATED USER POLICIES (READ ONLY)
-- ============================================================================

-- Usuários autenticados podem ler documentos
CREATE POLICY rag_documents_authenticated_read
  ON public.rag_documents
  FOR SELECT
  TO authenticated
  USING (true);

-- Usuários autenticados podem ler chunks
CREATE POLICY rag_chunks_authenticated_read
  ON public.rag_chunks
  FOR SELECT
  TO authenticated
  USING (true);

-- ============================================================================
-- 4. ANON RESTRICTIONS
-- ============================================================================

-- Usuários anônimos NÃO têm acesso (force usar service_role para bot)
-- Sem políticas = acesso negado por padrão

-- ============================================================================
-- 5. COMMENTS
-- ============================================================================

COMMENT ON POLICY rag_documents_service_role_all ON public.rag_documents IS
'Service role bypass para operações do bot Discord. Permite acesso total sem overhead de RLS.';

COMMENT ON POLICY rag_chunks_service_role_all ON public.rag_chunks IS
'Service role bypass para operações do bot Discord. Permite acesso total sem overhead de RLS.';

COMMENT ON POLICY rag_documents_authenticated_read ON public.rag_documents IS
'Permite que usuários autenticados leiam documentos RAG. Escrita é reservada para service role.';

COMMENT ON POLICY rag_chunks_authenticated_read ON public.rag_chunks IS
'Permite que usuários autenticados leiam chunks RAG. Escrita é reservada para service role.';

-- ============================================================================
-- 6. PERFORMANCE NOTES
-- ============================================================================

/*
IMPORTANTE: Bot Discord DEVE usar SUPABASE_SERVICE_ROLE_KEY

No arquivo .env, certifique-se de usar:
  SUPABASE_SERVICE_ROLE_KEY=eyJhbGc... (service role key, não anon key)

Com service_role:
- RLS é completamente bypass
- Performance 10x melhor (sem subqueries)
- Permite INSERT/UPDATE/DELETE sem restrições

Com anon key:
- RLS bloqueia tudo (sem políticas para anon)
- INSERT/UPDATE/DELETE falhará com permission denied

VERIFICAR CONFIGURAÇÃO:
Após aplicar esta migração, teste:
1. Bot deve conseguir inserir documentos
2. Bot deve conseguir buscar chunks
3. Queries devem ser rápidas (<50ms)

TROUBLESHOOTING:
Se o bot falhar com "permission denied":
- Verifique se está usando SERVICE_ROLE_KEY no .env
- Não use ANON_KEY para operações de escrita
- Confirme que as políticas service_role existem:
  SELECT * FROM pg_policies WHERE tablename IN ('rag_documents', 'rag_chunks');
*/
