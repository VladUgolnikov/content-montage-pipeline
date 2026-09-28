#!/bin/bash
# render_remotion.sh <props.json> <out.mp4> <draft|final> <base.mp4>
set -e
ROOT="$HOME/Library/Application Support/MAOS-bridge"
export PATH="$ROOT/node/bin:$PATH"
RP="$ROOT/remotion"
PIPE="${MAOS_PIPE:-$(cd "$(dirname "$0")/.." && pwd)}"
abs() { case "$1" in /*) echo "$1";; *) echo "$PIPE/$1";; esac; }
PROPS="$(abs "$1")"; OUT="$(abs "$2")"; MODE="${3:-draft}"; BASE="$(abs "$4")"; COMP="${5:-Reel}"
rm -rf "$RP/src"; cp -R "$PIPE/remotion/src" "$RP/src"
rm -rf "$RP/public"; mkdir -p "$RP/public/fonts" "$RP/public/media"
cp "$PIPE/fonts/Oswald700.ttf" "$PIPE"/assets/fonts/*.ttf "$RP/public/fonts/"
cp "$PIPE"/remotion/media/* "$RP/public/media/"
[ -n "$4" ] && [ -f "$BASE" ] && cp "$BASE" "$RP/public/media/"
cd "$RP"
if [ "$MODE" = "final" ]; then Q="--video-bitrate=16M"; SC="--scale=1"; else Q="--video-bitrate=6M"; SC="--scale=0.75"; fi
echo "== Remotion render ($MODE) -> $OUT"
npx remotion render src/index.ts "$COMP" "$OUT" --props="$PROPS" --codec=h264 $Q $SC \
  --concurrency=4 --hardware-acceleration=if-possible --audio-codec=aac --audio-bitrate=192k --log=warn
[ -n "$4" ] && [ -f "$BASE" ] && "$ROOT/venv/bin/python" "$PIPE/remotion/sync_fix.py" "$BASE" "$OUT"
# итоговый звук: лимитер + −14 LUFS (музыка и звуки из Remotion иначе дают клиппинг)
FFB="$(cd "$PIPE" && "$ROOT/venv/bin/python" -c 'from montage import ffbin; print(ffbin())' 2>/dev/null)"
if [ -n "$FFB" ]; then
  "$FFB" -y -v error -i "$OUT" -c:v copy -af "alimiter=limit=0.8:attack=2:release=50,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" \
    -c:a aac -b:a 192k -movflags +faststart "$OUT.lim.mp4" && mv "$OUT.lim.mp4" "$OUT" && echo "== звук: лимитер + loudnorm −14"
fi
echo "== готово: $OUT ($(du -h "$OUT" | cut -f1))"
