#!/bin/bash
# Установка моста MAOS на macOS. Python-среда лежит ЛОКАЛЬНО (не в iCloud):
#   ~/Library/Application Support/MAOS-bridge/{venv,python}
set -e
cd "$(dirname "$0")"
BR="$(pwd)"
ENVROOT="$HOME/Library/Application Support/MAOS-bridge"
mkdir -p "$ENVROOT"
VENV="$ENVROOT/venv"
echo "== Мост MAOS: скрипты в $BR"
echo "== Среда Python: $VENV (локально, без iCloud)"
DEPS="imageio-ffmpeg onnx-asr onnxruntime opencv-python-headless Pillow numpy huggingface_hub"

# старая среда внутри iCloud-папки от первой установки — убираем, чтобы не синхронизировалась
rm -rf "$BR/.venv" "$BR/.python"

pick=""
for c in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 \
         /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 \
         /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  [ -x "$c" ] || continue
  v=$("$c" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null) || continue
  if [ "$v" -ge 311 ]; then pick="$c"; break; fi
done

if [ -x "$VENV/bin/python" ]; then
  echo "== Среда уже есть — обновляю пакеты"
  if [ -n "$pick" ]; then "$VENV/bin/python" -m pip install -q -U $DEPS
  else UV="$(/usr/bin/python3 -c 'import site,os;print(os.path.join(site.USER_BASE,"bin","uv"))')"; "$UV" pip install -q --python "$VENV/bin/python" -U $DEPS; fi
elif [ -n "$pick" ]; then
  echo "== Нашёл Python: $pick"
  "$pick" -m venv "$VENV"
  "$VENV/bin/python" -m pip install -q -U pip
  "$VENV/bin/python" -m pip install -q $DEPS
else
  echo "== Подходящего Python нет — ставлю uv (с PyPI) и отдельный Python 3.12"
  SYS=/usr/bin/python3
  "$SYS" -m pip install -q --user uv
  UV="$("$SYS" -c 'import site,os;print(os.path.join(site.USER_BASE,"bin","uv"))')"
  export UV_PYTHON_INSTALL_DIR="$ENVROOT/python"
  "$UV" venv --python 3.12 "$VENV"
  "$UV" pip install -q --python "$VENV/bin/python" $DEPS
fi

echo "== Модели"
bash "$BR/setup_models.sh"

echo "== Самопроверка"
"$VENV/bin/python" selftest.py
echo "== Готово. Теперь дважды кликни «Запустить мост.command»."
