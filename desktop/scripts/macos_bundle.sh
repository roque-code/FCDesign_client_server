#!/bin/sh
# Sin notarización de Apple, macOS marca la descarga y responde -47 al abrir
# Traza.app. La firma ad hoc cubre el programa y el intérprete. El acceso
# «Abrir Traza» copia la app fuera de la imagen y quita esa marca.
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
bundle="$root/src-tauri/target/release/bundle"
app=$(find "$bundle/macos" -maxdepth 1 -name '*.app' -print | head -n 1)
if [ -z "$app" ]; then
  echo "traza: no hay una aplicación de Mac para empaquetar."
  exit 1
fi

name=$(basename "$app" .app)
executable=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")
if [ ! -x "$app/Contents/MacOS/$executable" ]; then
  chmod 755 "$app/Contents/MacOS/$executable"
fi

if ! codesign -dv "$app" 2>&1 | grep -q 'Authority='; then
  ents=$(mktemp)
  if codesign -d --entitlements :- "$app" >"$ents" 2>/dev/null && grep -q 'plist' "$ents"; then
    codesign --force --deep --sign - --timestamp=none --entitlements "$ents" "$app"
  else
    codesign --force --deep --sign - --timestamp=none "$app"
  fi
  rm -f "$ents"
fi

codesign --verify --deep --strict "$app"

payload=$(mktemp -d)/"$name"
mkdir -p "$payload"
ditto "$app" "$payload/$name.app"

cat >"$payload/Abrir Traza.command" <<'EOF'
#!/bin/bash
here=$(cd "$(dirname "$0")" && pwd)
src="$here/Traza.app"
dest="$HOME/Applications/Traza.app"
if [ ! -d "$src" ]; then
  echo "No encuentro Traza.app junto a este archivo."
  read -r -p "Pulsa Retorno para cerrar." _
  exit 1
fi
mkdir -p "$HOME/Applications"
if [ -d "$dest" ] && ! rm -rf "$dest"; then
  echo "Cierra Traza si está abierta e inténtalo de nuevo."
  read -r -p "Pulsa Retorno para cerrar." _
  exit 1
fi
cp -R "$src" "$dest"
xattr -cr "$dest"
open "$dest"
echo "Traza quedó en Aplicaciones de tu usuario y ya se abrió."
EOF
chmod 755 "$payload/Abrir Traza.command"

cat >"$payload/Leeme.txt" <<'EOF'
macOS no abre Traza.app con doble clic cuando la copia llega desde GitHub.
Muestra «no se puede abrir» y el código -47. La app no está dañada: falta la notarización de Apple.

Abre «Abrir Traza.command». Si macOS pregunta, elige Abrir.
Ese archivo copia Traza a tu carpeta Aplicaciones y la abre.

Después ábrela desde esa carpeta. No hace falta repetir el paso.
EOF

ditto -c -k --keepParent "$payload" "$bundle/macos/$name.zip"

if [ -d "$bundle/dmg" ]; then
  find "$bundle/dmg" -name '*.dmg' -print | while IFS= read -r dmg; do
    image=$(mktemp -d)
    hdiutil create -volname "$name" -srcfolder "$payload" -ov -format UDZO "$image/app.dmg" >/dev/null
    xattr -c "$image/app.dmg" 2>/dev/null || true
    mv "$image/app.dmg" "$dmg"
    rmdir "$image"
  done
fi

rm -rf "$app" "$payload"
echo "traza: imagen de Mac lista. Abre «Abrir Traza.command» dentro del .zip o del .dmg."
