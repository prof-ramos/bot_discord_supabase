#!/bin/bash

# Script para desligar o bot Discord RAG
# stop_bot.sh

# Diretório de logs
PID_FILE="bot.pid"

echo "🛑 Parando o bot Discord RAG..."

# Tenta ler o PID do arquivo
if [ -f "$PID_FILE" ]; then
    BOT_PID=$(cat "$PID_FILE")

    if kill -0 "$BOT_PID" 2>/dev/null; then
        # Shutdown flow:
        # 1. Send TERM signal to request graceful shutdown
        # 2. Wait up to 10s, polling every 0.5s
        # 3. If still alive, send KILL signal
        # 4. Only remove PID file if process is confirmed dead
        echo "🛑 Enviando sinal TERM para o bot (PID: $BOT_PID)..."
        kill -TERM "$BOT_PID" 2>/dev/null

        # Espera até 10 segundos pelo encerramento elegante
        for i in {1..20}; do  # Espera até 10 segundos com intervalos de 0.5s
            if ! kill -0 "$BOT_PID" 2>/dev/null; then
                echo "✅ Bot encerrado com sucesso."
                rm -f "$PID_FILE"
                exit 0
            fi
            sleep 0.5
        done

        # Se ainda estiver rodando, termina com sinal KILL
        echo "⚠️ Bot ainda ativo após 10 segundos, enviando sinal KILL..."
        kill -KILL "$BOT_PID" 2>/dev/null

        # Verifica se realmente terminou antes de remover PID file
        if ! kill -0 "$BOT_PID" 2>/dev/null; then
            echo "✅ Bot encerrado com sucesso (forçado)."
            rm -f "$PID_FILE"
        else
            echo "❌ Falha ao encerrar o bot. PID file mantido para investigação."
            echo "Falha ao encerrar PID $BOT_PID em $(date)" >> "$PID_FILE.failed"
        fi
    else
        echo "ℹ️ Processo do bot (PID: $BOT_PID) não encontrado."
        rm -f "$PID_FILE"
    fi
else
    # Se não encontrar o arquivo PID, tenta encontrar processos de forma alternativa
    echo "ℹ️ Arquivo PID não encontrado, procurando processos manualmente..."
    # Corrige o padrão de busca para evitar sobreposição com diferentes comandos
    # Busca por processos python rodando main.py ou src.bot.main
    BOT_PIDS=$(pgrep -f "python.*(main\.py|src\.bot\.main)")

    if [ -z "$BOT_PIDS" ]; then
        echo "ℹ️ Nenhum processo do bot encontrado."
    else
        echo "🛑 Encerrando processos do bot (PIDs: $BOT_PIDS)..."
        for pid in $BOT_PIDS; do
            if [ -n "$pid" ]; then
                kill -TERM "$pid" 2>/dev/null
                if [ $? -eq 0 ]; then
                    echo "✅ Processo $pid encerrado com sucesso."
                else
                    echo "⚠️ Falha ao encerrar processo $pid, tentando força..."
                    kill -KILL "$pid" 2>/dev/null
                    if [ $? -eq 0 ]; then
                        echo "✅ Processo $pid encerrado com KILL."
                    else
                        echo "❌ Falha ao encerrar processo $pid."
                    fi
                fi
            fi
        done
    fi
fi

echo "✅ Operação de desligamento concluída."
