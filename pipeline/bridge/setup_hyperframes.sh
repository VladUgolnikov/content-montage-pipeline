#!/bin/bash
# HyperFrames CLI локально (вне iCloud) + ffmpeg/ffprobe из Remotion в PATH
set -e
ROOT="$HOME/Library/Application Support/MAOS-bridge"
export PATH="$ROOT/node/bin:$PATH"
C="$ROOT/remotion/node_modules/@remotion/compositor-darwin-arm64"
mkdir -p "$ROOT/bin"
for b in ffmpeg ffprobe; do
  printf '#!/bin/bash\nexport DYLD_LIBRARY_PATH="%s"\nexec "%s/%s" "$@"\n' "$C" "$C" "$b" > "$ROOT/bin/$b"
  chmod +x "$ROOT/bin/$b"
done
export PATH="$ROOT/bin:$PATH"
ffmpeg -hide_banner -version | head -1; ffprobe -hide_banner -version | head -1
mkdir -p "$ROOT/hyperframes" && cd "$ROOT/hyperframes"
[ -f package.json ] || echo '{"name":"hf-local","private":true}' > package.json
[ -d node_modules/hyperframes ] || npm install --no-audit --no-fund --loglevel=error hyperframes@latest
npx hyperframes --version
npx hyperframes doctor 2>&1 | grep -E "✓|✗" | grep -v Docker || true
