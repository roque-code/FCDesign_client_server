#!/bin/sh
# La firma del enlazador no incluye los recursos. macOS, al bajar el archivo,
# lo declara dañado. Aquí se firma el paquete y se rehace la imagen sin
# atributos que el zip de GitHub no conserva.
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

if ! codesign -dv "$app" 2>&1 | grep -q 'Authority='; then
  tmp=$(mktemp)
  find "$app/Contents" -type f -print >"$tmp"
  while IFS= read -r bin; do
    [ "$(basename "$bin")" = "$executable" ] && continue
    if file "$bin" | grep -q 'Mach-O'; then
      codesign --force --sign - --timestamp=none "$bin"
    fi
  done <"$tmp"
  rm -f "$tmp"
  codesign --force --sign - --timestamp=none "$app"
fi

codesign --verify --deep --strict "$app"

ditto -c -k --keepParent "$app" "$bundle/macos/$name.zip"

if [ -d "$bundle/dmg" ]; then
  find "$bundle/dmg" -name '*.dmg' -print | while IFS= read -r dmg; do
    image=$(mktemp -d)
    hdiutil create -volname "$name" -srcfolder "$app" -ov -format UDZO "$image/app.dmg" >/dev/null
    xattr -c "$image/app.dmg" 2>/dev/null || true
    mv "$image/app.dmg" "$dmg"
    rmdir "$image"
  done
fi

rm -rf "$app"
echo "traza: imagen de Mac lista. Abre el .dmg o $name.zip."
