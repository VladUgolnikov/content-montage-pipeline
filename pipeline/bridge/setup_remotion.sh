#!/bin/bash
# Node.js + Remotion локально (вне iCloud): ~/Library/Application Support/MAOS-bridge/{node,remotion}
set -e
ROOT="$HOME/Library/Application Support/MAOS-bridge"
NODE="$ROOT/node"; RP="$ROOT/remotion"
mkdir -p "$ROOT" "$RP"
if [ ! -x "$NODE/bin/node" ]; then
  echo "== Скачиваю Node.js 22 (darwin-arm64)"
  BASE="https://nodejs.org/dist/latest-v22.x"
  TGZ=$(curl -fsSL "$BASE/SHASUMS256.txt" | awk '/darwin-arm64.tar.gz$/{print $2}')
  curl -fsSL "$BASE/$TGZ" -o "$ROOT/node.tgz"
  mkdir -p "$NODE" && tar -xzf "$ROOT/node.tgz" -C "$NODE" --strip-components=1 && rm -f "$ROOT/node.tgz"
fi
export PATH="$NODE/bin:$PATH"
echo "== node $(node -v), npm $(npm -v)"
cd "$RP"
PIPE="${MAOS_PIPE:-$(cd "$(dirname "$0")/.." && pwd)}"
cp "$PIPE/remotion/package.json" "$RP/package.json"
npm install --no-audit --no-fund --loglevel=error
echo "== Браузер для рендера"
npx remotion browser ensure
echo "== Remotion готов: $(npx remotion versions 2>/dev/null | head -3 | tr '\n' ' ')"
