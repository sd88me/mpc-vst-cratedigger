#!/usr/bin/env bash
# Runs INSIDE the build container (see build-sdk.sh): compile the core + the SDK front end into one shared object.
# env: CD_N (plugin name), CD_U (uid as 'C','r','D','g'), OUT, TAG, FLAGS (extra gcc flags)
set -euo pipefail
gcc -O2 -fPIC -fvisibility=hidden -std=gnu11 -DYT_POSIX_SPAWN ${FLAGS:-} -Isrc/include -Isrc/dsp -c src/dsp/yt_stream_plugin.c -o "build/obj-$TAG.o"
g++ -std=c++17 -O2 -fPIC -shared -fvisibility=hidden -fvisibility-inlines-hidden -fno-gnu-unique -ffunction-sections -fdata-sections \
  -Wall -Wextra -Wno-unused-parameter ${FLAGS:-} -I/sdk/framework -Isrc -Isrc/include -Isrc/dsp -Isrc/sdk -DCD_NAME="\"$CD_N\"" -DCD_UID="$CD_U" \
  -o "$OUT" src/sdk/CrateDiggerPlugin.cpp "build/obj-$TAG.o" \
  -Wl,--gc-sections -Wl,--version-script=/sdk/tools/exports.map -Wl,--exclude-libs,ALL -static-libstdc++ -static-libgcc -ldl -lpthread -lm
strip "$OUT"
echo "-- $(basename "$OUT"): highest glibc needed (arm32 must stay <= 2.32):"; readelf -V "$OUT" | grep -o 'GLIBC_[0-9.]*' | sort -uV | tail -n 1
