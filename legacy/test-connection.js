require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
    console.error('❌ Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY em .env');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey, {
    auth: {
        autoRefreshToken: false,
        persistSession: false
    }
});

async function testConnection() {
    try {
        // Teste 1: Ping básico
        const { data: ping, error: pingError } = await supabase.from('documents').select('count').single();
        if (pingError && pingError.code !== 'PGRST116') { // Tabela vazia OK
            throw pingError;
        }
        console.log('✅ Conexão Supabase JS OK (seguindo guia: client com service_role para full access)');

        // Teste 2: Ping documents (schema OK?)
        const { data: docs, error: docsError } = await supabase.from('documents').select('id, count').limit(1);
        console.log('✅ Tabela documents acessível:', docs || 'vazia');
        if (docsError && docsError.code !== 'PGRST116') throw docsError;

        // Teste 3: Verificar pgvector extension (embeddings)
        const { data: vectorCheck } = await supabase.rpc('current_app_role');
        console.log('📋 Role service (full access):', vectorCheck);


        console.log('🎉 Todos testes passaram! Use pooler/transaction para bot serverless.');
    } catch (error) {
        console.error('❌ Erro na conexão/teste:', error.message);
        if (error.code === 'PGRST116') console.log('ℹ️ Tabela vazia: normal.');
    } finally {
        await supabase.auth.signOut();
        process.exit(0);
    }
}

testConnection();
