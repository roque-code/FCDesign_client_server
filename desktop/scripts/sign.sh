#!/bin/sh
# La firma es opcional. Sin certificados, la construcción de prueba sigue.
set -eu
if [ -z "${APPLE_SIGNING_IDENTITY:-}" ] && [ -z "${APPLE_CERTIFICATE:-}" ] && [ -z "${WINDOWS_CERTIFICATE:-}" ] && [ -z "${TAURI_SIGNING_PRIVATE_KEY:-}" ]; then
  echo "traza: sin certificados en el entorno, se omite la firma."
  exit 0
fi
echo "traza: hay material de firma en el entorno. Tauri lo usa al empaquetar."
exit 0
