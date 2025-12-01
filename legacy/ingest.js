require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const OpenAI = require('openai');
const fs = require('fs-extra');
const crypto = require('crypto');
const path = require('path');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const openaiApiKey = process.env.OPENAI_API_KEY;

if (!supabaseUrl || !supabaseServiceKey || !openaiApiKey) {
    console.error('❌ Defina SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY e OPENAI_API_KEY em .env');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);
const openai = new OpenAI({ apiKey: openaiApiKey });

async function ingestDocuments() {
    try {
        // 1. Iniciar run de ingestão
        const { data: run, error: runError } = await supabase
            .from('ingestion_runs')
            .insert({ notes: 'Ingestão inicial data/d_administrativo' })
            .select()
            .single();
        if (runError) throw runError;
        console.log('🚀 Run iniciada:', run.id);

        const dataDir = path.join(__dirname, 'data');
        const mdFiles = await getMdFilesRecursive(dataDir);

        let succeeded = 0;
        let failed = 0;

        for (const filePath of mdFiles) {
            const relPath = path.relative(dataDir, filePath);
            const filename = path.basename(filePath, '.md');
            const content = await fs.readFile(filePath, 'utf8');
            const size = Buffer.byteLength(content, 'utf8');
            const checksum = crypto.createHash('sha256').update(content).digest('hex');

            const slug = filename.toLowerCase().replace(/[^a-z0-9]/g, '_');
            const title = filename.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const category = 'd_administrativo';

            try {
                // Inserir ingestion_item
                const { data: item, error: itemError } = await supabase
                    .from('ingestion_items')
                    .insert({ run_id: run.id, source_path: relPath, checksum, size_bytes: size })
                    .select()
                    .single();
                if (itemError) throw itemError;

                // Inserir document
                const { data: doc, error: docError } = await supabase
                    .from('documents')
                    .insert({
                        title,
                        slug,
                        category,
                        source_path: relPath,
                        checksum,
                        size_bytes: size,
                        status: 'pending',
                        tags: ['lei', 'administrativo'] // default
                    })
                    .select()
                    .single();
                if (docError) throw docError;

                // Inserir version
                const { error: verError } = await supabase
                    .from('document_versions')
                    .insert({
                        document_id: doc.id,
                        version_label: '1.0',
                        checksum,
                        storage_key: `data/${relPath}`
                    });
                if (verError) throw verError;

                // Chunk e embed
                const chunks = chunkText(content, 500); // ~500 palavras
                for (let i = 0; i < chunks.length; i++) {
                    const chunkContent = chunks[i];
                    const chunkId = `chunk_${i}`;

                    const embeddingResponse = await openai.embeddings.create({
                        model: 'text-embedding-ada-002',
                        input: chunkContent.slice(0, 8191) // limit
                    });
                    const embedding = embeddingResponse.data[0].embedding;

                    const { error: embError } = await supabase
                        .from('embeddings')
                        .insert({
                            document_id: doc.id,
                            chunk_id: chunkId,
                            content: chunkContent,
                            embedding
                        });
                    if (embError) throw embError;
                }

                // Atualizar item e doc
                await supabase
                    .from('ingestion_items')
                    .update({ status: 'processed', processed_at: new Date().toISOString() })
                    .eq('id', item.id);

                await supabase
                    .from('documents')
                    .update({ status: 'published', published_at: new Date().toISOString().split('T')[0] })
                    .eq('id', doc.id);

                succeeded++;
                console.log(`✅ ${relPath} ingerido (${chunks.length} chunks)`);

            } catch (fileError) {
                console.error(`❌ Erro em ${relPath}:`, fileError.message);
                await supabase
                    .from('ingestion_items')
                    .update({ status: 'failed', error_message: fileError.message })
                    .eq('source_path', relPath)
                    .eq('run_id', run.id);
                failed++;
            }
        }

        // Finalizar run
        await supabase
            .from('ingestion_runs')
            .update({
                status: 'succeeded',
                finished_at: new Date().toISOString(),
                total_files: mdFiles.length,
                succeeded,
                failed
            })
            .eq('id', run.id);

        console.log(`🎉 Ingestão concluída: ${succeeded}/${mdFiles.length} sucesso(s)`);

    } catch (error) {
        console.error('💥 Erro geral:', error);
        process.exit(1);
    }
}

function getMdFilesRecursive(dir) {
    const files = [];
    const items = fs.readdirSync(dir);
    for (const item of items) {
        const fullPath = path.join(dir, item);
        const stat = fs.statSync(fullPath);
        if (stat.isDirectory()) {
            files.push(...getMdFilesRecursive(fullPath));
        } else if (path.extname(item) === '.md') {
            files.push(fullPath);
        }
    }
    return files;
}

function chunkText(text, maxWords) {
    const sentences = text.split(/[.!?]+/).map(s => s.trim()).filter(s => s);
    const chunks = [];
    let currentChunk = '';
    for (const sentence of sentences) {
        if ((currentChunk.split(' ').length + sentence.split(' ').length) > maxWords) {
            if (currentChunk) chunks.push(currentChunk);
            currentChunk = sentence + '. ';
        } else {
            currentChunk += sentence + '. ';
        }
    }
    if (currentChunk) chunks.push(currentChunk);
    return chunks;
}

ingestDocuments();
