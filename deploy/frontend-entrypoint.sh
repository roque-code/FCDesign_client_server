#!/bin/sh
set -eu

stamp="/app/node_modules/.traza-package-lock"
current="$(sha256sum package-lock.json)"
if [ ! -f "$stamp" ] || [ "$(cat "$stamp")" != "$current" ]; then
  npm ci
  mkdir -p /app/node_modules
  echo "$current" > "$stamp"
fi

exec npm run dev -- --host 0.0.0.0 --port 5173
