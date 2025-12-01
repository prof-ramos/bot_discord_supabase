# BOT_DISCORD_SUPABASE

## Objetivo
Centralizar documentos jurídicos para ingestão no Supabase e uso posterior em soluções de RAG (chatbots, bot do Discord, bot do Telegram, etc.).

## Escopo
- Upload e organização dos documentos.
- Acompanhamento do status e manutenção do banco de dados.
- Integrações com bots ficam fora deste repositório (serão tratadas em projetos próprios).

## Estrutura dos dados
- `raw/`: insumos originais, sem tratamento.
- `processed/`: arquivos prontos para envio ao Supabase.
- `logs/`: registros de carregamentos e eventuais erros.
- `reports/`: resumos ou métricas de ingestão (opcional).

## Convenções
- Manter nomes de arquivos descritivos, utilizando `snake_case`.
- Registrar no `logs/` qualquer ajuste manual ou falha ao subir documentos.
- Validar encoding em UTF-8 antes do processamento.

## Checklist de validação (novos documentos)
- Formato permitido (`pdf`, `docx`, `txt`); sem proteção por senha.
- Nome em `snake_case` contendo tema e data (ex.: `contrato_prestacao_2023-12-10.pdf`).
- Metadados obrigatórios: título, categoria, data de vigência, versão.
- Sem dados sensíveis ou PII fora do escopo autorizado.
- Texto legível (OCR aplicado quando necessário); encoding em UTF-8.
- Tamanho dentro do limite suportado pelo pipeline e pelo Supabase.
- Revisão jurídica mínima confirmada e registrada em `logs/`.

## Próximos passos
1. Configurar scripts de upload automatizado para o Supabase.
2. Documentar o fluxo de revisão e aprovação de novos insumos.
