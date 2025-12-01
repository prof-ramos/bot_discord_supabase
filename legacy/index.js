require('dotenv').config();
const { Client, GatewayIntentBits, SlashCommandBuilder, REST, Routes } = require('discord.js');
const { createClient } = require('@supabase/supabase-js');
const OpenAI = require('openai');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const openaiApiKey = process.env.OPENAI_API_KEY;
const discordToken = process.env.DISCORD_TOKEN;

if (!supabaseUrl || !supabaseServiceKey || !openaiApiKey || !discordToken) {
    console.error('❌ Defina todas as vars em .env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, OPENAI_API_KEY, DISCORD_TOKEN');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);
const openai = new OpenAI({ apiKey: openaiApiKey });

const client = new Client({ intents: [GatewayIntentBits.Guilds] });

// Comandos slash
const commands = [
    new SlashCommandBuilder()
        .setName('ask')
        .setDescription('Pergunte sobre documentos jurídicos')
        .addStringOption(option =>
            option.setName('query')
                .setDescription('Sua pergunta')
                .setRequired(true)
        )
].map(command => command.toJSON());

const rest = new REST({ version: '10' }).setToken(discordToken);

client.once('ready', async () => {
    console.log(`✅ Bot ${client.user.tag} online!`);

    // Registrar comandos globalmente (ou por guild)
    try {
        console.log('📝 Registrando comandos slash...');
        await rest.put(
            Routes.applicationCommands(client.user.id),
            { body: commands }
        );
        console.log('✅ Comandos registrados!');
    } catch (error) {
        console.error('❌ Erro ao registrar comandos:', error);
    }
});

client.on('interactionCreate', async interaction => {
    if (!interaction.isChatInputCommand()) return;

    if (interaction.commandName === 'ask') {
        await interaction.deferReply();

        const query = interaction.options.getString('query');
        console.log(`🔍 Query: ${query}`);

        try {
            // Embed query
            const queryEmbeddingResponse = await openai.embeddings.create({
                model: 'text-embedding-ada-002',
                input: query
            });
            const queryEmbedding = queryEmbeddingResponse.data[0].embedding;

            // Busca vetorial (cosine distance via <=> pgvector)
            const { data: results, error } = await supabase.rpc('match_documents', {
                query_embedding: queryEmbedding,
                match_threshold: 0.78, // similaridade mín. (1 - distance)
                match_count: 5
            });

            if (error || !results || results.length === 0) {
                return interaction.editReply('❌ Nenhum documento relevante encontrado. Tente reformular!');
            }

            // Format response
            const response = results.map((r, i) => `**${i + 1}.** ${r.content.substring(0, 500)}...\n*(Similaridade: ${(r.similarity * 100).toFixed(1)}%)*`).join('\n\n');
            await interaction.editReply(`📚 **Resultados para: "${query}"**\n\n${response}\n\n*Fonte: Banco de leis administrativas.*`);

        } catch (error) {
            console.error('💥 Erro RAG:', error);
            await interaction.editReply('❌ Erro ao processar pergunta. Verifique logs.');
        }
    }
});

client.login(discordToken);

// RPC para match_documents (deve existir no Supabase ou criar via migration)
console.log('⚙️ Para busca vetorial, crie esta RPC no Supabase SQL Editor:\n');
console.log(`
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id bigint,
  document_id uuid,
  chunk_id text,
  content text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  select
    embeddings.id,
    embeddings.document_id,
    embeddings.chunk_id,
    embeddings.content,
    1 - (embeddings.embedding <=> query_embedding) as similarity
  from public.embeddings
  where 1 - (embeddings.embedding <=> query_embedding) > match_threshold
  order by embeddings.embedding <=> query_embedding
  limit match_count;
$$;
`);
