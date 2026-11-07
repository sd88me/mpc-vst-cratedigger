#!/usr/bin/env bash
# Offline x86 test under ASan/UBSan (no device): the SDK front end + the real core, driven by tests/host_test.cpp. Must print OK.
set -euo pipefail
cd "$(dirname "$0")/.."
SDK="${MPC_SDK:-$HOME/mpc-310-private/plugin-vibecode-sdk/plugin-vibecode-sdk}"
python3 tools/gen_sdk_params.py >/dev/null
docker image inspect crate-sdk-x64 >/dev/null 2>&1 || docker build -q -t crate-sdk-x64 --build-arg BASE=gcc:12 scripts >/dev/null
mkdir -p build/test
docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/b -v "$SDK":/sdk:ro -w /b crate-sdk-x64 bash -euc '
  S="-fsanitize=address,undefined -O1 -g"
  gcc $S -std=gnu11 -DYT_POSIX_SPAWN -Isrc/include -Isrc/dsp -c src/dsp/yt_stream_plugin.c -o build/test/core.o
  g++ $S -std=c++17 -DCD_TEST -I/sdk/framework -Isrc -Isrc/include -Isrc/dsp -Isrc/sdk -c src/sdk/CrateDiggerPlugin.cpp -o build/test/plugin.o
  g++ $S -std=c++17 -Isrc -Isrc/sdk -c tests/host_test.cpp -o build/test/host_test.o
  g++ $S -o build/test/ctest build/test/core.o build/test/plugin.o build/test/host_test.o -ldl -lpthread -lm
  ./build/test/ctest' 2>&1 | tail -${TAIL:-60}
