# Troubleshooting

## Install / upgrade

Download the package for your device from [Releases](https://github.com/sd88me/mpc-vst-cratedigger/releases) and follow its `INSTALL.txt` (or the README).
On a Force run `install-force.sh` from the unzipped package as root; it stops the MPC (save your project first), installs the plugin, and restarts it.
An older Crate Digger is replaced and your `channels.txt` is kept.

## Search shows an "error" status

The SEARCH line on the plugin screen says what went wrong, for example `DISCOGS REJECTED THE TOKEN (HTTP
401)` or `NO PLAYABLE VIDEO IN 12 RELEASES TRIED, SEARCH AGAIN`. The line holds about 45 characters, so
the full text is also written to a log file on the device (see below).

| SEARCH line says | Meaning | Fix |
|---|---|---|
| `DISCOGS RATE LIMIT HIT, RETRY IN ~Ns` | Discogs said too many requests | Add a token (below), or wait N seconds |
| `DISCOGS REJECTED THE TOKEN (HTTP 401/403)` | The token is wrong or revoked | Re-check `webstream_providers.json` |
| `NO NETWORK: DNS LOOKUP FAILED` / `NO NETWORK: ...` | The device can't reach the internet | Check the device's network connection |
| `NO ANSWER FROM DISCOGS (TIMED OUT)` | Discogs or the connection is too slow | Try again |
| `DISCOGS SERVER ERROR (HTTP 5xx), TRY AGAIN` | Discogs is having a bad moment | Try again later |
| `NO DISCOGS RELEASES MATCH THESE FILTERS` | The filter combination has no releases | Set a filter back to ANY |
| `NO PLAYABLE VIDEO IN N RELEASES TRIED, ...` | Releases were found, none had a YouTube video | Search again, or loosen the filters |
| `SEARCH HELPER ...` | The background helper didn't start or stopped answering | Restart MPC; report it if it repeats |

The STATUS line names why a track would not play: `PRIVATE VIDEO`, `VIDEO REMOVED`, `COPYRIGHT`,
`REGION BLOCKED`, `AGE / LOGIN`, `UNAVAILABLE`, `RATE LIMITED`, `TIMED OUT`, `NO NETWORK`,
`YT-DLP MISSING` or `RESOLVE FAILED`; NOW PLAYING then shows the track and yt-dlp's own wording. A
track that simply played to the end shows `TRACK ENDED`.

### 1. Set a Discogs token (fixes most search errors)

Without a token, the device is capped at 25 Discogs requests/minute, and a single search can
use up to ~24 of those (one page-count probe, up to 3 page fetches, and up to 4 release
lookups per result) — so a second search shortly after, or another device on the same
network, easily trips a rate limit. A free personal token raises the limit to 60/min:

1. Get a token at <https://www.discogs.com/settings/developers>.
2. On the device, create/edit `/data/UserData/schwung/config/webstream_providers.json`:
   ```json
   { "providers": { "cratedig": { "token": "YOUR_DISCOGS_PERSONAL_TOKEN" } } }
   ```

### 2. Check the runtime log

```sh
ssh root@<device-ip>
cat /tmp/webstream-runtime.log
```

Look for lines starting with `search error:` — the most recent one is the actual cause, in the
same words the SEARCH line used (untruncated). Anything that isn't in the table above is a cause
we haven't seen: report it (see below) with the exact line.

If the log file doesn't exist yet, no search has failed since the last MPC restart — try
reproducing the issue, then check again.

## Reporting a search failure

Open an issue at <https://github.com/sd88me/mpc-vst-cratedigger/issues> with:
- The exact `search error:` line from `/tmp/webstream-runtime.log`.
- Whether a Discogs token is configured.
- The genre/style/decade/region/country filters in use at the time.

## Helping us debug "search stops responding" or "playback breaks after a new search"

These two are still open (see [ROADMAP.md](ROADMAP.md)) and haven't been reproduced yet off a
device, so the fastest way to move them forward is a log capture while reproducing one. As of
this version, every log line in both files below is timestamped (`[seconds.milliseconds]`), so
the two logs can be read together as one timeline of what happened and in what order.

1. Reproduce the issue:
   - **Search gets stuck**: trigger a slow/failing search (e.g. searching right after another
     one, or with a filter combo that returns nothing quickly), wait for the `error` status,
     then press SEARCH again and confirm it doesn't restart.
   - **Playback breaks after a new search**: start a track playing from one search's results,
     then run a new search (with the track still playing) and try to select a track from the
     new results.
2. Immediately after, grab both log files:
   ```sh
   ssh root@<device-ip> cat /tmp/webstream-runtime.log
   ssh root@<device-ip> cat /tmp/cratedigger_vst.log
   ```
3. Attach both (full, not just the tail) to an issue at
   <https://github.com/sd88me/mpc-vst-cratedigger/issues>, along with:
   - What you did, step by step, and roughly when (so it can be matched to the timestamps).
   - Whether a Discogs token is configured.

`/tmp/webstream-runtime.log` now also logs, for every search dispatch, whether it ran
immediately, queued behind one already running, or restarted a stuck daemon — and for every new
track selection, what the previous stream's state was (still resolving, still playing, etc.).
`/tmp/cratedigger_vst.log` logs every SEARCH press and every result tap from the plugin's own
side, with the same timestamp clock.
