# Crate Digger 2.0.0

A new look and a rebuilt plugin, with a new screen styled after a vintage MPC.

## What's new
- **New screen** in three pages: PLAY, FILTERS and FIND. A green LCD shows what is playing, the status, the time and your filters; the five filter
  knobs sit directly under their own LCD columns; big keys and arrows are easy to hit.
- **GAIN fader and a stereo level meter** on every page.
- **PLAY and STOP lamps**, and SYNC now sits with the transport.
- **FIND** is regrouped: DISCOGS, YOUTUBE (with MUSIC ONLY and the length filters) and its CHANNEL extension, with KEYBOARD and SEARCH together at the far right.
- Works on 64-bit MPCs (Live III and other aarch64 units) and 32-bit MPCs (Force, Live, Live II, One, X, Key), as two packages.
- **Projects saved with Crate Digger 1.x still load.**

## Install
Download the package for your device, unzip it and follow `INSTALL.txt` (also in the README).
- `Crate-Digger-2.0.0-VST2-Plugins-aarch64.zip`: MPC Live III and other 64-bit MPCs. Copy the plugin folder into `VST2 Plugins` on a drive.
- `Crate-Digger-2.0.0-VST2-Plugins-armv7.zip`: Force and other 32-bit MPCs. Includes `install-force.sh` for devices that list plugins in `MPC.settings`
  (needs root shell access); an older Crate Digger is replaced and your `channels.txt` is kept.

The plugin folder carries its own yt-dlp, Python and ffmpeg (about 125 MB armv7, 180 MB aarch64) and needs a network connection on the MPC.

## Notes
- Tested on an MPC Live III and a Force.
- Search and playback depend on Discogs and on yt-dlp resolving YouTube; see docs/TROUBLESHOOTING.md.
- Not tested yet: the channel search with a `channels.txt`, and typing on the popup keyboard.
