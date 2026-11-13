"""Download Ticino cadastral survey (Misurazione ufficiale, MOpublic) layers for the map
from the geodienste.ch WFS (open data, attribution required):
  LCSF  copertura del suolo (road, sidewalk, island, building, garden, forest, water ...)
  SOSF / SOLI / SOPT  oggetti singoli as surfaces / lines / points (walls, stairs, bridges ...)
over the playable area (area.py) + MARGIN, in TILE m requests paged by COUNT features.
Saved as GeoJSON (LV95) in data/av/.

geodienste.ch's terms (geodienste.ch/terms-of-use) forbid bots with high request rates and say access can be refused
for excessive use: an IP that sends many GetFeature requests in a row gets HTTP 403 for a while (michi 2026-11-13, a
user's log: 403 on an open canton, Aargau, that answered normally from another IP). So the requests go one at a time
with PAUSE s between them, and a 403 is not retried: the level is built without the survey (as in a canton with no
open survey: land cover from swissTLM3D + ESA WorldCover) and BLOCKED is written, so the next build tries again.
"""
import json, os, time
import numpy as np
import netio
import shapely
from config import DATA
import area

WFS = "https://geodienste.ch/db/av_0/ita"
LAYERS = ["LCSF", "SOSF", "SOLI", "SOPT"]
TILE = 1024.0
MARGIN = 100.0
COUNT = 5000
PAUSE = 1.0           # s between two requests (fair use)
BLOCKED = "BLOCKED.txt"


def fetch(layer, bbox, start=0):
    params = dict(SERVICE="WFS", VERSION="2.0.0", REQUEST="GetFeature", TYPENAMES=f"ms:{layer}",
                  OUTPUTFORMAT="application/json; subtype=geojson", SRSNAME="EPSG:2056",
                  BBOX=",".join(f"{v:.1f}" for v in bbox) + ",urn:ogc:def:crs:EPSG::2056",
                  COUNT=str(COUNT), STARTINDEX=str(start))
    time.sleep(PAUSE)
    r = netio.get(WFS, params=params, timeout=300, what=f"survey {layer} page {start // COUNT + 1}")
    return r.json()["features"], len(r.content)


def main():
    out_dir = os.path.join(DATA, "av")
    os.makedirs(out_dir, exist_ok=True)
    blocked = os.path.join(out_dir, BLOCKED)
    if os.path.exists(blocked):         # the last build was refused: the empty layers it left are no survey, try again
        for l in LAYERS:
            if os.path.exists(os.path.join(out_dir, f"{l}.geojson")):
                os.remove(os.path.join(out_dir, f"{l}.geojson"))
        os.remove(blocked)
    try:
        download(out_dir)
    except netio.DownloadError as e:
        if e.status != 403:
            raise
        print("\nWARNING: geodienste.ch refused the cadastral survey (HTTP 403). It does that for a while to an address "
              "that sent it many requests (fair use, geodienste.ch/terms-of-use), or to some VPN and server networks. "
              "The level is built WITHOUT the survey (land cover from swissTLM3D and ESA WorldCover, fewer road "
              "details), as in a canton with no open survey. The next build tries again; wait a few hours, or turn a "
              "VPN off.\n", flush=True)
        for l in LAYERS:
            dest = os.path.join(out_dir, f"{l}.geojson")
            if not os.path.exists(dest):
                json.dump({"type": "FeatureCollection", "features": []}, open(dest, "w"))
        with open(blocked, "w") as f:
            f.write("geodienste.ch HTTP 403 %s: %s\n" % (time.strftime("%Y-%m-%d %H:%M"), str(e)[:300]))


def download(out_dir):
    g = area.lv95_polygon(MARGIN)
    shapely.prepare(g)
    e0, n0, e1, n1 = g.bounds
    boxes = [(e, n, min(e + TILE, e1), min(n + TILE, n1)) for e in np.arange(e0, e1, TILE) for n in np.arange(n0, n1, TILE)]
    boxes = [b for b in boxes if g.intersects(shapely.box(*b))]
    todo = [l for l in LAYERS if not os.path.exists(os.path.join(out_dir, f"{l}.geojson"))]
    for layer in LAYERS:
        if layer not in todo:
            print(layer, "exists", flush=True)
    # the percentage by requests: every box of every layer once, and the extra pages as they come
    prog = netio.Progress("cadastral survey", files=len(todo) * len(boxes))
    for layer in todo:
        dest = os.path.join(out_dir, f"{layer}.geojson")
        feats, seen = [], set()
        for b in boxes:
            start = 0
            while True:
                page, nbytes = fetch(layer, b, start)
                new = 0
                for f in page:
                    fid = f.get("id") or json.dumps(f["properties"], sort_keys=True) + str(f["geometry"])[:200]
                    if fid not in seen:
                        seen.add(fid)
                        feats.append(f)
                        new += 1
                prog.add(nbytes)
                if len(page) < COUNT:
                    break
                # 2026-11-09: a server that ignores STARTINDEX sends the same full page for ever
                if new == 0 or start > 200 * COUNT:
                    print("survey %s: page %d brought nothing new, the box is taken as complete" % (layer, start // COUNT + 1),
                          flush=True)
                    break
                start += COUNT
                prog.files += 1                 # one more request than counted
            prog.file_done()
        json.dump({"type": "FeatureCollection", "features": feats}, open(dest + ".part", "w"))
        os.replace(dest + ".part", dest)
        print(layer, len(feats), "features", flush=True)
    prog.done()


if __name__ == "__main__":
    main()
