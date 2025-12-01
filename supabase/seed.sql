-- Seed example (optional). Safe to run multiple times.
INSERT INTO public.rag_documents (id, title, doc_type, source_path, metadata)
VALUES
  ('11111111-1111-1111-1111-111111111111', 'Exemplo', 'seed', 'seed', '{"source":"seed"}')
ON CONFLICT DO NOTHING;

INSERT INTO public.rag_chunks (document_id, chunk, embedding, metadata)
SELECT
  '11111111-1111-1111-1111-111111111111',
  'Olá! Este é um chunk de exemplo.',
  ARRAY(SELECT 0.0::float4 FROM generate_series(1,1536)),
  '{"seed":true}'::jsonb
ON CONFLICT DO NOTHING;
