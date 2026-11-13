"""Downloads that show their progress in the log and never hang (switzerlandNG, 2026-11-09).

michi: "voglio che tutti i download siano tracciabili nei log con la percentuale". Every download of the build goes
through here:
  fetch(url, dest, ...)        one file, streamed to dest.part and renamed when complete; resumed with a Range
                               request after a cut connection; its own percentage line every EVERY s when it is big
  get(url, ...)                a small request (STAC pages, WFS pages): retries with backoff, (connect, read) timeouts
  get_range(session, url, a, b) one byte range of a remote file (swissTLM3D's zip read in place, the OSM ranges)
  Progress(label, files)       the totals of a step: "swisstopo: 45 % (12 of 30 files, 0.84 of ~1.9 GB, 6.2 MB/s)"

No silent hang: every request has a connect and a read timeout, and a watchdog thread shuts the socket of any
transfer that received less than MIN_RATE bytes/s over STALL s (a server that trickles a byte a minute never trips a
read timeout); the transfer is then retried from where it stopped. A file that fails ATTEMPTS times raises
DownloadError with the URL and the last error, so the step fails with a clear message (and the app retries the
step, which skips the finished files) instead of waiting for ever.
"""
import json
import os
import sys
import threading
import time

import requests

CONNECT = 30.0                 # s to open a connection
READ = 90.0                    # s without a byte on an open connection
STALL = 120.0                  # s over which a transfer must average MIN_RATE, or it is cut and retried
MIN_RATE = 4096                # bytes per s
EVERY = 10.0                   # s between two progress lines (of one file, of a step's totals)
BIG = 16 << 20                 # files from this size get progress lines of their own
ATTEMPTS = 6
CHUNK = 1 << 16
UA = {"User-Agent": "switzerlandNG map builder (github.com/wintrymichi/magliasinaNG)"}
# answers that will not change on a retry (a missing tile, a wrong request); 403 is often a short ban: one retry
PERMANENT = {400, 401, 404, 405, 410, 411, 413, 414, 416, 422}


class DownloadError(RuntimeError):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status            # the HTTP status of the last answer, when there was one (403: a ban)


class Stalled(IOError):
    pass


SAY = None                     # another place for the lines (the app's build log), else stdout


_SAY_LOCK = threading.Lock()


def say(*a):
    """One whole line (threads side by side glued their lines together with print, 2026-11-09)."""
    text = " ".join(str(x) for x in a)
    with _SAY_LOCK:
        if SAY is not None:
            SAY(text)
        else:
            sys.stdout.write(text + "\n")
            sys.stdout.flush()


def human(n):
    n = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return ("%.0f %s" if unit in ("B", "KB") else "%.1f %s" if n < 100 else "%.0f %s") % (n, unit)
        n /= 1024


def short(url, n=70):
    u = url.split("?")[0]
    return u if len(u) <= n else "..." + u[-(n - 3):]


def backoff(attempt):
    return min(60.0, 5.0 * 2 ** attempt)


def replace(src, dst, tries=20):
    """os.replace, again for a while when Windows answers PermissionError (an antivirus or the indexer holding the
    new file open for a moment)."""
    for k in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if k == tries - 1:
                raise
            time.sleep(0.5 + 0.25 * k)


# ---------------------------------------------------------------------------------------------- the stall watchdog
class _Transfer:
    __slots__ = ("resp", "t0", "n0", "n", "stalled", "what")

    def __init__(self, resp, what):
        self.resp, self.what = resp, what
        self.t0, self.n0, self.n, self.stalled = time.time(), 0, 0, False


_active = set()
_alock = threading.Lock()
_watch = None


def _socket(resp):
    """The socket under a requests response (urllib3 1.x and 2.x), or None."""
    raw = getattr(resp, "raw", None)
    for path in (("_connection", "sock"), ("_fp", "fp", "raw", "_sock"), ("connection", "sock")):
        o = raw
        for a in path:
            o = getattr(o, a, None)
            if o is None:
                break
        if o is not None and hasattr(o, "shutdown"):
            return o
    return None


def _cut(tr):
    tr.stalled = True
    s = _socket(tr.resp)
    try:
        if s is not None:
            import socket
            s.shutdown(socket.SHUT_RDWR)          # wakes the thread blocked in recv() at once
    except OSError:
        pass
    try:
        tr.resp.close()
    except Exception:
        pass


def _watchdog():
    while True:
        time.sleep(5.0)
        now = time.time()
        with _alock:
            act = list(_active)
        for tr in act:
            if tr.stalled:
                continue
            if now - tr.t0 >= STALL:
                if tr.n - tr.n0 < MIN_RATE * (now - tr.t0):
                    say("  download stalled (%s in %.0f s): %s, cut and retried" % (human(tr.n - tr.n0), now - tr.t0,
                                                                                   tr.what))
                    _cut(tr)
                else:
                    tr.t0, tr.n0 = now, tr.n


def _register(resp, what):
    global _watch
    tr = _Transfer(resp, what)
    with _alock:
        _active.add(tr)
        if _watch is None:
            _watch = threading.Thread(target=_watchdog, name="netio-watchdog", daemon=True)
            _watch.start()
    return tr


def _unregister(tr):
    with _alock:
        _active.discard(tr)


# ---------------------------------------------------------------------------------------------- progress lines
class Progress:
    """The downloads of a step together. files: how many are queued (0: unknown). Thread safe. A line at most every
    EVERY s, and one at the end (done())."""

    def __init__(self, label, files=0, total=0):
        self.label, self.files, self.total = label, files, total
        self.sizes = {}                  # file -> bytes expected
        self.got = 0                     # bytes received in this run
        self.skipped = 0                 # bytes already on the disk (finished earlier or resumed)
        self.ended = 0
        self.failed = 0
        self.lock = threading.Lock()
        self.t0 = self.last = time.time()

    def expect(self, key, size):
        if size:
            with self.lock:
                self.sizes[key] = size

    def add(self, n):
        with self.lock:
            self.got += n
        self.line()

    def have(self, n):
        """Bytes found on the disk (a resumed .part)."""
        with self.lock:
            self.skipped += n

    def file_done(self, ok=True):
        with self.lock:
            self.ended += 1
            self.failed += not ok
        self.line(force=self.files and self.ended == self.files)

    def percent(self):
        if self.total:
            return 100.0 * min(1.0, (self.got + self.skipped) / self.total), False
        if self.files:
            known = list(self.sizes.values())
            if known and len(known) >= self.files:
                return 100.0 * min(1.0, (self.got + self.skipped) / sum(known)), False
            if known:                            # the sizes not known yet estimated by the mean of the others
                est = sum(known) + (self.files - len(known)) * sum(known) / len(known)
                p = (self.got + self.skipped) / est
                return 100.0 * min(max(p, self.ended / self.files), 0.999 if self.ended < self.files else 1.0), True
            return 100.0 * self.ended / self.files, True
        return None, True

    def line(self, force=False):
        now = time.time()
        if not force and now - self.last < EVERY:
            return
        with self.lock:
            if not force and now - self.last < EVERY:
                return
            self.last = now
            p, approx = self.percent()
            el = max(now - self.t0, 1e-6)
            parts = []
            if self.files:
                parts.append("%d of %d files" % (self.ended, self.files))
            tot = self.total or (sum(self.sizes.values()) if self.files and len(self.sizes) >= self.files else 0)
            have = self.got + self.skipped
            parts.append("%s of %s%s" % (human(have), "~" if approx and not tot else "", human(tot)) if tot else human(have))
            parts.append("%s/s" % human(self.got / el))
            if self.failed:
                parts.append("%d failed" % self.failed)
            pct = ("%s%.0f %%" % ("~" if approx else "", p)) if p is not None else "?"
        say("[download] %s: %s (%s)" % (self.label, pct, ", ".join(parts)))

    def done(self):
        if time.time() - self.last > 1.0:
            self.line(force=True)
        el = time.time() - self.t0
        say("[download] %s: finished in %.0f s, %s received%s" % (self.label, el, human(self.got),
                                                                 ", %d failed" % self.failed if self.failed else ""))


class _FileLine:
    """The percentage line of one big file."""

    def __init__(self, name, size, start=0):
        self.name, self.size, self.n, self.start = name, size, start, start
        self.t0 = self.last = time.time()

    def add(self, k, force=False):
        self.n += k
        now = time.time()
        if self.size >= BIG and (force or now - self.last >= EVERY):
            self.last = now
            rate = (self.n - self.start) / max(now - self.t0, 1e-6)
            left = (self.size - self.n) / rate if rate > 0 else 0
            say("[download]   %s: %.0f %% of %s (%s/s, %s left)" % (self.name, 100.0 * self.n / max(self.size, 1),
                                                                   human(self.size), human(rate), _dur(left)))


def _dur(s):
    s = int(s)
    return "%d s" % s if s < 90 else "%d min" % round(s / 60) if s < 5400 else "%.1f h" % (s / 3600)


# ---------------------------------------------------------------------------------------------- requests
_tls = threading.local()


def session():
    """One kept-alive session per thread (requests.Session is not thread safe)."""
    s = getattr(_tls, "s", None)
    if s is None:
        s = _tls.s = requests.Session()
        s.headers.update(UA)
    return s


def _check(r, url):
    if r.status_code in PERMANENT:
        raise DownloadError("%s: HTTP %d (not retried)" % (short(url), r.status_code))
    r.raise_for_status()


def get(url, params=None, data=None, method=None, timeout=None, attempts=ATTEMPTS, what=None, headers=None):
    """A small request (the whole answer in memory): the Response. Retried with backoff; DownloadError at the end."""
    method = method or ("POST" if data is not None else "GET")
    what = what or short(url)
    last = None
    for attempt in range(attempts):
        tr = None
        try:
            r = session().request(method, url, params=params, data=data, headers=headers, stream=True,
                                  timeout=(CONNECT, timeout or READ))
            tr = _register(r, what)
            _check(r, url)
            buf = bytearray()
            for c in r.iter_content(CHUNK):
                buf += c
                tr.n += len(c)
            if tr.stalled:
                raise Stalled("stalled")
            r._content = bytes(buf)
            r._content_consumed = True
            return r
        except DownloadError:
            raise
        except Exception as e:
            last = e
            if tr is not None and tr.stalled:
                e = Stalled("less than %s/s for %.0f s" % (human(MIN_RATE), STALL))
            if r_status(e) == 403 and attempt >= 1:
                break
            if attempt < attempts - 1:
                say("  retry %d/%d in %.0f s: %s: %s" % (attempt + 1, attempts - 1, backoff(attempt), what,
                                                         str(e)[:200]))
                time.sleep(backoff(attempt))
        finally:
            if tr is not None:
                _unregister(tr)
    raise DownloadError("%s failed after %d attempts: %s" % (what, attempts, str(last)[:300]), status=r_status(last))


def r_status(e):
    resp = getattr(e, "response", None)
    return getattr(resp, "status_code", None)


def get_json(url, params=None, **kw):
    return get(url, params=params, **kw).json()


PART_MAX_AGE = 6 * 3600       # a part with no validator is resumed only this long after it was last written


def _part_meta(part, meta_p, pos):
    """What the part on disk was cut from: {"validator", "total"}, or {} when it cannot be trusted (none written by
    this module, or too old to resume without a validator). The caches outlive builds and the Geofabrik pbf or the
    GWR zip change every day: yesterday's part plus today's tail is a corrupt file of the right size (review 2)."""
    if not pos:
        return {}
    try:
        m = json.load(open(meta_p, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not m.get("validator") and time.time() - os.path.getmtime(part) > PART_MAX_AGE:
        return {}
    return m


def _save_meta(meta_p, r, size):
    et = r.headers.get("ETag") or ""
    v = et if et and not et.startswith("W/") else (r.headers.get("Last-Modified") or "")
    try:
        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump({"validator": v, "total": size or None}, f)
    except OSError:
        pass


def _drop_part(part, meta_p):
    for q in (part, meta_p):
        try:
            os.remove(q)
        except OSError:
            pass


def _content_range(r):
    """(first byte, total or None) of a 206 answer."""
    cr = r.headers.get("Content-Range", "")
    try:
        a = cr.split()[1]
        rng, tot = a.split("/")
        return int(rng.split("-")[0]), (int(tot) if tot.isdigit() else None)
    except (IndexError, ValueError):
        return None, None


def fetch(url, dest, progress=None, name=None, attempts=ATTEMPTS, headers=None, expect_size=None):
    """url into dest (dest.part until it is whole; resumed after a cut). (dest, "skip" | "ok"); DownloadError when
    it fails attempts times."""
    if os.path.exists(dest):
        if progress is not None:
            progress.expect(dest, os.path.getsize(dest))
            progress.have(os.path.getsize(dest))
            progress.file_done()
        return dest, "skip"
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    part = dest + ".part"
    meta_p = part + ".json"
    name = name or os.path.basename(dest)
    last = None
    counted = 0                                  # bytes of this file already added to progress
    for attempt in range(attempts):
        pos = os.path.getsize(part) if os.path.exists(part) else 0
        meta = _part_meta(part, meta_p, pos)
        if not meta and pos:
            pos = 0                              # a part of unknown origin: never glue it to today's file
        h = dict(headers or {})
        # the byte counts below must be the file's own bytes, not a gzipped answer decoded on the way (review 2)
        h["Accept-Encoding"] = "identity"
        if pos:
            h["Range"] = "bytes=%d-" % pos
            if meta.get("validator"):
                h["If-Range"] = meta["validator"]   # the file changed since: the server sends it whole (200)
        tr = None
        try:
            r = session().get(url, headers=h, stream=True, timeout=(CONNECT, READ))
            tr = _register(r, name)
            with r:
                if pos and r.status_code == 416:
                    # whole already only if the part is as long as the file was (and still is, when the server says)
                    cr = r.headers.get("Content-Range", "")
                    now_total = int(cr.rsplit("/", 1)[1]) if "/" in cr and cr.rsplit("/", 1)[1].isdigit() else None
                    if pos != meta.get("total") or (now_total is not None and now_total != pos):
                        _drop_part(part, meta_p)
                        raise IOError("the part on disk does not fit the file on the server: from the start")
                    size = pos
                else:
                    _check(r, url)
                    if pos and r.status_code != 206:          # no ranges, or the file changed: from the start
                        pos = 0
                    if pos:
                        start, total = _content_range(r)
                        if start != pos or (meta.get("total") and total and total != meta["total"]):
                            _drop_part(part, meta_p)
                            raise IOError("the server answered bytes from %s (of %s), asked from %d (of %s): "
                                          "from the start" % (start, total, pos, meta.get("total")))
                    clen = int(r.headers.get("Content-Length") or 0)
                    size = (pos + clen) if clen else (expect_size or 0)
                    if not pos:
                        _save_meta(meta_p, r, size)
                    if progress is not None:
                        progress.expect(dest, size)
                        if attempt == 0 and pos:
                            progress.have(pos)
                            counted = pos
                    fl = _FileLine(name, size, pos)
                    if attempt == 0 and size >= BIG:
                        say("[download]   %s: %s%s" % (name, human(size), ", resumed at %.0f %%" % (100.0 * pos / size)
                                                       if pos else ""))
                    with open(part, "r+b" if pos else "wb") as f:
                        f.seek(pos)
                        f.truncate()
                        for c in r.iter_content(CHUNK):
                            f.write(c)
                            k = len(c)
                            tr.n += k
                            fl.add(k)
                            if progress is not None:
                                if pos + fl.n - fl.start > counted:
                                    progress.add(k)
                                    counted += k
                    if tr.stalled:
                        raise Stalled("stalled")
                    got = os.path.getsize(part)
                    if size and got != size:
                        raise IOError("cut at %s of %s" % (human(got), human(size)))
                    if size >= BIG:
                        fl.add(0, force=True)
            replace(part, dest)
            try:
                os.remove(meta_p)
            except OSError:
                pass
            if progress is not None:
                progress.file_done()
            return dest, "ok"
        except DownloadError:
            if progress is not None:
                progress.file_done(False)
            raise
        except Exception as e:
            last = e
            if tr is not None and tr.stalled:
                e = Stalled("less than %s/s for %.0f s" % (human(MIN_RATE), STALL))
            if r_status(e) == 403 and attempt >= 1:
                break
            if attempt < attempts - 1:
                say("  retry %d/%d in %.0f s: %s: %s" % (attempt + 1, attempts - 1, backoff(attempt), name,
                                                         str(e)[:200]))
                time.sleep(backoff(attempt))
        finally:
            if tr is not None:
                _unregister(tr)
    if progress is not None:
        progress.file_done(False)
    raise DownloadError("%s failed after %d attempts (%s): %s" % (name, attempts, short(url), str(last)[:300]))


def get_range(url, a, b, progress=None, attempts=ATTEMPTS, what=None, sink=None):
    """Bytes a..b (inclusive) of url; with sink (a file opened r+b) written there at offset a instead. Resumed from
    where a cut left it."""
    what = what or "%s bytes %d-%d" % (os.path.basename(url.split("?")[0]), a, b)
    buf = bytearray()
    pos, last = a, None
    for attempt in range(attempts):
        tr = None
        try:
            r = session().get(url, headers={"Range": "bytes=%d-%d" % (pos, b), "Accept-Encoding": "identity"},
                              stream=True, timeout=(CONNECT, READ))
            tr = _register(r, what)
            with r:
                _check(r, url)
                if r.status_code != 206:
                    raise DownloadError("%s: the server ignored the range (HTTP %d)" % (short(url), r.status_code))
                if sink is not None:
                    sink.seek(pos)
                for c in r.iter_content(CHUNK):
                    if pos + len(c) > b + 1:              # a server that sends past the range end
                        c = c[:b + 1 - pos]
                    if sink is not None:
                        sink.write(c)
                    else:
                        buf += c
                    pos += len(c)
                    tr.n += len(c)
                    if progress is not None:
                        progress.add(len(c))
                    if pos > b:
                        break
            if tr.stalled:
                raise Stalled("stalled")
            if pos != b + 1:
                raise IOError("range cut at %d of %d bytes" % (pos - a, b + 1 - a))
            return bytes(buf) if sink is None else b + 1 - a
        except DownloadError:
            raise
        except Exception as e:
            last = e
            if tr is not None and tr.stalled:
                e = Stalled("less than %s/s for %.0f s" % (human(MIN_RATE), STALL))
            if attempt < attempts - 1:
                say("  retry %d/%d in %.0f s: %s: %s" % (attempt + 1, attempts - 1, backoff(attempt), what,
                                                         str(e)[:200]))
                time.sleep(backoff(attempt))
        finally:
            if tr is not None:
                _unregister(tr)
    raise DownloadError("%s failed after %d attempts: %s" % (what, attempts, str(last)[:300]))


def head(url, attempts=4):
    """(size, takes ranges) of url, (0, False) when it cannot be told."""
    for attempt in range(attempts):
        try:
            h = session().head(url, allow_redirects=True, timeout=(CONNECT, 60))
            if h.status_code in PERMANENT:
                return 0, False
            h.raise_for_status()
            return int(h.headers.get("Content-Length") or 0), h.headers.get("Accept-Ranges", "") == "bytes"
        except Exception as e:
            if attempt < attempts - 1:
                say("  retry HEAD %s: %s" % (short(url), str(e)[:200]))
                time.sleep(backoff(attempt))
    return 0, False


def fetch_parallel(url, dest, parts=4, name=None, min_mb=64):
    """A big file in `parts` byte ranges at once (OpenStreetMap's Geofabrik extracts): one connection took most of
    the Axenstrasse's OSM step. Falls back to fetch() when the server takes no ranges. (dest, status)."""
    if os.path.exists(dest):
        return dest, "skip"
    name = name or os.path.basename(dest)
    size, ranges = head(url)
    if not ranges or size < min_mb * 2 ** 20 or parts < 2:
        prog = Progress(name, files=1)
        try:
            return fetch(url, dest, prog, name)
        finally:
            prog.done()
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    part = dest + ".part"
    with open(part, "wb") as f:
        f.truncate(size)
    cuts = [size * k // parts for k in range(parts + 1)]
    prog = Progress("%s (%d connections)" % (name, parts), total=size)
    say("[download] %s: %s in %d ranges" % (name, human(size), parts))

    def one(k):
        with open(part, "r+b") as f:
            return get_range(url, cuts[k], cuts[k + 1] - 1, prog, what="%s range %d" % (name, k), sink=f)

    try:
        with ThreadPoolExecutor(parts) as pool:
            list(pool.map(one, range(parts)))
    except DownloadError as e:
        prog.done()
        say("  %s: %s; one connection instead" % (name, e))
        os.remove(part)
        prog = Progress(name, files=1)
        try:
            return fetch(url, dest, prog, name)
        finally:
            prog.done()
    prog.done()
    if os.path.getsize(part) != size:
        raise DownloadError("%s: %s of %s on the disk" % (name, human(os.path.getsize(part)), human(size)))
    replace(part, dest)
    return dest, "ok (%d ranges, %s)" % (parts, human(size))


if __name__ == "__main__":                        # python netio.py <url> <dest>: a manual test
    p = Progress("test", files=1)
    print(fetch(sys.argv[1], sys.argv[2], p))
    p.done()
