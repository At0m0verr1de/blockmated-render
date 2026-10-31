#!/bin/bash
# Install Blender 3.6.23 LTS into /Applications without visiting blender.org.
# Tries several official mirrors, verifies the SHA-256 published by Blender, then copies Blender.app.
set -euo pipefail
VER=3.6.23
case "$(uname -m)" in
  arm64)  FILE=blender-$VER-macos-arm64.dmg; SHA=ecbeaef4abbeb045de8465e78b3f97aec9b67faf2fc71b20e5eca37bf1caf874 ;;
  x86_64) FILE=blender-$VER-macos-x64.dmg;   SHA=910bd19e4d0f87be301df380a4fb03a08b9dcdb2b164dd0cabfb889a8dac03c2 ;;
  *) echo "unsupported CPU $(uname -m)"; exit 1 ;;
esac
MIRRORS=(
  https://download.blender.org/release
  https://mirrors.ocf.berkeley.edu/blender/release
  https://ftp.nluug.nl/pub/graphics/blender/release
  https://mirror.clarkson.edu/blender/release
)
DMG="$HOME/Downloads/$FILE"
if [ ! -f "$DMG" ] || [ "$(shasum -a 256 "$DMG" | cut -d' ' -f1)" != "$SHA" ]; then
  for m in "${MIRRORS[@]}"; do
    echo "downloading $FILE from ${m%%/release*} ..."
    if curl -fL --retry 2 --connect-timeout 15 -o "$DMG" "$m/Blender3.6/$FILE"; then
      [ "$(shasum -a 256 "$DMG" | cut -d' ' -f1)" = "$SHA" ] && break
      echo "checksum mismatch, trying next mirror"
    fi
    rm -f "$DMG"
  done
fi
[ -f "$DMG" ] || { echo "all mirrors failed - copy Blender 3.6 from another Mac instead (see README)"; exit 1; }
echo "checksum OK, installing"
MNT=$(hdiutil attach -nobrowse -readonly "$DMG" | awk -F'\t' '/\/Volumes\//{print $NF}')
[ -d /Applications/Blender.app ] && mv /Applications/Blender.app "/Applications/Blender-old-$(date +%s).app"
cp -R "$MNT/Blender.app" /Applications/
hdiutil detach -quiet "$MNT"
xattr -dr com.apple.quarantine /Applications/Blender.app 2>/dev/null || true
/Applications/Blender.app/Contents/MacOS/Blender --version | head -1
