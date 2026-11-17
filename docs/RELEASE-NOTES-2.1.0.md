# Crate Digger 2.1.0

Faster digging and fewer dead ends. Same screen as 2.0.0; projects from 2.0.0 and 1.x load as before.

## What's new
- **Faster Discogs searches.** Releases are looked up in parallel over kept-alive connections, and every release looked up is remembered on the
  device for two weeks, so a repeat search costs nothing. A cold search on a Live III went from about 6 s to about 2 s.
- **The next search is often ready at once.** While you listen, Crate Digger looks up the next batch for the same filters in the background
  (within Discogs' rate limit, always leaving room for your next search).
- **Rows start straight away.** The first rows of a search, and the next rows while a track plays, are resolved ahead of time; tapping one
  starts it without the usual wait.
- **No more removed videos in the results.** Discogs often links to YouTube videos that have since been deleted; those releases are now
  skipped (a video that is only private or region-blocked can still show UNAVAILABLE when played).
- **Tracks play to the end.** The last part of a track (up to 45 s, whatever was buffered) was cut off when the download finished early. Fixed.
- **Full-screen keyboard.** The keyboard now fills the screen with the text you are typing shown at its top. Tapping the TEXT line opens it too.
- **Q-Links and the data wheel step through short lists** (PAGE, SOURCE, the lengths, the channel), one entry per click; before, a Q-Link could
  not move them at all.
- **STYLE and COUNTRY use the whole knob.** Their lists change length with GENRE and REGION; a knob now spreads whatever the list holds over its
  full turn instead of using only the start of it.

## Install
Download the package for your device, unzip it and follow `INSTALL.txt` (also in the README).
- `Crate-Digger-2.1.0-VST2-Plugins-aarch64.zip`: MPC Live III and other 64-bit MPCs. Copy the plugin folder into `VST2 Plugins` on a drive.
- `Crate-Digger-2.1.0-VST2-Plugins-armv7.zip`: Force and other 32-bit MPCs. Includes `install-force.sh` for devices that list plugins in
  `MPC.settings` (needs root shell access); an older Crate Digger is replaced and your `channels.txt` is kept.

## Notes
- Tested on an MPC Live III. Not yet tested on a Force (32-bit) with this version.
- Without a Discogs token, Discogs allows 25 requests a minute: several searches in quick succession can still hit the limit (it says so, and how
  long to wait). A free token raises it to 60; see the README.
