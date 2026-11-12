#!/usr/bin/env bash
# The catalog-shaped release zips, from the release build (build/sdk/<cpu>/"sd88me - VST - Crate Digger", made by ./build-sdk.sh):
#   dist/Crate-Digger-<ver>-mpc-armv7.zip, dist/Crate-Digger-<ver>-mpc-aarch64.zip   one per CPU, made by mpc-vst-plugins' tools/release.py
# As 1.x, the .so is cratedigger.so at the folder root, so the installer upgrades a 1.x install in place; channels.txt is user data,
# kept on upgrade. The engine bundle (yt-dlp, Python, ffmpeg) is Content/engine. MPC_VST: an mpc-vst-plugins checkout with tools/release.py.
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
MPC_VST="${MPC_VST:-$HOME/mpc-vst-plugins-postlaunch}"
[ -f "$MPC_VST/tools/release.py" ] || { echo "need mpc-vst-plugins with tools/release.py (MPC_VST)" >&2; exit 1; }
DIR="sd88me - VST - Crate Digger"
VER=$(python3 -c 'import json;print(json.load(open("'"$here"'/plugin.json"))["version"])')
out="$here/dist"; mkdir -p "$out"
for pair in armv7:arm32 aarch64:arm64; do
  IFS=: read -r cpu so <<<"$pair"
  SRC="$here/build/sdk/$cpu/$DIR"
  [ -f "$SRC/VST/cratedigger-$so.so" ] || { echo "missing $SRC: run ./build-sdk.sh first" >&2; exit 1; }
  python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); sys.exit(0 if m["uid"]=="CrDg" and "Beta" not in m["name"] else "not the release identity")' "$SRC/plugin.json"
  st="$here/build/catalog/$cpu"; rm -rf "$st"; mkdir -p "$st/$DIR"
  cp -r "$SRC/Plugin Skins" "$SRC/version.xml" "$st/$DIR/"
  cp "$here/LICENSE" "$st/$DIR/"
  python3 - "$SRC/plugin.json" "$st/$DIR/plugin.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
m.pop("file32", None); m.pop("file64", None)
m["file32" if "armv7" in sys.argv[2] else "file64"] = "cratedigger.so"
json.dump(m, open(sys.argv[2], "w"), indent=2)
PY
  cp "$SRC/VST/cratedigger-$so.so" "$st/cratedigger.so"
  cp -a "$SRC/Content" "$st/Content"
  cp "$here/docs/channels.example.txt" "$st/Content/channels.example.txt"
  printf '<PLUGIN name="Crate Digger" descriptiveName="Crate Digger" format="VST" category="Synth" manufacturer="sd88me" version="%s" file="cratedigger.so" uid="43724467" isInstrument="1" fileTime="0" infoUpdateTime="0" numInputs="0" numOutputs="2" isShell="0"/>\n' "$VER" > "$st/entry.xml"
  python3 "$MPC_VST/tools/release.py" --so "$st/cratedigger.so" --skin "$st/$DIR" --entry "$st/entry.xml" --version "$VER" \
    --extra "$st/Content:Content" --user-data channels.txt \
    --repo sd88me/mpc-vst-cratedigger --license MIT --id crate-digger \
    --requires "A network connection (streams from Discogs and the web)" \
    --about "Dig for records by genre, style, decade, region and country on Discogs, then stream and play them into your MPC track. Needs a network connection." \
    -o "$st/dist"
  z=$(ls "$st/dist"/*.zip); cp "$z" "$out/Crate-Digger-$VER-mpc-$cpu.zip"
done
ls -la "$out"/Crate-Digger-"$VER"-mpc-*.zip
