#!/usr/bin/env bash
# Everything a release zip needs (TARGETS="armv7 aarch64": one set per CPU), in one go (mpc-vst-plugins' vst-release workflow runs this):
#   vst/build/cratedigger.so                       -> payload/vst/
#   vst/build/skin/sd88me - VST - Crate Digger/    -> payload/Synths/
#   vst/build/pluginlist-entry.xml
#   vst/build/engine/bin/                          -> payload/vst/cratedigger/bin (release.py --extra):
#       yt-dlp, ffmpeg/ffprobe, the private Python 3.11 and zlib module, yt_dlp_daemon.py
# Needs Docker with armhf emulation, zig, python3 with Pillow, and an mpc-vst-plugins checkout
# (MPC_VST) for its skin tooling. The skin artwork is drawn by the browser renderer
# (tools/html_art.py, "mpc-vst-html-art" Docker image: headless Chromium + Pillow) for real
# Titillium Web text, knob value arcs and transparent-edge controls -- not published to any
# registry, so build it here from $MPC_VST/tools/html_art/Dockerfile (cached by tag after the
# first build, on a dev machine and in CI alike).
set -euo pipefail
cd "$(dirname "$0")/.."
MPC_VST="${MPC_VST:?set MPC_VST to an mpc-vst-plugins checkout}"

# TARGETS (default "armv7"): "armv7 aarch64" also builds the Gen2 MPC plugin and its engine bundle (mpc-vst-plugins docs/GEN2.md):
#   vst/build/aarch64/cratedigger.so, vst/build/aarch64/engine/bin/  -> the -mpc-aarch64.zip
for t in ${TARGETS:-armv7}; do
  case "$t" in
    armv7)
      scripts/build-deps.sh
      scripts/build-pyzlib.sh   # the Force/Gen1 system Python 3.8 has no zlib module
      scripts/build-python.sh
      vst/build.sh ;;
    aarch64)   # Gen2 ships MPC OS 3.x only; the bundled Python 3.11 has its own zlib, so no pyzlib
      TARGET_ARCH=aarch64 scripts/build-deps.sh
      TARGET_ARCH=aarch64 scripts/build-python.sh
      TARGET_ARCH=aarch64 vst/build.sh ;;
    *) echo "unknown target $t" >&2; exit 1 ;;
  esac
done

docker build -q -t mpc-vst-html-art "$MPC_VST/tools/html_art"
# SHADOW_SKIN_MPC_OS=2 (set by the caller) writes the skin in the MPC OS 2.x shape: it has to be passed into the container.
docker run --rm -e MPC_VST=/mpcvst ${SHADOW_SKIN_MPC_OS:+-e SHADOW_SKIN_MPC_OS="$SHADOW_SKIN_MPC_OS"} -v "$PWD":/repo -v "$MPC_VST":/mpcvst \
  -w /repo mpc-vst-html-art:latest python3 vst/gen_skin.py

for t in ${TARGETS:-armv7}; do
  if [ "$t" = aarch64 ]; then deps=build/deps-aarch64; out=vst/build/aarch64/engine; else deps=build/deps; out=vst/build/engine; fi
  rm -rf "$out"
  mkdir -p "$out/bin"
  cp -R "$deps/bin/." "$out/bin/"
  cp src/bin/yt_dlp_daemon.py "$out/bin/"
  ls -la "$out/bin"
done
ls -la vst/build
