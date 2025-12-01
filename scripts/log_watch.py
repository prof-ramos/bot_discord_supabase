"""
Watcher simples para acompanhar logs do bot e do autoteste em tempo real.

Detecta:
- linhas com "ERROR"
- linhas com contagem de resultados > 0

Escreve eventos em logs/monitor_events.log com timestamp.
Uso:
  PYTHONPATH=. uv run scripts/log_watch.py
"""

import time
from datetime import datetime
from pathlib import Path

LOG_FILES = [
    Path("logs/bot.log"),
    Path("/tmp/auto_ask_tester.log"),
]

EVENT_LOG = Path("logs/monitor_events.log")


def now():
    return datetime.utcnow().isoformat() + "Z"


def tail_files():
    # Abre arquivos e posiciona no fim para só ler novos eventos
    handlers = {}
    for path in LOG_FILES:
        try:
            f = path.open("r", encoding="utf-8")
            f.seek(0, 2)
            handlers[path] = f
        except FileNotFoundError:
            continue
    return handlers


def parse_line(line: str):
    line_lower = line.lower()

    if "error" in line_lower or "traceback" in line_lower:
        return f"ERROR detected: {line.strip()}"

    # Padrões de resultado
    if "results_count=" in line_lower:
        try:
            # exemplo: results_count=3
            for token in line.replace(",", " ").split():
                if token.startswith("results_count="):
                    val = int(token.split("=", 1)[1])
                    if val > 0:
                        return f"RESULTS>0 (results_count): {val} | {line.strip()}"
        except Exception:
            pass

    if "results=" in line_lower:
        try:
            # exemplo: results=3
            for token in line.replace(",", " ").split():
                if token.startswith("results="):
                    val = int(token.split("=", 1)[1])
                    if val > 0:
                        return f"RESULTS>0 (results): {val} | {line.strip()}"
        except Exception:
            pass

    return None


def main():
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with EVENT_LOG.open("a", encoding="utf-8") as evt:
        evt.write(f"{now()} monitor start\n")

    handlers = tail_files()
    if not handlers:
        print("Nenhum arquivo de log encontrado para monitorar.")
        return

    while True:
        for path, f in list(handlers.items()):
            line = f.readline()
            if not line:
                continue

            event = parse_line(line)
            if event:
                entry = f"{now()} {event}\n"
                with EVENT_LOG.open("a", encoding="utf-8") as evt:
                    evt.write(entry)
                print(entry, end="")

        # Pequeno sleep para evitar busy-wait
        time.sleep(0.5)


if __name__ == "__main__":
    main()
