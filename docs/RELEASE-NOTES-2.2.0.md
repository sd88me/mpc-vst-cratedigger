# Crate Digger 2.2.0

A second look: the deck. Everything in 2.1.0, plus a turntable, a crate and an amp, switched with one key. The sampler look is unchanged.

## What's new
- **DECK LOOK.** A key at the top of every sampler page switches to the deck (on the deck, DECK LOOK on FIND switches back). It applies to every
  Crate Digger on the MPC and stays until you switch back; projects do not change it.
- **The turntable.** The record's centre label is the display: status, what is playing and the time, with the record's cover shown as dots behind
  the glass. The record turns while it plays on 64-bit MPCs (Live III and other Gen2 units); on 32-bit MPCs it stays still to save CPU.
- **Drag the tonearm to move through the track.** It follows the track as it plays; drag it up towards the label to go forward, down to go back,
  and the needle drops where you let go. Far jumps restart the stream at that point.
- **Pitch and speed.** A real pitch fader (+-8 %, with RESET) and 33 / 45 keys: the track plays faster or slower, pitch and tempo together, like a
  turntable. They are saved with the project and work in both looks.
- **The crate and the amp (PLAY).** The results are sleeves in a crate with PAGE tabs; the amp in front has two VU meters, GAIN, the search status
  and SEARCH.
- **Consoles on FILTERS and FIND.** FILTERS: one display with all five filters (long names wrap onto two lines) and a fader with up / down keys for
  each. FIND: DISCOGS / YOUTUBE / CHANNEL source keys, a display with the source's settings, faders for the minimum and maximum length under
  their readouts, MUSIC ONLY, the channel selector and a TEXT panel you tap to type.
- **Q-Links on PLAY** (both looks): pitch, gain, the results page and the tonearm, then the transport. The deck draws no Q-Link frame.

## Install
Download the package for your device, unzip it and follow `INSTALL.txt` (also in the README).
- `Crate-Digger-2.2.0-VST2-Plugins-aarch64.zip`: MPC Live III and other 64-bit MPCs. Copy the plugin folder into `VST2 Plugins` on a drive.
- `Crate-Digger-2.2.0-VST2-Plugins-armv7.zip`: Force and other 32-bit MPCs. Includes `install-force.sh` for devices that list plugins in
  `MPC.settings` (needs root shell access); an older Crate Digger is replaced and your `channels.txt` is kept.

## Notes
- Tested on an MPC Live III. Not yet tested on a Force (32-bit) with this version.
- Projects saved with 2.1.0, 2.0.0 and 1.x load (new controls are added after the old ones).
- The deck look's popup keyboard is the sampler's (cream keys).
