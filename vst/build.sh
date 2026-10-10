#!/usr/bin/env bash
# Build Crate Digger as a VST2 plugin for the MPC OS plugin host (armhf; TARGET_ARCH=aarch64 for Gen2 MPC devices).
#   vst/build/cratedigger.so          -> /sdcard/vst/ on the device (aarch64: vst/build/aarch64/cratedigger.so)
#   vst/build/pluginlist-entry.xml    the <PLUGIN> line for MPC.settings' pluginList-arm
# The engine bundle (bin/yt-dlp, bin/python3, bin/ffmpeg) is found at runtime: see
# find_module_dir() in cratedigger_vst.cpp.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 vst/gen_params.py
# armv7 (default): arm32v7/gcc:11-bullseye, glibc 2.31 so it also loads on MPC OS 2.x. aarch64 (Gen2, MPC OS 3.x only, glibc 2.39):
# arm64v8/gcc:12-bookworm, into vst/build/aarch64/.
case "${TARGET_ARCH:-armv7}" in
  armv7)   PLATFORM=linux/arm/v7; IMAGE=arm32v7/gcc:11-bullseye; OUT=vst/build ;;
  aarch64) PLATFORM=linux/arm64;  IMAGE=arm64v8/gcc:12-bookworm; OUT=vst/build/aarch64 ;;
  *) echo "unknown TARGET_ARCH ${TARGET_ARCH}" >&2; exit 1 ;;
esac
docker run --rm --platform "$PLATFORM" -u "$(id -u):$(id -g)" -e OUT="$OUT" -v "$PWD":/b -w /b "$IMAGE" bash -euxc '
  mkdir -p "$OUT/obj"
  gcc -O2 -fPIC -fvisibility=hidden -std=gnu11 -DYT_POSIX_SPAWN -Isrc/include -Isrc/dsp \
      -c src/dsp/yt_stream_plugin.c -o "$OUT/obj/core.o"
  g++ -O2 -fPIC -fvisibility=hidden -std=c++17 -Wall -Wextra -Wno-unused-parameter \
      -Isrc/include -Isrc -Ivst/build -c vst/cratedigger_vst.cpp -o "$OUT/obj/vst.o"
  g++ -shared -o "$OUT/cratedigger.so" "$OUT/obj/core.o" "$OUT/obj/vst.o" \
      -static-libstdc++ -static-libgcc -lpthread -ldl
  strip "$OUT/cratedigger.so"
  echo "-- exported --"; readelf --dyn-syms -W "$OUT/cratedigger.so" | grep -E " GLOBAL .* [0-9]+ [A-Za-z]" | grep -v UND
  echo "-- needed --"; readelf -d "$OUT/cratedigger.so" | grep NEEDED
  echo "-- highest glibc (MPC OS 2.x has 2.32; 3.x and Gen2 have 2.39) --"; readelf -V "$OUT/cratedigger.so" | grep -o "GLIBC_[0-9.]*" | sort -uV | tail -1
'
md5sum "$OUT/cratedigger.so"
