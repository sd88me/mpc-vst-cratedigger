#!/bin/sh
# Installs Crate Digger on a Force or another MPC whose MPC OS lists plugins in MPC.settings. Run on the device as root, from the unzipped folder:
#   sh install-force.sh [-y] [-t <synths-dir>]
# Copies "VST2 Plugins/sd88me - VST - Crate Digger" (the plugin, its skin and its engine) into a Synths folder (default /sdcard/Synths), backs up
# MPC.settings, registers the plugin, and restarts MPC. A 1.x install (same uid) is replaced: your channels.txt is kept. Safe to run again.
set -e
cd "$(dirname "$0")"
NAME='Crate Digger'; SKIN='sd88me - VST - Crate Digger'; SO='cratedigger-arm32.so'; UID_HEX='43724467'; LEGACY_SO='/sdcard/vst/cratedigger.so'
SYNTHS=/sdcard/Synths; YES=0
die() { echo "error: $*" >&2; exit 1; }
while [ $# -gt 0 ]; do
    case "$1" in
        -y) YES=1; shift ;;
        -t) [ -n "$2" ] || die "-t needs a folder"; SYNTHS="$2"; shift 2 ;;
        *) die "usage: sh install-force.sh [-y] [-t <synths-dir>]" ;;
    esac
done
case "$SYNTHS" in /*) ;; *) die "-t must be an absolute path" ;; esac
case "$SYNTHS" in *"&"*|*"|"*|*"\\"*) die "the Synths path may not contain & | or backslash" ;; esac
FILE="$SYNTHS/$SKIN/VST/$SO"
if [ -z "$MPC_INSTALL_TEST" ]; then
    [ "$(id -u)" = 0 ] || die "run as root"
    case "$(uname -m)" in armv7*) ;; *) die "this package is for 32-bit ARM MPCs (Force, Live, Live II, One, X, Key); this device is $(uname -m): use the -aarch64 package" ;; esac
    command -v systemctl >/dev/null || die "systemctl not found"
fi
SETTINGS="${MPC_SETTINGS:-$(ls /media/az01-internal/Settings/*/MPC.settings /data/Settings/*/MPC.settings 2>/dev/null | head -n 1)}"
[ -n "$SETTINGS" ] && [ -f "$SETTINGS" ] || die "MPC.settings not found (not an MPC OS device?)"
[ -f "VST2 Plugins/$SKIN/VST/$SO" ] || die "this package is damaged: VST2 Plugins/$SKIN/VST/$SO is missing"
mkdir -p "$SYNTHS" || die "cannot create $SYNTHS"
MP=$(df -kP "$SYNTHS" 2>/dev/null | awk 'NR==2 {m = $6; for (i = 7; i <= NF; i++) m = m " " $i; print m}' | sed 's/ /\\040/g')
if [ -n "$MP" ] && MP="$MP" awk '$2 == ENVIRON["MP"] {print $4}' /proc/mounts 2>/dev/null | grep -q '\(^\|,\)noexec\(,\|$\)'; then
    echo "warning: $SYNTHS is on a noexec mount, so MPC will not be able to load this plugin from it. Use the internal drive or an SD card (-t /sdcard/Synths)."
fi
echo "Installing $NAME:"
echo "  $SYNTHS/$SKIN/ (plugin, skin and engine), and an entry in $SETTINGS"
if [ $YES = 0 ]; then
    printf "MPC will be stopped and restarted. Save your project first. Continue? [y/N] "
    read -r ok; case "$ok" in y|Y|yes) ;; *) echo "cancelled"; exit 1 ;; esac
fi
mpc_service() { if systemctl cat acvs >/dev/null 2>&1; then echo acvs; elif systemctl cat inmusic-mpc >/dev/null 2>&1; then echo inmusic-mpc; else echo acvs; fi; }
mpc_ctl() { if [ -n "$MPC_INSTALL_TEST" ]; then return 0; fi; systemctl "$1" "$(mpc_service)"; }
mpc_ctl stop
trap 'mpc_ctl start' EXIT
if [ -z "$MPC_INSTALL_TEST" ]; then
    i=0; while pidof MPC >/dev/null && [ $i -lt 30 ]; do sleep 1; i=$((i + 1)); done
    pidof MPC >/dev/null && die "MPC did not stop"
fi
# 1. the folder: staged next to the target, your channels.txt carried over, then swapped in
NEW="$SYNTHS/$SKIN"; STAGE="$SYNTHS/.$SKIN.new"; OLD="$SYNTHS/.$SKIN.old"
rm -rf "$STAGE" "$OLD"
cp -r "VST2 Plugins/$SKIN" "$STAGE"
if [ -f MODES ]; then   # a zip unpacked on Windows loses the executable bits: put them back
    while read -r rel; do
        case "$rel" in ""|/*|..|../*|*/..|*/../*) continue ;; esac
        [ -f "$STAGE/$rel" ] && chmod 755 "$STAGE/$rel"
    done < MODES
fi
for c in "$NEW/channels.txt" "$NEW/cratedigger/channels.txt" "/sdcard/vst/cratedigger/channels.txt"; do
    if [ -f "$c" ]; then cp "$c" "$STAGE/channels.txt"; echo "kept your channels.txt from $c"; break; fi
done
if [ -e "$NEW" ]; then mv "$NEW" "$OLD"; fi
mv "$STAGE" "$NEW"
rm -rf "$OLD"
# 2. the plugin-list entry (entries with the same file= or uid, including a 1.x install, are replaced)
BAK="$SETTINGS.bak-cratedigger-$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS" "$BAK"
printf '<PLUGIN name="Crate Digger" descriptiveName="Crate Digger" format="VST" category="Synth" manufacturer="sd88me" version="1.0" file="%s" uid="%s" isInstrument="1" fileTime="0" infoUpdateTime="0" numInputs="0" numOutputs="2" isShell="0"/>\n' "$FILE" "$UID_HEX" > "$SETTINGS.entry"
awk -v mode=add -v file="$FILE" -v alt="$LEGACY_SO" -v uid="$UID_HEX" -v entryfile="$SETTINGS.entry" -v listkey=pluginList-arm -f plugin_list.awk "$SETTINGS" > "$SETTINGS.new"
rm -f "$SETTINGS.entry"
n=$(grep -c "file=\"$FILE\"" "$SETTINGS.new" || true)
u=$(grep -c " uid=\"$UID_HEX\"" "$SETTINGS.new" || true)
[ "$n" = 1 ] && [ "$u" = 1 ] || { rm -f "$SETTINGS.new"; die "settings edit failed (entries: $n by file, $u by uid); MPC.settings unchanged"; }
grep -q '<PROPERTIES' "$SETTINGS.new" && grep -q '</PROPERTIES>' "$SETTINGS.new" || { rm -f "$SETTINGS.new"; die "edited settings lost their root element; MPC.settings unchanged"; }
mv "$SETTINGS.new" "$SETTINGS"
# 3. a 1.x install in the old layout
[ -f "$LEGACY_SO" ] && [ "$LEGACY_SO" != "$FILE" ] && rm -f "$LEGACY_SO" && echo "removed the old copy $LEGACY_SO"
sync
echo "Done. Settings backup: $BAK"
echo "Starting MPC. Add '$NAME' to a track from the plugin browser."
