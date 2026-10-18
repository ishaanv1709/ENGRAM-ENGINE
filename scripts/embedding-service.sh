#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/collective/logs
pidfile=data/collective/embedding.pid
case "${1:-start}" in
  run)
    echo "$$" >"$pidfile"
    exec .venv-collective-linux/bin/python -m collective.embedding_server
    ;;
  start)
    if curl --fail --silent --max-time 3 http://127.0.0.1:8091/health >/dev/null; then
      echo 'Embedding service is already running.'
      exit 0
    fi
    if [[ -f "$pidfile" ]]; then
      pid=$(cat "$pidfile")
      if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$(readlink "/proc/$pid/cwd" 2>/dev/null || true)" = "$PWD" ]] &&
        tr '\0' ' ' <"/proc/$pid/cmdline" | grep -q 'collective.embedding_server'; then
        echo 'Embedding service is still starting.'
        exit 0
      fi
    fi
    nohup .venv-collective-linux/bin/python -m collective.embedding_server >data/collective/logs/embeddings.log 2>&1 </dev/null &
    echo "$!" >"$pidfile"
    ;;
  stop)
    if [[ -f "$pidfile" ]]; then
      pid=$(cat "$pidfile")
      if [[ "$pid" =~ ^[0-9]+$ ]] && [[ "$(readlink "/proc/$pid/cwd" 2>/dev/null || true)" = "$PWD" ]] &&
        tr '\0' ' ' <"/proc/$pid/cmdline" | grep -q 'collective.embedding_server'; then
        kill "$pid"
      fi
    fi
    ;;
  *) echo 'Use start or stop'; exit 1 ;;
esac
