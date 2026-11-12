#!/usr/bin/env bash
# switzerlandNG installer for Linux and macOS: always installs the NEWEST version of wintrymichi/switzerlandNG (main).
#
#   curl -fsSL https://raw.githubusercontent.com/wintrymichi/switzerlandNG/main/beamng/builder/launch/install.sh | bash
#   bash install.sh [folder] [--no-start]          default folder: ~/switzerlandNG
#
# It asks GitHub for the newest commit, downloads that commit's archive (about 330 MB) and unpacks it into the folder,
# then starts the app (the first start sets up its Python, 5-10 minutes). A folder that already holds switzerlandNG
# is updated instead (only the changed files, update-switzerlandng.sh). Builds and settings are never touched.
set -euo pipefail
REPO="wintrymichi/switzerlandNG"
REF="${SWISSNG_REF:-main}"
DEST="$HOME/switzerlandNG"
START=1
for a in "$@"; do
  case "$a" in
    --no-start) START=0 ;;
    *) DEST="$a" ;;
  esac
done
say() { printf '\n  %s\n' "$*"; }
fail() { printf '\n  ERROR: %s\n\n' "$*" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || fail "curl is not installed: install it and start again."
command -v tar >/dev/null 2>&1 || fail "tar is not installed: install it and start again."

if [ -f "$DEST/.switzerlandng.json" ] && [ -x "$DEST/update-switzerlandng.sh" ]; then
  say "switzerlandNG is already in $DEST: updating it to the newest version."
  [ "$START" = 1 ] || export SWISSNG_UPDATE_ONLY=1
  exec "$DEST/update-switzerlandng.sh"
fi

say "Looking for the newest version of switzerlandNG..."
SHA="$(curl -fsSL --retry 4 --connect-timeout 20 -H "Accept: application/vnd.github.sha" \
  "https://api.github.com/repos/$REPO/commits/$REF")" || fail "GitHub could not be reached: check the internet connection."
case "$SHA" in *[!0-9a-f]*|"") fail "GitHub gave no version ($SHA)." ;; esac
say "Newest version: ${SHA:0:10}. Downloading it (about 330 MB) into $DEST ..."
mkdir -p "$DEST"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fSL --progress-bar --retry 4 --retry-delay 3 --connect-timeout 20 --speed-limit 1024 --speed-time 60 \
  -o "$TMP/src.tar.gz" "https://codeload.github.com/$REPO/tar.gz/$SHA" || fail "the download stopped: start the installer again."
say "Unpacking..."
tar -xzf "$TMP/src.tar.gz" -C "$DEST" --strip-components=1
tar -tzf "$TMP/src.tar.gz" | grep -v '/$' | cut -d/ -f2- | grep -v '^$' | LC_ALL=C sort > "$DEST/.switzerlandng-files.txt"
[ -f "$DEST/beamng/builder/app/server.py" ] || fail "the download is not a switzerlandNG version."
printf '{"commit": "%s", "ref": "%s", "date": null, "updated": "%s"}\n' "$SHA" "$REF" \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$DEST/.switzerlandng.json"
say "switzerlandNG ${SHA:0:10} is installed in $DEST."
say "Start it with $DEST/start-switzerland-builder.sh (macOS: 'Start Switzerland Builder.command'), update it with update-switzerlandng.sh."
if [ "$START" = 1 ]; then
  exec "$DEST/start-switzerland-builder.sh"
fi
