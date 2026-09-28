#!/bin/bash
# Скачивает модель распознавания речи GigaAM v3 (RNNT, int8, ~225 МБ) в pipeline/models/gigaam
# с Hugging Face (istupakov/gigaam-v3-onnx). В git модель не хранится — лимит GitHub 100 МБ на файл.
set -e
cd "$(dirname "$0")/.."
PY="$HOME/Library/Application Support/MAOS-bridge/venv/bin/python"
[ -x "$PY" ] || PY=python3
if [ -f models/gigaam/v3_rnnt_encoder.int8.onnx ]; then echo "== GigaAM уже на месте"; exit 0; fi
echo "== Скачиваю GigaAM v3 (~225 МБ)…"
"$PY" -m pip install -q huggingface_hub >/dev/null 2>&1 || true
"$PY" - <<'PY'
import onnx_asr
onnx_asr.load_model("gigaam-v3-rnnt", "models/gigaam", quantization="int8")
print("== GigaAM готов: models/gigaam")
PY
