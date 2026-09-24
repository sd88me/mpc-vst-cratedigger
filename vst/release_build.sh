#!/usr/bin/env bash
# Everything a release zip needs, in one go (mpc-vst-plugins' vst-release workflow runs this):
#   vst/build/cratedigger.so                       -> payload/vst/
#   vst/build/skin/sd88me - VST - Crate Digger/    -> payload/Synths/
#   vst/build/pluginlist-entry.xml
#   vst/build/engine/bin/                          -> payload/vst/cratedigger/bin (release.py --extra):
#       yt-dlp, ffmpeg/ffprobe, the private Python 3.11 and zlib module, yt_dlp_daemon.py
# Needs Docker with armhf emulation, zig, python3 with Pillow, a C compiler, and a force-shadow
# checkout for the skin artwork renderer (FORCE_SHADOW).
set -euo pipefail
cd "$(dirname "$0")/.."
FORCE_SHADOW="${FORCE_SHADOW:?set FORCE_SHADOW to a force-shadow checkout}"

scripts/build-deps.sh
scripts/build-pyzlib.sh
scripts/build-python.sh
vst/build.sh

gcc -O2 -I"$FORCE_SHADOW/tools" -o vst/build/shadow_art vst/shadow_art.c -lm
python3 vst/gen_skin.py

rm -rf vst/build/engine
mkdir -p vst/build/engine/bin
cp -R build/deps/bin/. vst/build/engine/bin/
cp src/bin/yt_dlp_daemon.py vst/build/engine/bin/
ls -la vst/build vst/build/engine/bin
