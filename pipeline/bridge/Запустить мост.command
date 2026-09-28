#!/bin/bash
cd "$(dirname "$0")"
PY="$HOME/Library/Application Support/MAOS-bridge/venv/bin/python"
if [ ! -x "$PY" ]; then echo "Среда не установлена — сначала «Установить мост.command»"; read -n1; exit 1; fi
echo "Мост MAOS работает. Не закрывай это окно, пока идёт монтаж (можно свернуть)."
exec "$PY" runner.py
