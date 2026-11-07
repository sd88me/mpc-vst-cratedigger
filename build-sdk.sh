#!/usr/bin/env bash
# Build Crate Digger on the MPC Plugin SDK front end (src/sdk/CrateDiggerPlugin.cpp) into one plugin folder per CPU, as two release zips are
# shipped (a 32-bit one and a 64-bit one):
#   build/sdk/armv7/"sd88me - VST - Crate Digger"/    Force, MPC Live / One / X / Key (glibc 2.31)
#   build/sdk/aarch64/"sd88me - VST - Crate Digger"/  MPC Live III and other 64-bit units
# The engine bundle (yt-dlp, python, ffmpeg, the daemon) goes in Content/engine/. It is taken from build/engine-<cpu>/, which this script
# unpacks from the last release zip (ENGINE_RELEASE, default cratedigger-vst-v1.3.0) the first time; rebuild the bundle itself with
# vst/release_build.sh.
#   ./build-sdk.sh            gen params, build both CPUs, assemble the folders (plugin.json, version.xml, Plugin Skins when skins/ exists)
#   ./build-sdk.sh beta       the same as "Crate Digger 2 Beta" (uid CrDB): installs next to the release
#   ./build-sdk.sh test       the offline test (tests/run.sh)
# MPC_SDK: the plugin-vibecode-sdk checkout.
set -euo pipefail
cd "$(dirname "$0")"
SDK="${MPC_SDK:-$HOME/mpc-310-private/plugin-vibecode-sdk/plugin-vibecode-sdk}"
[ -f "$SDK/framework/mpc_plugin.h" ] || { echo "need the SDK (MPC_SDK)" >&2; exit 1; }
NAME="Crate Digger"; UID_="'C','r','D','g'"; UIDS=CrDg; SLUG=cratedigger
if [ "${1:-}" = beta ]; then NAME="Crate Digger 2 Beta"; UID_="'C','r','D','B'"; UIDS=CrDB; SLUG=cratedigger2beta; fi
python3 tools/gen_sdk_params.py
if [ "${1:-}" = test ]; then tests/run.sh; exit; fi
mkdir -p build
engine() {   # <cpu> <zip suffix>: unpack the engine bundle of the last release once
  [ -d "build/engine-$1/bin" ] && return
  local tag="${ENGINE_RELEASE:-cratedigger-vst-v1.3.0}"
  mkdir -p build/rel && gh release download "$tag" -R sd88me/mpc-vst-cratedigger -p "*-mpc-$2.zip" --dir build/rel --clobber
  python3 - "$1" "$(ls build/rel/*-mpc-$2.zip | head -n 1)" <<'PY'
import os, sys, zipfile
cpu, z = sys.argv[1:]
zf = zipfile.ZipFile(z)
pre = [n for n in zf.namelist() if n.endswith("/cratedigger/bin/yt-dlp")][0][:-len("bin/yt-dlp")]
for i in zf.infolist():
    if not i.filename.startswith(pre) or i.is_dir(): continue
    dst = os.path.join("build/engine-" + cpu, i.filename[len(pre):]); os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(zf.read(i))
    if (i.external_attr >> 16) & 0o777: os.chmod(dst, (i.external_attr >> 16) & 0o777)
PY
}
build() {   # <cpu> <docker platform> <image> <base image> <zip suffix>
  local cpu="$1" folder="build/sdk/$1/sd88me - VST - $NAME"
  rm -rf "$folder"; mkdir -p "$folder/VST" "$folder/Plugin Skins" "$folder/Content"
  docker image inspect "$3" >/dev/null 2>&1 || docker build -q -t "$3" --platform "$2" --build-arg BASE="$4" scripts >/dev/null
  local so="$SLUG-$([ "$cpu" = armv7 ] && echo arm32 || echo arm64).so"
  docker run --rm --platform "$2" -u "$(id -u):$(id -g)" -e CD_N="$NAME" -e CD_U="$UID_" -e OUT="$folder/VST/$so" -e TAG="$3" \
    -v "$PWD":/b -v "$SDK":/sdk:ro -w /b "$3" scripts/compile.sh
  engine "$cpu" "$5"
  cp -a "build/engine-$cpu" "$folder/Content/engine"
  python3 - "$NAME" "$UIDS" "$folder" "$so" "$cpu" <<'PY'
import json, sys
name, uid, folder, so, cpu = sys.argv[1:]
m = json.load(open("plugin.json"))
m["name"], m["uid"] = name, uid
m["file32" if cpu == "armv7" else "file64"] = "VST/" + so
json.dump(m, open(folder + "/plugin.json", "w"), indent=2)
open(folder + "/version.xml", "w").write('<?xml version="1.0" encoding="utf-8"?>\n<plugincontent version="1.0">\n    <version>%s</version>\n</plugincontent>\n' % m["version"])
PY
  # Phase 1 has no skin (the MPC then shows its generic parameter pages); phase 2 adds skins/ from tools/make_tui.py.
  if [ -d skins ]; then cp -r skins/. "$folder/Plugin Skins/"; else rmdir "$folder/Plugin Skins"; fi
  python3 "$SDK/tools/validate.py" "$folder" || true
  echo "built: $folder"
}
build armv7   linux/arm/v7 crate-sdk-arm32 arm32v7/gcc:11-bullseye armv7 &
build aarch64 linux/arm64  crate-sdk-arm64 arm64v8/gcc:12-bookworm aarch64 &
wait
