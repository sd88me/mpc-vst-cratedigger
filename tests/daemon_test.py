#!/usr/bin/env python3
"""Offline test of the search daemon (src/bin/yt_dlp_daemon.py) against a fake Discogs: no device, no network.
    python3 tests/daemon_test.py              # must end with OK
    python3 tests/daemon_test.py --compare REF # also times another daemon file (e.g. the previous release) on the same fake
The fake answers like api.discogs.com: rate-limit headers and 429s over a 60 s window, gzip, keep-alive, a fixed delay per
call and a further one per new connection (the TLS handshake on the MPC), and 60% of releases with a YouTube video."""
import gzip, http.server, json, os, re, shutil, subprocess, sys, tempfile, threading, time, types

HERE = os.path.dirname(os.path.abspath(__file__))
DAEMON = os.path.join(HERE, "..", "src", "bin", "yt_dlp_daemon.py")
CALL_DELAY, CONNECT_DELAY = 0.12, 0.25


class Fake:
    def __init__(self, limit):
        self.limit, self.lock, self.calls, self.window, self.connections, self.too_many = limit, threading.Lock(), 0, [], 0, 0
        self.oembed = 0


def handler(fake):
    class H(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def setup(self):
            super().setup()
            with fake.lock:
                fake.connections += 1
            time.sleep(CONNECT_DELAY)

        def log_message(self, *a):
            pass

        def do_GET(self):
            m = re.search(r"/oembed\?.*v%3D[v](\d+)", self.path)
            if m:   # YouTube's oEmbed, not Discogs: no rate limit. Every 7th release's video is gone, every 11th can't be embedded
                rid = int(m.group(1))
                with fake.lock:
                    fake.oembed += 1
                return self.reply(404 if rid % 7 == 0 else 401 if rid % 11 == 0 else 200, {}, 0)
            time.sleep(CALL_DELAY)
            now = time.monotonic()
            with fake.lock:
                fake.window = [t for t in fake.window if now - t < 60]
                over = len(fake.window) >= fake.limit
                if not over:
                    fake.window.append(now)
                    fake.calls += 1
                else:
                    fake.too_many += 1
                remaining = fake.limit - len(fake.window)
            if over:
                return self.reply(429, {"message": "slow down"}, remaining, {"Retry-After": "30"})
            m = re.match(r"/releases/(\d+)$", self.path)
            if m:
                rid = int(m.group(1))
                videos = [{"uri": f"https://www.youtube.com/watch?v=v{rid}", "title": f"Artist {rid} - Track", "duration": 200}] \
                    if rid % 5 < 3 else []
                return self.reply(200, {"id": rid, "title": f"Record {rid}", "year": 1974, "country": "US", "genres": ["Funk"],
                                        "styles": ["Soul"], "artists": [{"name": f"Artist {rid}"}], "videos": videos,
                                        "images": [{"type": "secondary", "uri": f"https://img.example/{rid}-back.jpg"},
                                                   {"type": "primary", "uri": f"https://img.example/{rid}.jpg"}]}, remaining)
            if self.path.startswith("/database/search"):
                page = int(re.search(r"page=(\d+)", self.path).group(1)) if "page=" in self.path else 1
                return self.reply(200, {"pagination": {"pages": 5}, "results": [{"id": page * 1000 + i} for i in range(100)]},
                                  remaining)
            self.reply(404, {}, remaining)

        def reply(self, code, obj, remaining, extra=None):
            body = json.dumps(obj).encode()
            self.send_response(code)
            if "gzip" in (self.headers.get("Accept-Encoding") or ""):
                body = gzip.compress(body)
                self.send_header("Content-Encoding", "gzip")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Discogs-Ratelimit", str(fake.limit))
            self.send_header("X-Discogs-Ratelimit-Remaining", str(max(remaining, 0)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
    return H


def serve(limit):
    fake = Fake(limit)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler(fake))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return fake, srv, f"http://127.0.0.1:{srv.server_address[1]}"


class Daemon:
    def __init__(self, path, base, work, token=""):
        mod = os.path.join(work, "module")
        os.makedirs(os.path.join(mod, "secrets"), exist_ok=True)
        if token:
            open(os.path.join(mod, "secrets", "discogs_token.txt"), "w").write(token)
        env = dict(os.environ, CRATEDIG_DISCOGS_BASE=base, CRATEDIG_OEMBED_BASE=base, CRATEDIG_CACHE_DIR=os.path.join(work, "cache"),
                   WEBSTREAM_MODULE_DIR=mod, WEBSTREAM_PROVIDER_CONFIG=os.path.join(work, "none.json"))
        self.p = subprocess.Popen([sys.executable, "-I", path, os.path.join(work, "no-yt-dlp")], stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, text=True, env=env, cwd=work)
        assert self.p.stdout.readline().strip() == "READY"

    def ask(self, line, until=None):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        lines = []
        while True:
            out = self.p.stdout.readline().rstrip("\n")
            lines.append(out)
            if until is None or out.split("\t")[0] in until:
                return lines

    def search(self, filt):
        self.ask("CRATEDIG_FILTER\t" + json.dumps(filt))
        t = time.monotonic()
        lines = self.ask("CRATEDIG_SEARCH\t16", until=("SEARCH_END", "ERROR"))
        items = [l.split("\t") for l in lines if l.startswith("SEARCH_ITEM")]
        return items, time.monotonic() - t, lines[-1]

    def quit(self):
        self.ask("QUIT")
        self.p.wait(timeout=20)


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)
    print("  ok:", msg)


def timed_search(path, token=""):
    work = tempfile.mkdtemp()
    fake, srv, base = serve(60 if token else 25)
    try:
        d = Daemon(path, base, work, token)
        items, secs, end = d.search({"genre": "Funk / Soul", "decade": "1970s"})
        d.quit()
        return len(items), secs, fake.calls, fake.connections
    finally:
        srv.shutdown()
        shutil.rmtree(work, ignore_errors=True)


def test_search_and_cache():
    print("cold search, then a restart with the disk cache (no token: 25 calls a minute)")
    work = tempfile.mkdtemp()
    fake, srv, base = serve(25)
    try:
        d = Daemon(DAEMON, base, work)
        items, secs, end = d.search({"genre": "Funk / Soul", "decade": "1970s"})
        check(len(items) >= 6, f"{len(items)} results in {secs:.2f}s, {fake.calls} calls, {fake.connections} connections")
        check(all(i[5].startswith("https://www.youtube.com/") for i in items) and len({i[1] for i in items}) == len(items),
              "distinct releases with YouTube links")
        check(all(len(i) >= 14 and i[13] == f"https://img.example/{i[1]}.jpg" for i in items), "each result carries its front cover")
        check(not any(int(i[1]) % 7 == 0 for i in items) and fake.oembed > 0,
              f"no video YouTube says is gone ({fake.oembed} oEmbed checks); embedding-disabled ones stay")
        check(fake.calls <= 22 and fake.too_many == 0, f"within Discogs' limit (calls {fake.calls}, 429s {fake.too_many})")
        check(fake.connections <= 6 + 4, f"connections kept alive ({fake.connections} for {fake.calls} calls and the oEmbed checks: "
                                          "the fake serves both, one connection per worker each)")
        d.quit()
        check(os.path.exists(os.path.join(work, "cache", "discogs_releases.json")), "release cache saved on disk")
        time.sleep(0.2)
        with fake.lock:
            fake.window = []          # a minute later
            before = fake.calls
        d = Daemon(DAEMON, base, work)
        d.ask("CRATEDIG_FILTER\t" + json.dumps({"genre": "Funk / Soul", "decade": "1970s"}))
        cached = json.load(open(os.path.join(work, "cache", "discogs_releases.json")))
        check(len(cached) >= 16, f"{len(cached)} releases remembered")
        items, secs, end = d.search({"genre": "Funk / Soul", "decade": "1970s"})
        check(len(items) >= 14, f"{len(items)} results after restart (cache hits are free) in {secs:.2f}s, {fake.calls - before} calls")
        # rate limit: three searches back to back without a token must never be refused with something to show
        for n in range(3):
            items, secs, end = d.search({"genre": "Funk / Soul", "decade": "1970s"})
            check(len(items) > 0 or end.startswith("ERROR"), f"search {n + 3}: {len(items)} results, {end.split(chr(9))[0]}")
        check(fake.too_many <= 1, f"paced by the rate-limit headers ({fake.too_many} refused calls)")
        d.quit()
    finally:
        srv.shutdown()
        shutil.rmtree(work, ignore_errors=True)


def test_refill():
    print("background refill (token: 60 calls a minute)")
    work = tempfile.mkdtemp()
    fake, srv, base = serve(60)
    try:
        d = Daemon(DAEMON, base, work, token="t")
        first, secs1, _ = d.search({"style": "Soul"})
        time.sleep(4)                      # the user listens
        calls = fake.calls
        second, secs2, _ = d.search({"style": "Soul"})
        check(len(second) >= 8, f"second search {len(second)} results in {secs2:.2f}s (first {secs1:.2f}s)")
        check(secs2 < 0.5 and fake.calls == calls or secs2 < secs1 / 2, "second search answered from the refill")
        check(not ({i[1] for i in first} & {i[1] for i in second}), "no release repeated")
        third, secs3, _ = d.search({"style": "Jazz-Funk"})          # new filters: the refill's results are not used
        check(len(third) >= 8, f"filter change starts afresh ({len(third)} results in {secs3:.2f}s)")
        d.quit()
    finally:
        srv.shutdown()
        shutil.rmtree(work, ignore_errors=True)


def test_resolver():
    print("PREPARE / RESOLVE")
    sys.path.insert(0, os.path.dirname(DAEMON))
    import yt_dlp_daemon as D
    calls = []

    class YDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def extract_info(self, url, download=False):
            calls.append(url)
            time.sleep(0.4)
            return {"url": "https://media.example/" + url[-3:], "title": url, "http_headers": {"User-Agent": "UA"}}

    r = D.Resolver(types.SimpleNamespace(YoutubeDL=YDL))
    urls = [f"https://www.youtube.com/watch?v=00{i}" for i in range(4)]
    r.prepare(urls[:3])
    time.sleep(0.1)
    t = time.monotonic()
    f0 = r.resolve("youtube", urls[0])             # in flight: waits for it, doesn't start a second lookup
    check(f0[0].endswith("000") and calls.count(urls[0]) == 1, f"waited for the lookup in flight ({time.monotonic() - t:.2f}s)")
    time.sleep(1.0)
    t = time.monotonic()
    f2 = r.resolve("youtube", urls[2])
    check(time.monotonic() - t < 0.05 and f2[0].endswith("002"), "a prepared row resolves at once")
    f3 = r.resolve("youtube", urls[3])
    check(f3[0].endswith("003") and calls.count(urls[3]) == 1, "an unprepared row is looked up as before")
    r.prepare(urls)                                # all done already: nothing looked up again
    time.sleep(0.6)
    check(len(calls) == 4, f"nothing resolved twice ({len(calls)} lookups)")


if __name__ == "__main__":
    test_search_and_cache()
    test_refill()
    test_resolver()
    if "--compare" in sys.argv:
        ref = sys.argv[sys.argv.index("--compare") + 1]
        print("timing, one cold 16-result search on the same fake (delay per call %.2fs, per connection %.2fs)" % (CALL_DELAY, CONNECT_DELAY))
        for name, path in (("before", ref), ("after", DAEMON)):
            n, secs, calls, conns = timed_search(path)
            print(f"  {name:6s} {n:2d} results  {secs:5.2f}s  {calls} calls  {conns} connections")
    print("OK")
