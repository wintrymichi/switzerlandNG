"""Updates of switzerlandNG: always to the newest commit of the main branch of wintrymichi/switzerlandNG on GitHub.

    python -m app.update            update now (the launchers: "Update switzerlandNG.bat", update-switzerlandng.sh)
    python -m app.update --check    only say whether a newer version is out
    python -m app.update --full     download the whole branch again (the repair of a broken install)

An install made by an updater or by the installer remembers its commit in .switzerlandng.json at the top of the
folder. From a known commit an update downloads only the files that changed (GitHub's compare of the two commits, each
file checked against its git blob hash); with no known commit, or when the compare cannot be used (more than 300
files, a rewritten branch), it downloads the branch's archive of the newest commit (about 330 MB) and writes every file
of it. Files the old version had and the new one has not are deleted only when they are in the old version's file
list (.switzerlandng-files.txt): nothing else in the folder (the runtime, a data folder put there by hand) is touched.
Builds keep their own copy of the pipeline (jobs.py, b.code), so an update never changes a build already started.
SWISSNG_REF chooses another branch or tag, GITHUB_TOKEN raises GitHub's limit of 60 requests an hour.
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from . import REPO, VERSION

OWNER_REPO = "wintrymichi/switzerlandNG"
REF = os.environ.get("SWISSNG_REF", "main")
STATE = os.path.join(REPO, ".switzerlandng.json")
FILES = os.path.join(REPO, ".switzerlandng-files.txt")
API = "https://api.github.com/repos/" + OWNER_REPO
RAW = "https://raw.githubusercontent.com/" + OWNER_REPO
CODELOAD = "https://codeload.github.com/" + OWNER_REPO + "/tar.gz/"
KEEP = (".switzerlandng.json", ".switzerlandng-files.txt", ".git/", "beamng/builder/.runtime/")
CRLF = (".bat", ".ps1")                       # .gitattributes: eol=crlf (raw files come as stored, with LF)
EXEC = (".sh", ".command")
COMPARE_MAX = 300                             # GitHub lists at most 300 files of a compare
RESTART_CODE = 75                             # the app's exit code that makes the launchers start again


class UpdateError(Exception):
    pass


def _headers(accept="application/vnd.github+json", url=API):
    h = {"User-Agent": "switzerlandNG/" + VERSION, "Accept": accept}
    tok = os.environ.get("GITHUB_TOKEN")
    if tok and url.startswith(API):          # raw.githubusercontent.com answers 404 to a token it does not take
        h["Authorization"] = "Bearer " + tok
    return h


def _get(url, accept="application/vnd.github+json", timeout=30):
    req = urllib.request.Request(url, headers=_headers(accept, url))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code == 403 and "rate limit" in e.read().decode("utf-8", "replace").lower():
            raise UpdateError("GitHub's limit of 60 checks an hour is used up: try again in an hour.")
        raise UpdateError(f"GitHub answered {e.code} for {url}")
    except OSError as e:
        raise UpdateError(f"no connection to GitHub ({e})")


def installed():
    """{commit, ref, date} of this install, or {} when it is not known (a zip unpacked by hand, a git checkout)."""
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def latest():
    """The newest commit of the branch: {commit, date, message}."""
    d = json.loads(_get(f"{API}/commits/{urllib.parse.quote(REF, safe='')}"))
    return {"commit": d["sha"], "date": d["commit"]["committer"]["date"],
            "message": d["commit"]["message"].splitlines()[0][:200]}


def git_checkout():
    return os.path.isdir(os.path.join(REPO, ".git"))


def check():
    """What the app shows: {installed, latest, available, git}. Never raises (error in "error")."""
    have = installed()
    out = {"installed": have.get("commit"), "installed_date": have.get("date"), "git": git_checkout(),
           "latest": None, "available": False, "error": None, "checked": time.time()}
    try:
        new = latest()
    except UpdateError as e:
        out["error"] = str(e)
        return out
    out.update(latest=new["commit"], latest_date=new["date"], latest_message=new["message"])
    if out["git"]:
        try:
            head = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True,
                                  timeout=20).stdout.strip()
            out["installed"] = head or None
        except (OSError, subprocess.SubprocessError):
            pass
    out["available"] = out["installed"] != new["commit"]
    return out


def blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _safe(rel):
    rel = rel.replace("\\", "/")
    if rel.startswith("/") or any(p in ("..", "") for p in rel.split("/")) or ":" in rel:
        raise UpdateError(f"refused path {rel!r}")
    if any(rel == k.rstrip("/") or rel.startswith(k) for k in KEEP):
        return None
    return rel


def _crlf(rel, data):
    if rel.lower().endswith(CRLF) and b"\r\n" not in data:
        return data.replace(b"\n", b"\r\n")
    return data


def _write(rel, data):
    dst = os.path.join(REPO, *rel.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".swissng-new"
    with open(tmp, "wb") as f:
        f.write(data)
    if rel.endswith(EXEC) and os.name != "nt":
        os.chmod(tmp, 0o755)
    os.replace(tmp, dst)                     # Windows too: a .py of the running app is not locked


def _remove(rel):
    p = os.path.join(REPO, *rel.split("/"))
    if os.path.isfile(p):
        os.remove(p)
        d = os.path.dirname(p)               # empty folders the old version left
        while d != REPO and os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            d = os.path.dirname(d)


def _old_files():
    try:
        return [l.rstrip("\n") for l in open(FILES, encoding="utf-8") if l.strip()]
    except OSError:
        return None


def _save_state(commit, date, files):
    with open(FILES + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(sorted(files)) + "\n")
    os.replace(FILES + ".tmp", FILES)
    with open(STATE + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"commit": commit, "ref": REF, "date": date, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                                        time.gmtime())}, f, indent=1)
    os.replace(STATE + ".tmp", STATE)


def _raw(sha, rel):
    """One file of a commit: a few tries at raw.githubusercontent.com (a busy CDN), then the contents API (counts
    towards the hourly limit)."""
    url = f"{RAW}/{sha}/{urllib.parse.quote(rel)}"
    for wait in (0, 3, 10):
        time.sleep(wait)
        try:
            return _get(url, accept="*/*", timeout=120)
        except UpdateError:
            pass
    return _get(f"{API}/contents/{urllib.parse.quote(rel)}?ref={sha}", accept="application/vnd.github.raw", timeout=120)


def _delta(base, new, say):
    """Only the changed files, or None when the compare cannot be used."""
    files, page = [], 1
    while True:
        try:
            d = json.loads(_get(f"{API}/compare/{base}...{new}?per_page=100&page={page}"))
        except UpdateError as e:
            say(f"  compare not available ({e}): the whole version is downloaded")
            return None
        if d.get("status") not in ("ahead", "identical"):
            say(f"  the branch was rewritten (compare: {d.get('status')}): the whole version is downloaded")
            return None
        part = d.get("files") or []
        files += part
        if len(part) < 100 or page >= 3:
            break
        page += 1
    if len(files) >= COMPARE_MAX:
        say(f"  {len(files)} changed files: the whole version is downloaded")
        return None
    got, gone = {}, []
    for f in files:
        st = f["status"]
        if st == "renamed" and f.get("previous_filename"):
            gone.append(f["previous_filename"])
        if st == "removed":
            gone.append(f["filename"])
            continue
        if st == "unchanged":
            continue
        rel = _safe(f["filename"])
        if rel is None:
            continue
        data = _raw(new, rel)
        if f.get("sha") and blob_sha(data) != f["sha"]:
            raise UpdateError(f"{rel}: the downloaded file does not match GitHub's hash")
        got[rel] = data
        say(f"  {st:9s} {rel} ({len(data) / 1024:.0f} KB)")
    return got, [g for g in (_safe(x) for x in gone) if g]


def _full(new, say):
    """Every file of the newest commit, from GitHub's archive of it."""
    say("  downloading the whole version (about 330 MB)...")
    tmpd = tempfile.mkdtemp(prefix="swissng-update-")
    try:
        arc = os.path.join(tmpd, "src.tar.gz")
        req = urllib.request.Request(CODELOAD + new, headers=_headers("*/*", CODELOAD))
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(arc, "wb") as f:
                n, last = 0, 0
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
                    n += len(chunk)
                    if n - last >= 25 << 20:
                        say(f"  {n / 2 ** 20:.0f} MB")
                        last = n
        except OSError as e:
            raise UpdateError(f"the download stopped ({e}): start the update again")
        say(f"  {n / 2 ** 20:.0f} MB downloaded, unpacking")
        files = {}
        with tarfile.open(arc, "r:gz") as t:
            for m in t:
                if not m.isfile():
                    continue
                parts = m.name.split("/", 1)          # switzerlandNG-<sha>/...
                if len(parts) < 2:
                    continue
                rel = _safe(parts[1])
                if rel is None:
                    continue
                files[rel] = (t.extractfile(m).read(), m.mode)
        if len(files) < 100 or "beamng/builder/app/server.py" not in files:
            raise UpdateError("the downloaded archive is not a switzerlandNG version")
        return files
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)


def apply(full=False, say=print):
    """Bring the install to the newest commit. Returns {updated, commit, changed, removed}."""
    if git_checkout():
        say("This folder is a git checkout: updating with git pull.")
        r = subprocess.run(["git", "-C", REPO, "pull", "--ff-only"], capture_output=True, text=True)
        say(r.stdout + r.stderr)
        if r.returncode:
            raise UpdateError("git pull failed (see above)")
        return {"updated": "Already up to date" not in r.stdout, "commit": None, "changed": None, "removed": 0}
    have = installed().get("commit")
    new = latest()
    say(f"newest version: {new['commit'][:10]} of {new['date']} ({new['message']})")
    if have == new["commit"] and not full:
        say("switzerlandNG is up to date.")
        return {"updated": False, "commit": have, "changed": 0, "removed": 0}
    say(f"installed: {have[:10] if have else 'not known (unpacked by hand)'}")
    old = _old_files()
    d = _delta(have, new["commit"], say) if have and old is not None and not full else None
    if d is not None:
        got, gone = d
        for rel, data in got.items():
            _write(rel, _crlf(rel, data))
        for rel in gone:
            if rel not in got:
                _remove(rel)
        files = (set(old) - set(gone)) | set(got)
        removed = len(gone)
        changed = len(got)
    else:
        allf = _full(new["commit"], say)
        for rel, (data, mode) in allf.items():
            _write(rel, data)
            if mode & 0o111 and os.name != "nt":
                os.chmod(os.path.join(REPO, *rel.split("/")), 0o755)
        removed = 0
        for rel in (old or []):
            if rel not in allf and _safe(rel):
                _remove(rel)
                removed += 1
        files = set(allf)
        changed = len(allf)
    _save_state(new["commit"], new["date"], files)
    say(f"switzerlandNG updated to {new['commit'][:10]}: {changed} files written, {removed} removed.")
    return {"updated": True, "commit": new["commit"], "changed": changed, "removed": removed}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if "--check" in argv:
            c = check()
            if c["error"]:
                print("  " + c["error"])
                return 1
            print(f"  installed {(c['installed'] or 'not known')[:10]}, newest {c['latest'][:10]} ({c['latest_date']}): "
                  + ("an update is out." if c["available"] else "up to date."))
            return 0
        r = apply(full="--full" in argv, say=lambda s: print("  " + s, flush=True))
        if r["updated"] and os.environ.get("SWISSNG_UPDATE_ONLY"):
            print("\n  Start switzerlandNG again with its launcher (the first start after an update of the Python "
                  "libraries sets them up again).", flush=True)
        return 0
    except UpdateError as e:
        print(f"\n  The update did not work: {e}\n  Nothing is half written: start it again.", flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
