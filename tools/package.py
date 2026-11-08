#!/usr/bin/env python3
"""Packs the release zips from build/sdk/<cpu>/"sd88me - VST - Crate Digger" (made by ./build-sdk.sh, release identity) into dist/:
  dist/Crate-Digger-<ver>-VST2-Plugins-aarch64.zip   VST2 Plugins/<folder>/   (MPC Live III and other 64-bit MPCs)
  dist/Crate-Digger-<ver>-VST2-Plugins-armv7.zip     VST2 Plugins/<folder>/ + install-force.sh (Force and other 32-bit MPCs)
File modes are kept (the engine's programs must stay executable). No firmware, ROM or cookie data is included."""
import json, os, stat, sys, zipfile
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
VER = json.load(open(os.path.join(ROOT, "plugin.json")))["version"]
NAME = "sd88me - VST - Crate Digger"
DIST = os.path.join(ROOT, "dist")

TEXT = {
"aarch64": """Crate Digger %s for MPC Live III and other 64-bit (aarch64) MPCs

1. Copy the folder "VST2 Plugins/%s" into a folder named exactly "VST2 Plugins" at the root of a drive the MPC can see
   (internal storage, SD card or USB drive). If that drive already has a "VST2 Plugins" folder, put the plugin folder inside it.
2. On the MPC: Preferences > Enhancements > Enable Enhancements and VST2 Support must be on. Restart the MPC.
3. Add "Crate Digger" to a track from the plugin browser (External VST Plugins).

The plugin folder is about 180 MB (it carries its own yt-dlp, Python and ffmpeg). It needs a network connection on the MPC.
To upgrade, replace the whole plugin folder; keep your channels.txt (in the plugin folder).
More: https://github.com/sd88me/mpc-vst-cratedigger
""" % (VER, NAME),
"armv7": """Crate Digger %s for Force and other 32-bit (armv7) MPCs

A) MPC OS that loads plugin folders from "VST2 Plugins":
   copy "VST2 Plugins/%s" into a folder named exactly "VST2 Plugins" at the root of a drive, enable VST2 Support
   (Preferences > Enhancements), restart the MPC and add "Crate Digger" from External VST Plugins.

B) Force and MPC OS that lists plugins in MPC.settings (needs root shell access to the device):
   scp -r <this unzipped folder> root@<device-ip>:/tmp/crate-digger
   ssh root@<device-ip> sh /tmp/crate-digger/install-force.sh
   This stops the MPC (save your project first), copies the plugin to /sdcard/Synths, backs up and edits MPC.settings, and restarts the MPC.
   An older Crate Digger (1.x) is replaced and your channels.txt is kept. Then add "Crate Digger" to a track from the plugin browser.

The plugin folder is about 125 MB (it carries its own yt-dlp, Python and ffmpeg). It needs a network connection on the MPC.
More: https://github.com/sd88me/mpc-vst-cratedigger
""" % (VER, NAME),
}


def add_tree(z, src, arc):
    for d, _, files in os.walk(src):
        for f in sorted(files):
            full = os.path.join(d, f)
            rel = os.path.join(arc, os.path.relpath(full, src)).replace(os.sep, "/")
            zi = zipfile.ZipInfo(rel, (2026, 11, 8, 0, 0, 0))
            mode = stat.S_IMODE(os.stat(full).st_mode)
            zi.external_attr = ((stat.S_IFREG | (0o755 if mode & 0o100 else 0o644)) << 16)
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, open(full, "rb").read())


def add_file(z, path, arc, mode=0o644):
    zi = zipfile.ZipInfo(arc, (2026, 11, 8, 0, 0, 0))
    zi.external_attr = (stat.S_IFREG | mode) << 16
    zi.compress_type = zipfile.ZIP_DEFLATED
    z.writestr(zi, open(path, "rb").read() if os.path.isfile(path) else path.encode())


def main():
    os.makedirs(DIST, exist_ok=True)
    for cpu in ("aarch64", "armv7"):
        src = os.path.join(ROOT, "build", "sdk", cpu, NAME)
        if not os.path.isdir(src):
            sys.exit("missing %s: run ./build-sdk.sh first" % src)
        for bad in ("beta", "Beta"):
            if bad in json.load(open(os.path.join(src, "plugin.json")))["name"]:
                sys.exit("%s is a beta build" % src)
        out = os.path.join(DIST, "Crate-Digger-%s-VST2-Plugins-%s.zip" % (VER, cpu))
        execs = []
        with zipfile.ZipFile(out, "w") as z:
            add_tree(z, src, "VST2 Plugins/" + NAME)
            add_file(z, os.path.join(ROOT, "LICENSE"), "VST2 Plugins/%s/LICENSE" % NAME)
            add_file(z, os.path.join(ROOT, "UPSTREAM_LICENSE.txt"), "VST2 Plugins/%s/UPSTREAM_LICENSE.txt" % NAME)
            add_file(z, os.path.join(ROOT, "UPSTREAM_THIRD_PARTY_NOTICES.md"), "VST2 Plugins/%s/UPSTREAM_THIRD_PARTY_NOTICES.md" % NAME)
            add_file(z, os.path.join(ROOT, "docs", "channels.example.txt"), "VST2 Plugins/%s/channels.example.txt" % NAME)
            add_file(z, TEXT[cpu], "INSTALL.txt")
            if cpu == "armv7":
                add_file(z, os.path.join(ROOT, "tools", "install-force.sh"), "install-force.sh", 0o755)
                add_file(z, os.path.join(ROOT, "tools", "plugin_list.awk"), "plugin_list.awk")
                for d, _, files in os.walk(src):
                    for f in files:
                        full = os.path.join(d, f)
                        if os.stat(full).st_mode & 0o100:
                            execs.append(os.path.join("VST2 Plugins", NAME, os.path.relpath(full, src)).replace(os.sep, "/")[len("VST2 Plugins/" + NAME) + 1:])
                add_file(z, "\n".join(sorted(execs)) + "\n", "MODES")
        print("wrote", os.path.normpath(out), "%.0f MB" % (os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
