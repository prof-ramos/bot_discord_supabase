#!/bin/bash

# Script para iniciar e manter o bot ativo com sistema de logs e proteção contra crash loops
# start_bot.sh

# Diretório de logs
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/bot.log"
ERROR_LOG="$LOG_DIR/bot_error.log"
PID_FILE="bot.pid"

# Cria o diretório de logs se não existir
mkdir -p "$LOG_DIR"

# Configurações de proteção contra crash loops
RESTART_DELAY=5
MAX_FAILURES=5
FAILURE_WINDOW=60
RESTART_COUNT=0
FIRST_FAILURE_TIME=0

# Função para registrar logs com timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Função para lidar com o encerramento do script
cleanup() {
    log "🛑 Recebido sinal para encerrar o bot..."
    if [ -f "$PID_FILE" ]; then
        BOT_PID=$(cat "$PID_FILE")
        if kill -0 "$BOT_PID" 2>/dev/null; then
            log "🛑 Parando o bot (PID: $BOT_PID)..."
            kill -TERM "$BOT_PID" 2>/dev/null
            # Espera até 10 segundos pelo encerramento elegante
            for i in {1..10}; do
                if ! kill -0 "$BOT_PID" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            # Se ainda estiver rodando, termina com sinal KILL
            if kill -0 "$BOT_PID" 2>/dev/null; then
                log "⚠️ Bot ainda ativo após 10 segundos, enviando sinal KILL..."
                kill -KILL "$BOT_PID" 2>/dev/null
            fi
        fi
        rm -f "$PID_FILE"
    fi
    log "✅ Script de gerenciamento do bot encerrado."
    exit 0
}

# Configura o tratamento de sinais
trap cleanup SIGTERM SIGINT SIGQUIT

log "🔄 Iniciando e mantendo o bot Discord RAG ativo..."

# Loop para manter o bot ativo
while true; do
    log "🚀 Iniciando Bot Discord (RAG via Supabase)..."

    # Executa o bot e captura o PID
    uv run main.py >>"$LOG_FILE" 2>>"$ERROR_LOG" &
    BOT_PID=$!

    # Salva o PID do bot em arquivo para controle
    echo "$BOT_PID" > "$PID_FILE"

    log "🤖 Bot iniciado com PID: $BOT_PID"

    # Espera o processo terminar
    wait $BOT_PID
    BOT_STATUS=$?

    log "⚠️ Bot encerrado com código: $BOT_STATUS"

    # Remove o arquivo PID após o encerramento
    rm -f "$PID_FILE"

    CURRENT_TIME=$(date +%s)

    # Se foi primeira falha nesta janela, registra
    if [ $RESTART_COUNT -eq 0 ]; then
        FIRST_FAILURE_TIME=$CURRENT_TIME
    fi

    ((RESTART_COUNT++))

    # Se excedeu limite de falhas na janela, para!
    TIME_DIFF=$((CURRENT_TIME - FIRST_FAILURE_TIME))
    if [ $RESTART_COUNT -ge $MAX_FAILURES ] && [ $TIME_DIFF -lt $FAILURE_WINDOW ]; then
        log "❌ Limite de reinicializações alcançado ($RESTART_COUNT falhas em $TIME_DIFF segundos)! Encerrando para evitar crash loop."
        exit 1
    fi

    # Reset counter se saiu da janela
    if [ $TIME_DIFF -ge $FAILURE_WINDOW ]; then
        RESTART_COUNT=0
    fi

    log "🔄 Reiniciando em $RESTART_DELAY segundos... (tentativa $RESTART_COUNT/$MAX_FAILURES)"
    sleep $RESTART_DELAY
done
