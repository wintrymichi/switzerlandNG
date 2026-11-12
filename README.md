<div align="center">

# Switzerland Builder · BeamNG.drive

**Pick any part of Switzerland on the real map, press Build, and drive it in BeamNG.drive: a 1:1 level made from open data with the pipeline of the Malcantone map.**

![BeamNG.drive 0.40](https://img.shields.io/badge/BeamNG.drive-0.40-orange)
![Builder](https://img.shields.io/badge/builder-1.0.0-blue)
![Runs on](https://img.shields.io/badge/runs%20on-Windows%20%C2%B7%20Linux%20%C2%B7%20macOS-informational)
![Data](https://img.shields.io/badge/data-swisstopo%20%C2%B7%20cadastral%20surveys%20%C2%B7%20OSM-lightgrey)
[![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](LICENSE)

**[Download the Switzerland Builder](https://github.com/wintrymichi/switzerlandNG/archive/refs/heads/main.zip)** · [The Malcantone map (main branch)](https://github.com/wintrymichi/magliasinaNG/tree/main) · [wintrymichi.ch](https://wintrymichi.ch)

</div>

The Switzerland Builder (the app is called **switzerlandNG**, by wintrymichi) is a small app that runs on your own computer and opens in your browser. You draw a rectangle anywhere on the swisstopo map of Switzerland, give it a name and press **Build**. The app downloads the open data of that area, builds a drivable level with the same Python pipeline that makes the [Malcantone map](https://github.com/wintrymichi/magliasinaNG/tree/main) and the Ticino zones, and puts the finished mod in BeamNG.drive's mods folder.

There is nothing to install or set up first: no Python, no GIS software, no accounts, no API keys. On its first start the app makes its own Python next to itself. Nothing in a level is modelled by hand and nothing comes from a commercial map: terrain, roads, buildings, woods, water, railways and tunnels are all made from the open data of the Swiss Confederation, the cantons and OpenStreetMap.

This repository is the builder (it came out of the `switzerland-builder` branch of magliasinaNG). The Malcantone mod itself, its releases and its own README are in [magliasinaNG](https://github.com/wintrymichi/magliasinaNG).

**Contents:** [Quick start](#quick-start) · [Using the app](#using-the-app) · [What you need](#what-you-need) · [What a level contains](#what-a-level-contains) · [Detail compared with the Malcantone](#detail-compared-with-the-malcantone) · [Cantons and their data](#cantons-and-their-data) · [Build times and sizes](#build-times-and-sizes) · [Command line](#command-line) · [Files and folders](#files-and-folders) · [Troubleshooting](#troubleshooting) · [Known limitations](#known-limitations) · [For developers](#for-developers) · [Sources and licences](#sources-and-licences) · [Licence](#licence)

## Quick start

1. **Install** it with one line, which always takes the newest version (about 330 MB, in `switzerlandNG` in your home folder; it puts a `switzerlandNG` shortcut on the Windows desktop and starts the app):

   | System | Paste into |
   |---|---|
   | Windows 10 / 11 | *Run* (Win+R) or a command prompt: `powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/wintrymichi/switzerlandNG/main/beamng/builder/launch/install.ps1 \| iex"` |
   | macOS, Linux | a terminal: `curl -fsSL https://raw.githubusercontent.com/wintrymichi/switzerlandNG/main/beamng/builder/launch/install.sh \| bash` |

   Or **download** [switzerlandNG-main.zip](https://github.com/wintrymichi/switzerlandNG/archive/refs/heads/main.zip) and unpack it anywhere, for example on the disk with the most free space. It is about 330 MB because the repository carries the whole history of magliasinaNG (the photos and checks of the Malcantone map); the app uses about 55 MB of it.
2. **Start it** with a double click:

   | System | Double-click |
   |---|---|
   | Windows 10 / 11 | `Start Switzerland Builder.bat` |
   | macOS (Intel or Apple silicon) | `Start Switzerland Builder.command` |
   | Linux | `start-switzerland-builder.sh` (or run `./start-switzerland-builder.sh` in a terminal) |

3. **The first start takes 5 to 10 minutes, once.** The launcher downloads [micromamba](https://mamba.readthedocs.io/) and sets up Python with the map libraries (GDAL, rasterio, shapely, osmium...) in its own folder, about 2 GB. Later starts take a few seconds.
4. **The app opens in your browser** at `http://127.0.0.1:8765`. Only your own computer can reach it. Keep the black window open while you use the app: closing it stops the app (a running build stops too and resumes later from the step it was in).
5. **Pick an area, name it and press *Build this area*.** When the build is done the level is in BeamNG.drive's mods folder: start the game and pick it in *Freeroam*.

## Updates

switzerlandNG is always updated to the newest version of this branch, and only the files that changed are downloaded (usually a few hundred KB). Your builds, downloads and settings stay.

- **In the app:** when a new version is out, a red box at the top says so; press *Update and restart* (not while a build runs). The app checks GitHub when it starts and every 6 hours.
- **With the update script:** `Update switzerlandNG.bat` (Windows), `Update switzerlandNG.command` (macOS) or `./update-switzerlandng.sh` (Linux). It updates the app and starts it. `--check` only says whether a new version is out, `--full` downloads the whole version again (to repair a broken install).
- **Running the installer again** on the same folder updates it too.

A folder unpacked from the zip by hand does not know its version yet: its first update downloads the whole version once (about 330 MB), the later ones only the changes. When the new version needs other Python libraries, the next start sets them up again (some minutes). A build that is already running or stopped keeps the pipeline code it started with; `cli resume <build id> --update-code` gives it the new one. A git checkout is updated with `git pull`.

## Using the app

The page has the map of Switzerland on the left and the steps on the right.

**1. Pick an area.** The map is swisstopo's national map, with the aerial photos (SWISSIMAGE) and the grey map as other layers, the canton borders and your earlier builds on top. Search a place ("Andermatt", "Axenstrasse", "Gruyères"), then press *Draw a rectangle* and drag on the map, or press *8 × 8 km* / *4 × 4 km* for a square in the middle of the view. Move the rectangle or its corners until it holds what you want to drive. The dashed square around it is the terrain block the level gets (12.3 km a side, the area in its middle).

As soon as an area is drawn the app checks it and shows:

- its size (from 0.5 to 8.4 km a side) and the cantons it touches;
- the OpenStreetMap extracts it needs (Switzerland, and a neighbour country's when the area reaches the border);
- an estimate of the build time (a range: from mountains and lakes to a dense town of the same size) and of the disk space;
- a warning when part of the area lies outside Switzerland (at least half must be inside) or in a canton whose cadastral survey is not open (see [Cantons and their data](#cantons-and-their-data)), and what that means for the level.

**2. Build it.** Give the level a name (it is the name you will see in the game) and press *Build this area*. The build runs step by step in the background, one build at a time (more go in a queue). Each build shows its current step, how many steps are left and the remaining time, which the app corrects as it sees how fast your computer is. *Log* shows what the pipeline is doing. *Stop* stops a build; *Resume* goes on from the step it stopped in, also after a restart of the PC or of the app. When the build is done, *Install in BeamNG* copies the zip into the game's mods folder (the app does it by itself when the setting is on), *Show zip* opens its folder and *Delete* removes the build (the downloads stay in the shared cache for the next area).

**Settings:**

| Setting | What it does |
|---|---|
| Data folder | Where downloads and builds go. By default `SwissBuilder` in your home folder; on Windows on the drive with the most free space. A build takes 15 to 50 GB. |
| BeamNG.drive user folder | The folder with `mods` in it. Found by itself on Windows, Linux and Linux with Proton (Steam); set it here if it was not found. |
| Worker processes | *Automatic* runs 2-4 processes in the heavy steps, by the memory of the PC; *Few* for 16 GB or less; *Many* only with 48 GB or more. |
| Put finished levels in BeamNG's mods folder | On by default. Off: the zip stays in the build's folder. |

## What you need

- A 64-bit PC with Windows 10 or 11, Linux, or macOS (Intel or Apple silicon).
- 16 GB of memory; 32 GB is comfortable. The test areas below needed at most 5 GB, a dense town of 64 km² about 13 GB at its peak. With less than 20 GB the app runs fewer processes at once.
- 15 to 50 GB of free disk per build, plus the shared download cache (the terrain tiles and extracts one area downloaded are reused by the next one nearby). The app warns before a build when it sees less room than its estimate.
- An internet connection: an area downloads a few GB (swisstopo tiles, the cadastral survey, swissTLM3D, OpenStreetMap, the Register of Buildings).
- BeamNG.drive 0.40 to play the levels. They use the game's own Italy textures for asphalt, stone, plaster and the like, as the Malcantone map does.

## What a level contains

Everything below is made for any area by the pipeline of the Malcantone map, from open data:

- **Terrain:** a 12.3 × 12.3 km block (8,192 × 8,192 samples, 1.5 m apart) from swissALTI3D, the area in its middle, and the mountains to the horizon around it (swissALTI3D 2 m and Copernicus GLO-30 out to 25 km). The ground layers come from the land cover (meadow, wood, rock, scree, gravel, water, paved ground) with colours measured on the aerial photos; grass grows on the meadows, the woods have an undergrowth and a forest floor of their own, steep cuts and banks get a skin of rock and earth.
- **Roads and paths:** every swissTLM3D road and path, from motorways to 1 m trails, at the widths the cadastral survey measures, with banks, kerbs, pavements, yards and squares, traffic islands and roundabouts, bridges with their deck and parapets, road paint by the Swiss rules (centre and edge lines, give way and stop lines, crossings, motorway lanes), wear and patches on the asphalt, road signs and direction signs, street lamps that light the road at night, delineator posts, traffic lights where OpenStreetMap maps them, car parks with painted spots.
- **Guard rails:** on the motorways, wherever the ground falls away beside a road (2 m or more, steeper than 1:2, within 6 m of the edge; 3 m beside the narrowest roads; not in villages, nor where a yard, a wall or a building is beside the road), and wherever OpenStreetMap maps one. No post stands in the air: the ground is filled in under the rails, and where it falls too steeply the rail stands on an edge beam on a retaining wall down to the ground (of concrete, or of stone beside a stone wall of the survey).
- **Tunnels and galleries:** every swissTLM3D road and railway tunnel that joins the level's roads or tracks, with its portals and name, lining, kerbed walkways, lights, lit escape signs, SOS niches, emergency exits and jet fans in the long tubes, and the AI roads through it. The avalanche and rock-fall galleries of the mountain roads are open to the valley, with their pillars, roof slab and parapet.
- **Buildings:** every swissBUILDINGS3D building with its real roof (tiles, slate, metal, ridge caps), façades with windows, doors and shutters by the period of construction (Register of Buildings), gutters, aerials, solar panels, balconies with flower boxes, shop fronts, canopies on posts, and the buildings the 3D model lacks taken from the survey.
- **Trees and woods:** single trees measured on the surface model (swissSURFACE3D), with their height and kind (broadleaf or conifer), woods to the horizon, vineyards.
- **Water:** the lake with its shore, piers and lake bed, rivers and streams with their water and banks, their sounds.
- **Railways:** tracks on ballast with sleepers and rails, the overhead line with masts on the electrified lines.
- **Street life:** benches, bins, letter boxes, planters, hydrants, garden furniture, café tables where OpenStreetMap maps cafés and shops, bus shelters.
- **Driving:** AI roads with lanes, speed limits and give-way rules (traffic works out of the box), spawn points on the main roads and in every village, named after the nearest village.

## Detail compared with the Malcantone

A level of the Switzerland Builder goes through the **same pipeline, the same stages and the same 49 finishing steps** as the Malcantone map and the Ticino zones, from the same kinds of data. Where the canton's cadastral survey is open (19 of the 26 cantons), the detail is the Malcantone's.

Some things are better than in the released Malcantone map: tunnels and avalanche galleries (the Malcantone v3.1.1 has none), motorways with their lanes and guard rails, traffic lights from OpenStreetMap, and the land cover outside the survey from swissTLM3D.

What the Malcantone has on top was measured by hand or from street photos along its own roads, and does not exist for other areas:

| Only in the Malcantone | In a Switzerland Builder level |
|---|---|
| Guard rails placed from street photos (10.7 km) | Guard rails by rule where the ground falls away, and from OpenStreetMap |
| Signs, lamps, wall tops and road paint of the Magliaso-Pura road measured on the panoramas | Signs, lamps and paint by the Swiss rules and OpenStreetMap |
| Roadside walls of the cantonal road, hedges, fountains and roof heights checked on photos | Survey walls and swissBUILDINGS3D roofs as they are |
| Bus stop paint traced on 10 cm aerial photos | No bus stop paint |
| The church towers, the Monte Lema cable car and its summit modelled one by one | swissBUILDINGS3D's own model of every building |
| Time trials along named roads | No time trials yet |

Where the survey is **not** open (Jura, Lucerne, Neuchâtel, Nidwalden, Obwalden, Vaud, Valais), there is less: see the next section.

## Cantons and their data

The cadastral survey (geodienste.ch) gives the pipeline the outline of every road, yard, pavement, traffic island, wall, river and lake. The app probed every canton on 7 November 2026 (`beamng/builder/tools/probe_sources.py`):

| | Cantons |
|---|---|
| **Open survey: full detail** | Aargau, Appenzell Ausserrhoden, Appenzell Innerrhoden, Basel-Landschaft, Basel-Stadt, Bern, Fribourg, Geneva, Glarus, Graubünden, St. Gallen, Schaffhausen, Schwyz, Solothurn, Thurgau, Ticino, Uri, Zug, Zurich |
| **Survey not open: less detail** | Jura, Lucerne, Neuchâtel, Nidwalden, Obwalden, Vaud, Valais |

In a canton without an open survey the app warns before the build, and the level is made from what is open there: the land cover (woods, lakes, rivers, rock, meadows) from swissTLM3D and ESA WorldCover, the roads from swissTLM3D's lines at the width of their class. There are no yards, pavements, traffic islands or survey walls, and no buildings the 3D model lacks. Everything else (terrain, buildings, trees, tunnels, railways, signs, lamps, AI roads) is the same.

Outside Switzerland (an area at the border) the level has terrain (Copernicus, 30 m), land cover and simple woods; the roads and buildings stop at the border.

## Build times and sizes

Measured on GitHub's runners (4 cores, 16 GB of memory), every step from the first download to the zip:

| Area | Size | Time | Level zip |
|---|---|---|---|
| Axenstrasse and Sisikon (Uri, Schwyz): mountains, the Urnersee, 44 road and rail tunnels and galleries | 32.8 km² | 41–45 min (61 min before the faster builds of 2026-11-09) | 0.86 GB (3.8 GB unpacked) |
| Vitznau and Gersau (Lucerne without open survey, Schwyz): Lake Lucerne, the Rigi's slopes | 17 km² | 39 min | 0.56 GB (2.2 GB unpacked) |
| Montreux and Chillon (Vaud, no open survey): a lakeside town, Lake Geneva, the A9's tunnels | 8.7 km² | 31 min | 0.36 GB (1.1 GB unpacked) |
| Sisikon, small test area, on Windows | 0.9 km² | 14 min (18 min before) | 0.28 GB |
| Lugano (Ticino zone ti_1_0), dense town | 64 km² | about 5 h | 1.9 GB |

A dense town takes far longer than mountains and lake of the same size: the build time grows with the buildings and roads, not with the area. So the app gives the build time as a range, from mountains to a dense town, and the remaining time shown during a build follows the real speed of the steps. On a slow internet connection add the downloads: a few GB per area.

## Command line

The same builds without the web page, for scripts or a server:

```
start-switzerland-builder.sh cli check  S,W,N,E
start-switzerland-builder.sh cli build  "Name" S,W,N,E [--data DIR] [--until STEP]
start-switzerland-builder.sh cli resume <build id>     [--data DIR] [--until STEP] [--update-code]
```

On Windows the same words follow `"Start Switzerland Builder.bat"`. `S,W,N,E` is the box in degrees (WGS84), for example `46.915,8.588,46.983,8.643` for the Axenstrasse. `check` prints what the app would show for the box. `--until` stops after a step (`stages`, `finish:tunnels`, `package`...), `resume` goes on from where a build stopped, and `--update-code` gives a build the pipeline code of a newer download of the app before it goes on (its downloads stay). `start-switzerland-builder.sh --no-browser` starts the app without opening the browser; `SWISSBUILDER_PORT` chooses another port.

## Files and folders

```
<data folder>/
  cache/                 downloads shared by the builds (terrain tiles, swissBUILDINGS3D, OSM and register extracts)
  builds/<id>/
    build.json           the steps and their state
    build.log            everything the pipeline printed
    zone.json            the area, as the pipeline reads it
    code/                the pipeline as it was when the build started
    root/data/           the downloads of this area
    root/work/           intermediate files, reports (work/reports)
    root/beamng_user/levels/ch_<name>/   the level
    root/dist/ch_<name>.zip              the mod
```

The app's own Python and settings are in `beamng/builder/.runtime` (when the folder's path has spaces or accents: `%SystemDrive%\SwissBuilder\runtime` on Windows, `~/.swissbuilder/runtime` on Linux and macOS). Deleting that folder makes the next start set Python up again. The OpenStreetMap extracts in the cache are fetched again after 14 days and the Register of Buildings after 7.

Every level is called `ch_<name>` in the game's files, so levels of different areas never clash with each other or with the Malcantone (`magliaso_pura`).

## Troubleshooting

- **Windows says "Windows protected your PC"** at the first double click: the file comes from the internet and is not signed. Click *More info* → *Run anyway*.
- **macOS says the file cannot be opened** because it is from an unidentified developer: right-click `Start Switzerland Builder.command` → *Open* → *Open*, once.
- **The first start stopped** (no internet, a download cut off): start it again; it goes on where it stopped.
- **The browser did not open:** open `http://127.0.0.1:8765` yourself. If that port is taken, the app takes the next free one and prints it in its window.
- **A build failed:** press *Log* to see the error, then *Resume*: it goes on from the failed step, the downloads and finished steps stay. A download that failed for a moment (a server busy) usually goes through the second time.
- **The disk filled up:** free some room or move the data folder in Settings to a bigger disk (move the folder's contents too), then *Resume*.
- **The level is not in the game:** check that the zip is in `<BeamNG user folder>/mods` and that the mod is enabled in the game's mod manager (after an update of the game BeamNG.drive disables every mod). In the app, *Install in BeamNG* tells you where it copied the zip or why it could not.
- **The game loads the level slowly the first time:** it converts every shape and texture once and keeps them in its cache; the next loads are faster.

## Known limitations

- **One area per level**, at most 8.4 km a side and at least half of it in Switzerland. A larger region needs several levels (or the streaming of the Ticino branch).
- **One lake per level:** the largest lake of the area gets its water; a second lake at another level (a reservoir above a valley lake, a mountain lake) stays a dry hollow. Rivers and streams get their water everywhere.
- **Cantons without an open survey** (Jura, Lucerne, Neuchâtel, Nidwalden, Obwalden, Vaud, Valais) have no yards, pavements, traffic islands or survey walls; their road widths come from the road class.
- **Roads under rock overhangs** (the Axenstrasse has many) run in a notch cut into the rock face: the terrain is a height map and cannot hang over a road.
- **Old roads that are footpaths today** (old stretches of the Axenstrasse) get tunnels and galleries as narrow as the path swissTLM3D gives them, narrower than the real ones, and bits of the old road's asphalt stand on the rock beside some of their portals.
- **A road over a gorge that swissTLM3D does not draw as a bridge** keeps its guard rail on an edge beam without a wall under it where the fall is deeper than 8 m (7 short stretches on the Axenstrasse, listed in the build's report `rail_walls.json`).
- **The data measured from photos** for the Malcantone is not there for other areas (see [Detail compared with the Malcantone](#detail-compared-with-the-malcantone)); there are no time trials yet.
- **Tested on GitHub's Linux and Windows runners**, from the launcher to the zip. macOS is not tested yet, and the levels of the builder have not been driven in the game yet (the Malcantone and the Ticino zones made by the same pipeline have).
- **The build time** is given as a range before a build, because it depends on how many buildings and roads the area has, which is only known once the data is downloaded.

## For developers

```
Start Switzerland Builder.bat / .command, start-switzerland-builder.sh   launchers (repository root)
Update switzerlandNG.bat / .command, update-switzerlandng.sh              update scripts (repository root)
beamng/builder/
  launch/start.ps1, start.sh   micromamba, the Python environment (environment.yml), then the app ("update": the updater)
  launch/install.ps1, install.sh  one-line installers of the newest commit of the branch
  app/update.py                updates: newest commit of the branch, changed files only (.switzerlandng.json keeps the commit)
  app/server.py                the local web server (127.0.0.1 only, a token per page)
  app/jobs.py                  builds, their steps and their state; one process per step, resumable
  app/zone.py                  the checks of an area, the zone file the pipeline reads (MAGLIASO_ZONE)
  app/recenter.py              moves a finished level to its own origin (float precision in the game)
  app/cache.py                 the download cache shared by the builds
  app/cli.py                   the command line
  web/                         the page (Leaflet 1.9, swisstopo WMTS tiles)
  tools/probe_sources.py       which canton's open sources answer (app/data/sources_probe.json)
  tests/test_builder.py        checks that need no download
beamng/pipeline/               the magliasinaNG pipeline (shared with the Malcantone and Ticino)
```

A build is the pipeline's own build of a Ticino zone (`zone_build.yml` of the ticino branch) with a zone file of the picked area: the downloads (`download_*.py`), the rasters, land cover, buildings, trees and road network, `build_level.py` stages and finishing steps, then the app's recentring and packaging. Everything that only exists for the Malcantone (street photos, hand-made lists) is left out of any other area by its box.

Tests: `python tests/test_builder.py` from `beamng/builder` with the app's Python. `.github/workflows/builder_test.yml` builds the test areas of `beamng/builder/test/` on GitHub through the launcher, as a user's PC runs it, when `beamng/builder/test/stamp.txt` changes on this branch; the zips and logs go to a draft release. `builder_probe.yml` runs the probe of the cantons' sources. `builder_update_test.yml` (on `beamng/builder/test/update_stamp.txt`) installs, updates from an older commit and installs again on Windows and Linux, and checks that the updated folder equals a fresh install.

## Sources and licences

The app downloads the data of each area itself, from:

- © swisstopo: swissALTI3D, swissSURFACE3D, SWISSIMAGE, swissBUILDINGS3D 3.0, swissTLM3D, swissNAMES3D (open geodata of the Swiss Confederation, free use with the source named).
- The cadastral surveys of the cantons (official survey, geodienste.ch), where they are open.
- Federal Register of Buildings and Dwellings (Federal Statistical Office).
- © OpenStreetMap contributors, ODbL 1.0 (Geofabrik extracts).
- Copernicus DEM GLO-30 (© DLR e.V. / Airbus, provided under COPERNICUS by the European Union and ESA).
- ESA WorldCover 2021 (© ESA WorldCover project, CC BY 4.0).
- The map of the app: swisstopo's national map and SWISSIMAGE (WMTS), with Leaflet (BSD-2-Clause).

Every level names its sources in its own description in the game.

## Licence

The Switzerland Builder, the pipeline and this repository are **free for non-commercial use** under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). You can use them, share them and modify them, provided you give appropriate credit, indicate any changes, and comply with the licence terms.

**Commercial use of my original work is not permitted without my prior written permission and a separate commercial licence, subject to a fee agreed in writing.** This includes selling levels made with the builder, paid downloads, paywalls, paid bundles, subscriptions, and commercial services incorporating my work. To request a commercial licence, contact [**info@wintrymichi.ch**](mailto:info@wintrymichi.ch).

The data in the levels remains subject to the licences of its sources above; OpenStreetMap data remains under the ODbL. The full terms are in [`LICENSE`](LICENSE).

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/wintrymichii)
