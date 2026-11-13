# Notes for Claude sessions on MagliasinaNG

Mistakes made in earlier sessions and what to do instead. Add to this list when a new one costs time.

## Building the level locally

- Mirror `.github/workflows/v3_build_test.yml` with `MAGLIASO_ROOT` etc. exported. Without the env vars,
  `config.py` falls back to Windows paths (`BEAMNG_USER = C:\Users\...`) and scripts silently find nothing
  (a mesh search returned no items until the build env was sourced).
- A full build takes about 3.5 h; `build_level.py --finish <steps>` reruns single finish steps. After a
  container restart mid-build, resume from the failed step instead of starting over.
- Never run whole-terrain analysis (full 8192x8192 arrays, the 0.5 m DTM) while a build runs: it OOM-killed
  a pool worker and deadlocked the `optimize` step. Use small windows (memmap slices) during a build.
- `pkill -f build_level.py` also matches the shell running the pkill and kills it. Use `pkill -f "[b]uild_level.py"`.
- The build rewrites files in `beamng/dati` (e.g. `ponti.json`). Run `git checkout -- beamng/dati` before
  committing, or generated data ends up in the commit.
- The cloud container idles when no turn is active: keep a foreground wait loop while a build runs
  (`timeout 590 bash -c 'until grep -qE "BUILD DONE|Traceback" LOG; do sleep 20; done'`).
- `optimize_level` used os.cpu_count() - 2 processes (14) and the OOM killer took the build and the Claude session on
  the 14 GB PC (2026-10-17): now OPT_WORKERS (default 4). Keep PATCH_WORKERS=2 and nothing else heavy meanwhile.
- `pgrep -f`/`pkill -f` with a pattern in your own command line stops your own shell: use "[r]un_build" style patterns.
  The bracket trick only helps if the plain name is nowhere else in the same command: `pkill -f "[s]core.py"; python3
  score.py` and `pkill -f "[c]ompare.py /home"; ... compare.py /home/...` killed the shell (exit 144) twice in the
  buildings thread (2026-10-23). Kill by PID (`ps aux | grep "[n]ame"` first, then `kill <pid>` in a separate call).
  `ps aux | grep "[c]ompare.py" | xargs kill` is no better: it lists the shell whose command line holds the name
  further on (a third kill). `pgrep -af "^python3 compare"` anchors on the process's own command.
  Again 2026-10-29 (helper thread): `pkill -f "[t]icino_helper.py"` followed by a heredoc that named
  helper/ticino_helper.py killed the shell before the heredoc ran (its edits were lost silently): one kill per call.
- Push work often. An earlier session lost the fuel stations module because it was never pushed.

- The cloud container cannot upload release assets (uploads.github.com answered 415 through the gateway) and cannot
  dispatch a workflow that is not on the default branch (404): give a new workflow a push trigger on a stamp file of
  the branch (nightly_from_test.yml copies the draft test build to the nightly pre-release on GitHub's side).
- A force-push of a branch restarts every workflow whose push paths the branch touches: two rebases of the roofs
  branch reran roofs_pack.yml (it committed nothing new). Check `actions/runs?branch=` after a force-push.
- The cloud session cannot edit a release either (PATCH .../releases/<id>: 403 "not permitted for this session type",
  2026-10-23): a change to the nightly notes goes into beamng/nightly/v31_notes.md and reaches the release only with the
  next workflow that rewrites the notes.
- `gh release download` fails in the cloud (GraphQL blocked): download release assets through the REST API
  (`gh api .../releases/tags/<tag>`, then the asset URL with `Accept: application/octet-stream`).
- Cloud sessions cannot create, edit or delete releases or their assets (403 "not permitted for this session type",
  2026-10-23, publishing v3.1). Do it from michi's PC through Remote Control: gh is logged in on the Linux PC; on
  Windows DESKTOP-OUPOLOA install gh with winget and let michi enter the device code. A nightly becomes a release
  without re-upload: delete the old assets, rename the zip (PATCH releases/assets/<id>), `gh release edit --tag`.
  Read the asset id from the release itself: an id passed on between threads was wrong (669661675, real 669853164).
  DESKTOP-OUPOLOA has no winget (gh zip from github.com/cli/cli/releases, in %LOCALAPPDATA%\Programs\GitHubCLI), and the
  RC safety filter blocked `gh auth login --web` ("Create Public Surface"): michi must log in himself or say yes in the thread.
  With michi's "sì" in the thread it ran; gh is now logged in on DESKTOP-OUPOLOA (%LOCALAPPDATA%\Programs\GitHubCLI).
  v3.1 was published this way (2026-10-23 23:16Z): the nightly release is gone (only its git tag is left), so the next
  nightly workflow has to create the release again.
- pip can hang with no output in the cloud: run it with `timeout` and `--progress-bar off`, kill and retry.
- `git commit` during an unfinished rebase folds the new commit into the one being picked: run
  `git rebase --continue` (check `git status`) before committing anything else.

## Testing in the game on the PC

- The monitor may be off (OLED, black window on top): run the game in a virtual KWin session, it renders on the RTX:
  `kwin_wayland --virtual --xwayland --width 2560 --height 1440 --socket wl-mng --exit-with-session <script>` with
  `SDL_VIDEODRIVER=x11` (the plain launch hung at startup with the screen off). Measure before/after in the same setup.
- An extension name `magliaso_v31` loads `lua/ge/extensions/magliaso/v31.lua` (the underscore is a folder).
  The v3.0.40 traffic runner still installed `magliaso_traffic.lua` flat and the game never ran it (2026-10-21): check
  every new runner script against this line.
- `gz()` (getSurfaceHeightBelow) hits roofs: give cameras near buildings absolute heights.
- The game's sites (`city.sites.json`, `facilities.sites.json`) need an `oldId` on every spot and zone, or the level
  stops loading with a Lua error.
- Restore the player's mod zip, temp cache and remove every test file from the user folder at the end.
- A screenshot on michi's PC while he uses it took his real desktop (browser, terminal) instead of the game, because
  Windows did not bring BeamNG to the front (2026-10-20; deleted at once). Capture only the game window or the virtual
  display, never the whole screen, and check the picture shows the game before keeping it.
- A game update can move the game's own files the level uses: 0.40 moved 73 of them from `/levels/italy/...` to
  `/assets/materials/...` and left `.link` redirects, which it follows, except for 3 (the stone wall, italy_plastic):
  missing textures everywhere (2026-10-20). Read the game log ("Failed to load", NO-MATERIAL) before guessing, then
  update `dati/game_paths_<version>.json` (finish step `game_paths`) against the installed game.
- After a version update BeamNG disables every mod in `mods/db.json`, and a relaunch from Steam drops the launch
  options (`-level`, `-gfx dx11`): the game opened West Coast USA. Check both before every test.
- Do not use the laptop DESKTOP-EKDTIGL (AMD iGPU, 512 MB video memory) for load tests on 0.40 (michi, 2026-10-20):
  the released v3.0 took 12-15 min to load and crashed twice "Out of VRAM" while the game converted the sign PNGs.
  0.40 clears `temp/levels/<level>` at every start, so a relaunch converts them again (no warm cache).
- On michi's PC the Remote Control permission check refused to move or even copy the installed mod zip out of `mods`
  ("Irreversible Local Destruction"), so the v3.0 comparison run (swap the zips) was dropped (2026-10-21). Plan a test
  that needs another version as a second install or ask michi to swap the zip himself; and the game had auto-updated
  overnight (0.40 -> 0.40.1): read the version in the log before comparing with an earlier test.
- After stop_rc_session the thread's folder tools (device_list_dir, device_stage_files) never came back (2026-10-21,
  only get_device_info and the computer tools were offered, also to a fresh subagent): the test results were stuck on
  the PC. Copy what you need off the PC while you still have a route; the fallback was an RC session packing one zip
  (PowerShell + .NET) on the Desktop for michi to drag into the thread. PowerShell variable names ignore case: `$w`
  and `$W` are one variable (the first packing attempt wrote nowhere).
- A Remote Control session started from a thread reports only to that thread (@parent): forward its notes to the
  other threads yourself. `list_events`/`interrupt_session` do not reach it, and a message waits until its current
  long step ends.

- 88 Ticino zips (ticino-all, ~596,000 files, 49 GB) in mods (2026-10-29, 0.40.4): the first start after installing
  them blocked the main thread while core_modmanager.initDB mounted the new mods; after ~70 s Windows reported it as
  "not responding" and it was closed (launcher log: exit 0xCFFFFFFF STATUS_APPLICATION_HANG; beamng.log cut off in
  the middle of the mountEntry lines, so it reads like a crash). Not a crash: started again, it reached the menu
  (michi). Wait through "not responding" on the first start with many new mods; read beamng-launcher.log for the exit
  code before hunting a crash in beamng.log. Fewer, bigger files per zone would shorten it (5 region zips with 31,896
  files mounted in under 1 s).

- All Ticino (ticino-all base, 2026-10-29, 0.40.4): the level loaded, then the game froze for good in its first frame
  after the vehicle spawn (one core at 100 %, no disk, ~5 min, then Windows closed it: "Application Hang"). Cause:
  city.sites.json with 122,111 parking spots (58 MB); with the spots removed the level ran. region_net.merge_sites
  keeps MAX_PARKING. Found by elimination with empty user-folder overrides (AI roads, SFX emitters, water, vegetation
  all innocent) after the streamer itself was cleared twice: tests/sim_stream.lua with the zones' real files (the
  first jump took 2.3 s of Lua) and a traced copy of the streamer whose onUpdate never ran. beamng.log is buffered
  and cut off at a freeze: write a trace file of your own (rewrite it after every step) instead of trusting its
  last line. A user-folder file of 0 bytes replaces a level's items.level.json for such a test.

- Replays keep the time of day they were recorded at; core_environment.setTimeOfDay during playback works only with the
  replay paused. For sunset or night shots record the replay at that hour (tod 0.245 golden sunset, 0.27 dusk, 0.29
  lamps on with an orange sky, 0.5 full night, 0.85 morning) ("Video cinematico con pianoforte", 2026-10-21).
- PowerShell again: script parameters $B/$T collided with variables $b/$t (names ignore case) and the first scripts sent
  the wrong Lua to the game.
- On DESKTOP-OUPOLOA downloading code from raw.githubusercontent.com is blocked: test files (e.g. mngluci.lua) have to
  reach the PC through the thread's folder tools or the coordinator.
- Wikimedia downloads from that PC: Invoke-WebRequest gets 429; curl.exe with a descriptive User-Agent works.
- ETK 800 cockpit camera placed by hand: offset from the reference node forward -0.3, left 0.4, up 0.92 m (forward 0
  ends outside the windscreen).
- SendUserFile takes files under 20 MB.
- Drone video ("Video drone del Malcantone", 2026-10-22): the virtual display \\.\DISPLAY5 was detached at start (michi
  re-attached it). Mid-session the main monitor went off and DISPLAY5 became the only screen, at 0,0: gdigrab with a fixed
  offset of 2560 failed ("capture area outside window area") and then captured the Claude app instead of the game.
  Compute the offset at runtime and set BeamNG topmost.
- After core_environment.setTimeOfDay, scenetree.sunsky.elevation read in the same chunk is still the old value (it
  updates on the next frame). tod 0.77 is already night-dark; the morning golden hour is at 0.80.
- The PC's permission check (auto mode) blocked an RC session's curl download of a release zip because the order came
  from the thread, not from michi (2026-10-22): ask michi to write the download in his own words in the thread first.
  DESKTOP-OUPOLOA has no gh, so a DRAFT release asset cannot reach it: put test zips on the public pre-release nightly.

- v3.1 in-game test (2026-10-24, 0.40.3, DESKTOP-OUPOLOA): the driver camera in 0.40 is not called `driver`:
  `core_camera.getDriverCameraNameById(vehId)` returns `occupant.FL`; set head yaw/pitch through
  `core_camera.getCameraDataById(id)['occupant.FL'].relativeYaw/relativePitch` about 2 s after teleporting (a teleport
  resets it). Asking for "driver" is why every v3.0.40 cockpit shot came out as a chase view.
- BeamNG vehicles face -Y: pass `quatFromDir(-dir, up)` to `setPositionRotation`, or the car stands backwards.
- An unfocused game window is capped at 30 FPS (`fpsLimitBackgroundEnabled`, `fpsLimitBackground` = 30), and on the
  virtual display it is never focused: turn it off with `settings.setValue` before measuring FPS and restore
  settings.json afterwards, or every FPS number is 30.
- `startFreeroamByName(level, spawn, nil, false)` loads the level with no player car and leaves the main menu on top:
  spawn a car, then `guihooks.trigger('ChangeState', {state='play'})`.
- A raycast down from 2000 m hits tree crowns and roofs: use `core_terrain.getTerrainHeight` for eye-level cameras, and
  expect eye-level cameras near buildings to end up inside walls.
- PowerShell parses `"$var:text"` as a scoped variable: write `"${var}:text"`.
- v3.1 was published before its game test, with README captions written from cloud renders: the test (2026-10-24)
  found the hairpin caption "a straight top" false. Write captions of in-game screenshots only after the test.

- Automatic in-game runs on Windows (v3.1 visual check, DESKTOP-OUPOLOA, 2026-10-24/25): start
  `Bin64\BeamNG.drive.x64.exe` from the game folder. `BeamNG.drive.exe` opens the launcher, and with `-gfx dx12` the
  game said "There is no valid rendering device".
- `[System.Windows.Forms.Screen]::AllScreens` is cached inside a long-running PowerShell process: when the monitor went
  to standby the virtual screen moved to 0,0 and gdigrab failed for 40 minutes with the old offset. Compute the offset
  in a NEW process for every shot, and check the picture file exists after each one.
- A command started in the background by the PowerShell tool is not found by Get-CimInstance on its CommandLine: two
  shot runners ran at once and stole each other's teleports. Stop them with TaskStop and redo those points.
- PowerShell variables ignore case (again): a script parameter `[string]$Plan` was overwritten by `$plan = Import-Csv`.
- A test mod in `mods/unpacked` is added to `mods/db.json` by the game by itself: after removing it, restore the
  db.json saved before the test.
- The external camera behind the car ends inside trees and buildings in about 90 of 650 shots: the static raycast
  does not see the forest's vegetation (forest items are not in the static collision it tests).
- The night of 25.10 the clocks go back (03:00 -> 02:00 CEST -> CET): log timestamps run backwards for an hour.
- michi (2026-10-24): in in-game tests that do not measure FPS, cap the frame rate at 30 fps.

## Nightly v3.1.1 (merging the visual check, 2026-10-25)

- Nine group PRs were opened from main at once (#90-#98): three of them changed steep_skin.py (#95, #96, #97) and the
  merge had two real conflicts (the ROAD_CLAMP block, colours vs colours.ground). Run every merged finishing step on a
  `cp -al` copy of the released level before starting a 4-5 h build: islands, bare_concrete, yard_wear, steep_skin
  and steep_yards took 40 min together and caught nothing, but a crash at hour 4 costs the day.
- The release "nightly" was gone (turned into v3.1) with its tag left: `gh release create` on an existing tag keeps the
  tag's old commit. nightly_build.yml now deletes the tag first.
- steep_yards (#97) gives a road_m shape vertex colours for all its faces as soon as one yard face in it turns
  mp_hard_bank: the road meshes grew 1.15 -> 1.40 GB (+22 %) for the same triangles (the level +0.36 GB, the zip only
  +16 MB). Writing the colours only into the mp_hard_bank part would save it.
- check_level's network_holes (1,623) has no v3.1 value to compare with (the v3.1 checks were never kept): compare the
  road coverage instead (2 m cells of the roads/surfaces up faces): identical to v3.1 but 7 cells. Keep
  `nightly_reports.zip` of every release build in the repo's verifica folder from now on.
- nightly_patch.yml runs any finishing step on the nightly zip (MOD.FN): unzip, run, `find -newer marker | zip -@`,
  upload with --clobber (only a workflow can upload assets; the cloud gets 415).
- road_seams got a second part (sags, 1c09ad3) after its first version was already patched into the nightly zip. Running
  the whole step again would ramp the seams a second time (stacked ramps up to 78 cm): road_sags_step (steps=False) lifts
  the sags alone. Ask whether a step is idempotent before patching a new version of it onto a zip that has the old one.

## Known issues of the map (found in game, no GitHub issue yet: ask michi before opening one)

Found by the AI driving in lane during the piano video (v3.0.40, 2026-10-21), level coordinates:
- a street lamp on the edge of the carriageway at Pura, about (288, -892): hit twice;
- the inner guard rail of the hairpin about (-206, -220) on the Magliaso-Pura road;
- a post on a traffic island in Magliaso village, about (1111, -963);
- on the route spawn_magliaso -> spawn_pura, between nodes 10 and 14, a junction where the AI road drops 4 m from the
  lower road to the upper one: the car ends against a wall.

Found in the v3.1 game test (2026-10-24, report beamng/verifica/v3.1/ingame_test_report.md), causes not yet looked at:
- saw-tooth wall tops still on the Magliaso-Pura Cantonale (the hairpin, the cut near node 58 above Magliaso), after
  the v3.1 saw-top fix: the renders of the fix did not show them;
- missing materials `mp_island_reflector` and `mp_island_beacon` (30 errors each in beamng.log). Looked at 2026-10-25:
  NO file of the released v3.1 zip names them (every entry grepped); the bollards patch removed the beacon and its
  two materials, and the 30 errors = the 30 island tiles with poles. The game used shapes compiled from an EARLIER
  version (its .cdae cache), which is kept while it is newer than the .dae, and the patched .dae carried the date of
  the patch run. Fixed in the pipeline: the two materials stay defined (islands.materials) and package.py dates every
  zip entry at packaging time. Before an in-game test of a new zip, clear the level's compiled shapes in the user
  folder; and grep the zip itself for a material name before chasing a NO-MATERIAL in the code;
- the Via Golf underpass deck renders as a flat grey slab with no texture (fixed in railway.py, 2026-10-25, not built yet);
- grass tufts on the asphalt of the Ponte Tresa bridge at its Italian end (the bridge was widened in v3.1) (fixed in
  terrain.py, 2026-10-25, not built yet);
- large angular wall blocks beside strada_cantonale_1 near (-222, -60);
- AI traffic (#83) still broken: 13 cars queued behind the player's car parked on the Magliaso bridge, then crashed
  into the island at the roundabout exit (783, -1143), 8 of 12 damaged within 2 minutes. The island part is fixed in
  islands.island_lanes (2026-10-25, see Traffic and AI), not tested in game.

## Props and buildings placed wrong (v3.1 visual check, group 8, 2026-10-25)

- street_life kept its props off the carriageway MESH only: 432 props (156 pallets, benches, drums, skips, bags) stood
  inside the AI roads' width where a road crosses a yard, square or junction with no carriageway mesh (the yards are
  `mp_hard_asphalt`, not `mp_road_*`). Site.free now also keeps off the AI road lines (half width + LANE_CLEAR 0.1 m):
  0 left. A clear of 0.5 m threw out half the hydrants, letter boxes and mirrors, which stand on purpose 0.35-0.4 m
  beyond the carriageway edge: measure a new clearance on the roadside props before choosing it.
- props_osm put a bench of OSM on the rock face of a road cut (-3921, 2303; ground 656.4 to 661.9 m within 1 m): no
  slope test. Furniture now skips a footprint (0.8 m round) that rises more than 0.8 m. props_osm runs in the main
  build, so it cannot be rerun on a released level: check it by evaluating `props_osm.steep` on the final ground.
- Not bugs of the data, checked before changing code (keep them out of the next visual check list):
  "canopies on posts without a roof" are canopies whose roof and underside are there (render3d and the DAE): seen
  from a road 1-2 m under their eaves the slab is edge-on and only the posts and roof_details fascias show.
  "Trees on the road edge" (0304, 0321, 1040): no forest item stands within half width + 0.5 m of an AI road
  (1 on the whole map); the shots had trees between the camera and the car. Buildings "on the carriageway" are
  swissBUILDINGS3D houses at the edge of village lanes whose AI road is as wide as the lane (3,802 wall vertices
  inside the AI widths): moving houses is wrong, the AI width would be the thing to narrow. "Sunk" buildings checked
  (0341, 0403) are low sheds and houses built into the slope; telling a raised terrain from a hillside house needs the
  DTM, which the cloud cannot download.
- Render the in-game check points with render3d at the plan.csv pose (driver: eye 1.3 m; ext: 16 m back, 7 m to the
  right, 6 m up) before reading anything from a shot: the ext camera often stands in a tree or a roof.

## Tyre punctures and steps between road pieces (road_seams.py, v3.1.1)

- In BeamNG 0.40 a puncture is a tyre beam breaking (vehicle/beamstate.lua, beamBroken: `beam.wheelID` -> deflateTire):
  a sharp impact on an edge, never a ground model. Look for vertical edges the wheels can hit, not for materials.
- The "hole on the right before Pura" (michi, 2026-10-25: uphill, right side, after the third main curve) was a 22-26 cm
  step along 40 m between two asphalt pieces of road_m3_-01_-01 at about (-176,-122)..(-194,-104), just after the
  hairpin: the uphill lane's outer strip was meshed lower than the rest. The whole map had 6.2 km of such seams
  (1.1 km over 8 cm, max 30 cm), each a vertical skirt with collision. Finish step `road_seams` (after `roundabouts`)
  raises the lower piece into a ramp (12 m per m of step, 0.75-3 m) with its paint/wear/islands/pavements: 1.9 km
  left, 215 m over 8 cm (corners where three pieces meet; a second pass stacked ramps up to 78 cm, not done).
- The hole of michi's screenshot (2026-10-25: "after the two hairpins up from Magliaso, right after the ~90 degree
  curve", 545,-968) was not a seam: a yard and a dirt track join the cantonale from 1-3 m below, and the corridor's
  edge row was pulled down to them, the uphill lane's edge 0.75-0.85 m under the middle over 2 m (a ramp into a pit
  beside the guard rail). road_seams.sags lifts road-surface corners inside the AI road's lane (and the carriageway's
  own edge row, half width + 0.3 m) to the middle's height minus a crossfall, and ramps what joins from outside up to
  them. Corners in the lane are sparse (rows 1 m apart, the edge row just outside half width - 0.3): lifting only the
  lane's own corners changed nothing in the cross-sections. A height test alone also lifted the lower lane beside
  the wall above Magliaso (690,-1046) by 1.18 m: a sag must be joined to the middle without a step (_joined).
  Found by 0.5 m cross-sections of every AI road (drop at the lane edge vs the middle), not by holes in the mesh:
  the asphalt was there, only too low. Render the place from the player's screenshot pose before guessing.
- First version told the two sides of a seam by connected component: the two strips were one welded component
  (joined elsewhere) and both went up 20 cm, step kept. A corner is on the low side only if it lies behind the seam
  edge (outward normal) and more than half the step under the higher face's plane.
- patch_release.read_dae reads the g-pa array of the first geometry but the triangles of all of them: on the terrain
  skin DAEs (three LODs) it made garbage triangles up to 80 cm over the road. A scan reads only up to the first
  `</geometry>` (patch_release left as it is: rewrite_dae writes back what read_dae reads).
- Not changed, also puncture candidates (checked with a 0.1 m scan across the Magliaso-Pura route): low walls 10-30 cm
  standing up to 0.7 m inside the asphalt edge (walls.drive_free skips the cantonale and keeps walls under FREE_OVER
  0.3 m: s 247-307 at (646,-972) is a stone kerb under the guard rail, (-252,85) a slab by a lamp); the 5-6 cm skirt lip
  at every outer road edge; the 12 cm traffic islands. Real kerbs puncture too: left as they are.
- Writing DAE numbers with "%.4f" grew every array by trailing zeros: strip them (road_seams._set_z).

## Terrain fixes

- Terrain heights are written in several places, in this order: the road carve override (`terrain_override`,
  applied as the height under and one terrain step around every paved mesh), the posts (walls.carve_terrain +
  adjust_terrain_roadside, water.lake_bed, rivers, railway.carve_terrain), then `min(H, override)`, then the
  finish steps `unpaved` and `paved_edges` (network_mesh.block raises ground up to EMB_MAX). Fixing one of
  them repeatedly let the same teeth come back from another.
- To find which step made a spike, compare in a small window: the final `.ter` (uint16 at offset 5,
  Z0/MAXH from the terrain json), `work/terrain_heights.npy` (stage terrain), the DTM, and the override
  stored in `work/roads_state.npz` (`ov_i`, `ov_v`). Only then change code.
- The override raises terrain, not only lowers it: a pavement on top of a retaining wall raised the vertices
  one ring beyond the wall carve to pavement height (single white teeth beside the railway under Magliaso,
  about 2500 over the map). walls.carve_terrain now lowers that ring on the low side of a wall.
- Do not tell the side of a wall from a vertex's own height: the DTM smears walls into slopes. Read the
  ground a few metres out on both sides (walls.wall_side), and read beyond any vertex that may itself be raised.
- Anything that raises ground near the railway must respect its bed (railway.bed_fn, network_mesh rail caps).
- The "stretched" cut slopes beside the roads (michi, 2026-10-22, "burroni") were NOT the steep skin: the skin stopped one
  terrain square short of the road (solid = road footprint dilated by 1), and the cut face right beside the road (5-7 m
  in ONE 1.5 m square) stayed bare terrain, its colour projected from above in vertical streaks. In render3d the bare
  terrain and the skin both look like smooth grey sheets: check what a surface is by listing the meshes within a few m
  of the point and by rendering once with the skin items emptied. steep_skin.foot now runs the skin into the road
  (under its surface, ROAD_DIVE), and the faces over ROCK_DEG are rock (v3.1). The skin is round: only 5 % of it is
  steeper than 55 degrees, so a rock threshold taken from the real cuts (60-80) leaves almost no rock.
- Clamping the skin lattice under the road surface was not enough (review of 92bf0fd): the rock relief moves points
  along their normal, sideways onto the road, and clip() cuts new points in along the edges. 3,553 points stood over a
  road (645 by more than 3 cm, worst 0.60 m). Clamp the FINAL points of every material after the clips (tile_mesh),
  only up to ROAD_LIFT_MAX over the road ("near" surface: never pull the skin down to a road in a gallery below), and
  keep the relief small within 2 m of a road (RELIEF_NEAR). The report counts the points before the clamp.
- Pale yellow-green patches with sharp edges on the meadow slopes of the Magliaso-Pura road (michi, 2026-10-25, hairpin
  near (-200,-215) and below Pura near (-240,50)) were the steep skin's EARTH (t_steep_bank_b: light beige with bright moss
  blobs and roots), laid on every bank between STEEP and ROCK_DEG, also on grass slopes, not a terrain layer. Under the
  skin the terrain layer is mostly Bank (the steep vertices), which says nothing about meadow or wood: take the layer of
  the nearest non-Bank, non-paved vertex. First fix: a grass texture of the skin's own in the meadow's colour. michi: "non
  mi piace, non si deve vedere differenza": no mesh looks like the terrain with the game's GroundCover grass. Now the finish
  step skin_grass (steep_skin.py, after steep_yards) removes the skin earth on meadow ground (15 % of the skin, 41 tiles
  whole), turns the Bank vertices under it into the meadow layer beside them (so the grass grows) and drops the skin's
  bushes there; rock (> ROCK_DEG) stays. It is not idempotent (the relayered vertices make more meadow: a second run took
  another 0.4 %): run it once on a zip. michi's in-game colours matched the v3.1 skin (EARTH_MIX 0.45) with the vertex
  colours taken as sRGB multipliers: a screenshot may come from the release, not the nightly; check which first.
- road_obstacles (check_level) cannot run on a released folder in the cloud: it needs network.load() data in WORK. The
  steep_skin report's skin_points_over_road stands in for it for the skin.
- The green and brown "teeth" along the foot of the rock cuts (G1 of the v3.1 visual check, ~45 points, e.g. 0277 at
  2290,5649) were the SKIN, not terrain poking through it: sampled every 25 cm the terrain was under the skin
  everywhere (max 7 cm). Within ROAD_CLAMP (1.5 m) of a road the skin was clamped to split_max of the terrain + EPS
  (against the issue #15 lip), and where a road runs across the terrain grid its carve leaves the foot of a cut as a
  staircase (road level, then 2-3 m up one square further): the higher split of those squares is a row of pyramids
  one square apart, and the skin copied them. First tries that failed: blurring the normals the rock/earth line is
  told by (the teeth stayed, the narrow faces lost their rock), blurring the rock weight alone (teeth stayed: they
  were geometry). Now steep_skin.foot_line draws a line up from the TRUE road edge (a FOOT_FINE raster of the road
  surface; the terrain-vertex footprint steps across the road too) and lower_under lowers the terrain under the
  whole skin until no split of a square stands over it, the road's own vertices outside its surface included. The
  first version of that left the terrain up to 3 m over the skin 25 cm outside the road edge: the line went on down
  under every road, also where the bank falls away from the road (the skin comes up to its edge from below) and
  under the terrain under the road. Check a skin change with the dense terrain-vs-skin sampling outside the road
  surfaces (both splits, 25 cm), not only in renders. Preview harness: run steep_skin_step on a cp -al copy with
  the tile loop limited to the tiles of the view (one tile 3 min, the whole map 13-16 min).
- G1 points NOT from the skin: 0570 (2134,3110) is a ridge of 2-3 terrain vertices 2.4 m over the road at the edge of
  an embankment with no mesh over it, the same in v3.0.40 (likely a DTM wall smear of a wall the level does not
  build); 0328 and 0091 are teeth at the foot or top of walls (walls.carve_terrain lets a terrain square rise across a
  wall "as a short bank of earth at its foot", which along a diagonal wall is a saw). Not fixed in the G1 thread.
- The skin's 90,000 bushes made check_level forest_floating jump 3,751 -> 31,847 (build test v2, 2026-10-23): canopy.check
  measured items against the terrain and mp_fill only, and the skin stands up to metres over the terrain. On the v2 zip
  every bush was 8 cm into the skin (PLANT_SINK), none over it. canopy.skin_height now reads the skin as ground (one
  tile at a time: the whole skin, 20 M triangles, in one TriSurface was OOM-killed in the 15 GB container): 1,690. A
  new kind of surface things stand on must go into every check that measures "ground", not only into its own step.
- The skin DAEs grew +51 % for +25 % triangles (v2): the rock/earth split, the clip along rw = 0.5 and the per-axis
  projection add vertices (0.59 -> 0.72 per triangle), and write_dae repeats every corner index 4 times in <p> (56 % of
  a skin file). One index per corner (all inputs at offset 0, valid COLLADA) measured -42 % on 80 tiles: not applied,
  it needs a load test in the game first (it would change every mesh of the map).
- Cut slopes patchy and low-res (michi's v3.1.1 screenshot, 2026-10-25, "rendi più omogeneo e alta risoluzione"): three
  causes in steep_skin. (1) The earth texture was 512 px over 3 m with bright green moss blobs and root lines: the
  same blobs every 3 m on every bank. (2) Each face took the projection axis it is turned to: on a rock face about 45
  degrees to x and y the relief flipped the axis from one triangle to the next, a patchwork of seams. (3) The rock
  texture's mean was 150 and the earth's 205 (and yellow, 225/212/167) for the SAME vertex colour at the line where
  they meet: a 27 % brightness and hue step along it. v3.1.3: textures 2048 px over 6 m, one mean (180, the earth
  nearly grey), axes from normals averaged over 4.5 m (smooth_axes), a cut-out fringe of earth over the rock in 5
  bands that nest (one alpha texture, alphaRef per band: border), the rock's moss calmer away from the line. A
  built level gets it from the finish step skin_blend (6 min, no-op after a build; the steep yards keep the old
  texture as t_hard_bank_*). +9 % skin triangles (the fringe), FPS not measured in game.
- render3d views of cuts were covered by big flat grey planes: the coarse far terrain (one vertex every 12 squares
  at far=2500, lowered only 1 m) spans the cut and stands over the skin inside the near region. It is not in the
  game; for views of cut slopes lower the coarse terrain (scratch monkeypatch of Renderer._terrain, cast=False).
- render3d draws every forest tree as a big cone or crown: views of slopes in woods show only trees. Render from a copy of
  the level without its `forest` folder (cp -al, then rm the folder: the hard links keep the original).
- Visual review of v3.1, group 3 ("scarpate stirate", 2026-10-25): most of the ~50 stretched cuts had NO skin at all
  (0022, 0338, 0548, 1011...): their steep vertices all lay within one or two squares of the road, inside `solid` (road
  dilated by 1), so skin_mask never seeded them and foot() only runs on from a skin that exists. 23,000 vertices over 50
  degrees near roads were bare terrain on the v3.1 zip. Before changing a texture or a threshold, check whether the face
  in the screenshot is the skin or the terrain: rasterise the near skin triangles over the terrain slope on a top-view map
  (mp_steep_bank_far parts index their own g1/g2 arrays: optimize_level.parse reads only the first geometry, so a probe
  that takes every part of a skin DAE gets triangles of 200 m). Seeding every steep vertex of the ring cost +48 % skin
  triangles; only those over STEEP_ROAD (45) and halving rock edges only over SUB_DZ 1.5 m: +11.6 % (19.4 -> 21.6 M).
  Halving edges alone did not round a face beside a road (0439): within ROAD_CLAMP the lattice was set to the terrain's
  facet and the relief capped at 12 cm, so it stayed one plane however finely cut. Now the clamp holds only the foot
  (CLAMP_HAB) and the relief may reach part of the clearance to the road edge (RELIEF_CLEAR); skin points over a road
  surface stayed 7 (none over 0.3 m) on the whole map. Each try = steep_skin on the whole released level (12 min) +
  renders (10 min): compare against a "before" run of main's steep_skin on the same copy (the step lowers the terrain
  again on a released level, so the released skin is no fair "before").
- render3d (textured) draws many road surfaces as smooth untextured grey: in the review renders a big grey sheet in front
  of the camera is the road or a yard, not a terrain slope.
- A 3x3 median "tooth" scan near the roads found 28,000 vertices, mostly in villages (yards, sidewalks): not a way to find
  a place from a screenshot. Find it from the video it came from (frames, then the road and the railway beside it).
- railway.carve_terrain kept every vertex more than CARVE_MAX (4 m) over the cutting, also one beside the bed: a lone
  vertex of the ground on top of the wall north of the line between Caslano and Ponte Tresa (-361,-2326) stood 4.1 m
  over it, and railway.build, which took the HIGHEST terrain sample across the bed, lifted the track 2.5 m onto it in a
  few metres: rails up a ramp of sleeper steps into the wall (seen in the piano video, v3.0.40; also 5 teeth at Agno
  near 2090,0). Now the carve lowers any vertex within one terrain step of the bed, and the bed sits at most LIFT
  (0.3 m) over the median of the samples. The same max sample made the 4 tracks at Ponte Tresa station climb 1 m to
  the face of the deck over them: the covered stations no longer feed the bed's smoothing. Checked in the cloud with
  TLM_EISENBAHN printed into a workflow log (swisstopo blocked here) and railway.build run on the released level
  (rebuilt "before" matched the released sleepers to the cm). render3d.Level takes the level name from the folder
  name: a copy of the level in a folder named otherwise draws none of its meshes.
- network.SKIP left out every swissTLM3D underpass (KUNSTBAUTE Unterfuehrung) with the tunnels: Via Golf (Caslano -
  Magliaso, 874,-1306) ran down into its cutting on both sides of the FLP and ended against 4-5 m of railway embankment
  (v3.0.40, 2026-10-23). The rails there are not a TLM Bruecke: the road line carries the structure. An underpass is
  kept only under a railway and under no road (network.underpasses; Caslano station's footway runs under the Via
  Cantonale too), and the lines over it become bridges there (over_underpass). In the TLM a Treppe (stairs) is not
  an underpass: filter on the exact KUNSTBAUTE value (a probe filtering "not Keine/Bruecke" listed 200 stairs).
  The first v3.1 build with it still had two faults there: the two 1 m footways kept with it took the DTM, which beside
  the road is the embankment smeared under the deck (2 m over the road, 1.2 m under the rail deck: the 9 new path
  "binario" obstacles of check_level, also in the v3.0.40.1 test build), and the survey's wing walls stood 0.4-0.9 m
  into the asphalt at the four corners (the drive-free band is a quarter of the width, and the survey has no road
  polygon in an underpass). network_surface.under_walkways puts the footways on the road + 15 cm, walls.drive_free
  frees the whole width + 0.3 m of an underpass. Not built yet (fixed after the v3.1 nightly) The wing walls of the nightly zip were
  patched in place (patch_underpass_walls.py, nightly_patch_v31.yml): only the numbers of the DAE's g-pa array
  change, so the solid stays closed and nothing else of the file moves (rewriting the 1.5 GB zip takes about 6 min).
  Pushing the walls out also showed the raised footway under the deck from the road (not patched: it needs the build).
  So the nightly v3.1 zip is NOT a plain build of its commit: compare a fresh build with it knowing the Via Golf walls
  were moved afterwards. The collision is the visible mesh ("Visible Mesh Final"), so the cars hit the moved walls. The
  patch script and its workflow are left out of the release PR to main (michi's rule, PR #49: no patch scripts there).
- A height band is not the lake: network.LakeCut cut every dtm05 cell between lake level -2 m and +0.15 m out of the
  surveyed paved polygons, and the floor of the Tresa valley below Ponte Tresa (268.6-270.5 m, lake 270.48) lost its
  yards and roads (about 1,800 4 m cells, network_holes 418 -> 1417 in the bridge thread's test build, 2026-10-21).
  Cut only the low patches that touch the surveyed lake (MU specchio_acqua), and check a lake cut by the area it removes.

## Yards, bare Concrete and river gaps (v3.1 visual review, group 5)

- The "grey-blue flat surfaces without texture" of the review (0205, 0207, 0410, 0473, 0485, 0493; two were reported as
  water planes) were no mesh at all: the terrain layer Concrete (classes edificio and bacino_idrico) where no building
  stands. terrain_colors.py measured Concrete on the open ground of those cells, which is the water of pools and basins:
  151,165,165, grey-blue, and the orthophoto base map made it bluer still. 36.6 ha of it lay bare (houses built into a
  slope, buildings missing from swissBUILDINGS3D, basins). Before calling a flat surface "water" in a screenshot, look
  for a water mesh there (level_objects/Water) and read the terrain layer: neither showed water at five of the six.
  Fixed by the finish step bare_concrete (nearest non-Concrete layer where no solid mesh touches it), a fixed Concrete
  colour in dati/terrain_colors.json (terrain_colors.FIXED) and no orthophoto base map for Concrete.
- The big yards (mp_hard_asphalt, 172 ha) had none of road_wear's dressing: it works along AI roads only. yard_wear (after
  road_wear, it needs its overlay materials) lays the blotches, dusty edges, patches and cracks on yards of 600 m2 or
  more (452 yards, +754k overlay triangles, mostly the blotch layer). Random patch angles looked scattered: lay
  rectangles along or across a yard's long axis.
- The Swiss survey stops at the border, which runs along the Tresa: where the river is all in Italy the water ended
  in a point (0391) and the bed went on dry under forest floor. rivers.osm_channels adds the channel along OSM
  waterway=river outside the survey (lowest ground of each cross-section + CHANNEL_DZ). Tested in the cloud only by
  emulation on the released level (the .ter as the DTM, the existing water as the survey): with CHANNEL_DZ 0.6 and no
  opening it also took ragged patches of the flat ground beside the Tresa below Ponte Tresa; 0.45 and an opening of
  2 cells left one small low patch. Check the build log's osm_channels / ha_osm_channels and the river near
  (-2250, -1060) in the first build with it.
- The render tool render.py of the thread was run on a `cp -al` copy; the .ter was replaced as a new file (os.remove,
  then write) so the hard-linked original stayed as it was. Cameras placed by hand at (x, y, z) without reading the
  terrain ended under the ground twice: take z from the .ter.

## Ground materials (visual review of v3.1, group G4)

- The pale grey-green banks all over the map (whole hairpins, every cut in the woods, 0456 at -3872,119) were the
  terrain skin's colour, not its rock: steep_skin.BaseColours looked a layer's colour map up as
  `t_base_<layer>_b.png`, and the twins added later (understory: ForestFloorVerge/Light, forest_mosaic: ForestRock,
  BankWood) have no such file: their vertices took a flat 0.55 grey, which EARTH_MIX made pale. Read the map from the
  level's terrain materials (baseColorBaseTex). A step that adds terrain layers must check every reader of layer names
  (BaseColours, render3d._layer_colors, groundcover lists), not only its own.
- The skin runs into the road (FOOT) and its colours are blurred over 3 squares: the light Asphalt/Concrete layer under
  the road meshes greyed the foot of every bank. The skin takes the nearest natural layer's colour (BaseColours.ground).
- With the colours right the skin was still about twice as bright as the forest floor round it (pale patches with a
  sharp edge, 0192/0509/0519): EARTH_MIX 0.45 pulled every colour towards EARTH, a light beige. Three rounds of renders
  to settle it: the terrain's brightness alone (as dark as the forest floor's macro colour, 62 sRGB, darker than the
  detail-textured terrain beside it), times 1.35 (meadow banks still pale beige: the desaturation, not the brightness,
  made the edge), then EARTH_MIX 0.25 at the terrain's luminance + EARTH_LIFT 0.08 (steep_skin.earth_colour). A full
  steep_skin rerun + renders is about 40 min in the cloud: try a tint on a few lattice colours against the ground
  colours of the review points first, and check it against the ground beside it, not alone.
- `pkill -f "[s]hots.py /home/..."` in a command that also named that path later killed the shell again (exit 144).
- The "asphalt on slopes" (0030, 0160, 0161, 0399) were survey yards (altro_rivestimento_duro) meshed on the DTM, which
  smears walls and terrace edges into slopes: 14 ha of mp_hard_asphalt at 20-60 degrees in v3.1. Finish step
  steep_yards (after steep_skin) gives yard faces over 18 degrees (32 %) the skin's earth (mp_hard_bank, same geometry);
  24 degrees missed the light ramp of 0399, mostly 10-20 degrees.
  The skirts (over 72 degrees) are left alone. Mean slopes per material lie: area per slope band is the useful probe.
- Gravel at 150 sRGB (surface_textures.BRIGHTNESS) read near white with a blue cast in the game's light (0280); now 124.
  Italy's setts and cobbles at 1.0 were the brightest thing in a meadow (0367): STONE_TINT.
- Roof colours were the orthophoto median over the roof: tree crowns over a roof made 5-14 % of the roof area green
  (0165, a shed with a "grass" roof). buildings_mesh.roof_colors drops the green pixels; a roof is never green.
- Checking these in the cloud: probe the level for terrain layers and mesh materials near a point (layer counts +
  mesh area per slope band) before guessing; render3d (no orthophoto) draws the terrain in the layer colours and the
  skin with its vertex colours, so it reproduces the pale skin. Rerunning steep_skin on a released level lowers the
  terrain under the old skin a second time (changed_max_m 4 m): fine for renders, never for a release.
- PIL `save` onto a path that is a hard link (cp -al copy) writes into the original too: remove the file first.

## Bridges

- On a bridge the survey draws the bridge (SOSF ponte_passerella), not the carriageway (LCSF strada_sentiero), so
  network.measure_width found nothing there and the deck took the nominal width of the class (3.2 / 4.5 m, decks of
  3.8 / 5.1 m) between approaches measured at 6-9 m: about 20 of the 64 road bridges of the v3.1 test build were a
  bottleneck (2026-10-23). A deck width equal to the nominal one is the sign. Now measured in the bridge polygon, or
  as wide as the narrower approach (network.widen_bridges, one width for a bridge in pieces).
- A survey bridge polygon is not always the deck: at Ponte Tresa the Swiss half is one 19.7 x 18.6 m polygon with the
  bridgehead, and the border bridge came out 18.7 m wide (a second piece, in Italy with no survey, took it over the
  chain). Its approach was no check either (the customs square measured 15 m). Polygon widths are now capped at the
  narrower approach + 2 m (network.cap_bridge_polygons) and Ponte Tresa has "width": 11 in ponti.json (supervisor's
  review, 2026-10-23). List every widened deck with old/new and approach width before handing a width change over.
- A survey deck (bridges.survey_height) was eased at its edges to the bare DTM, not to the road that joins it: the
  road surfaces (corridor, network_surface) are smoothed and differ from the DTM, steps of 0.3-0.45 m at the Magliaso
  bridge corners. Join a deck to the road mesh beside it (build_level passes the road tops as `surface`).
- The bridge thread tested in the cloud without a full build: a temporary workflow ran the downloads, network.py and
  `build_level.py roads` alone (about 35 min, the roads stage 21 min) and put the road meshes on the draft release;
  swapped into the extracted test build (roads/surfaces items + DAEs) they gave before/after renders and measures.
  First try of the road join took any road surface within 1 m: a path beside the bank pulled a deck corner 0.8 m
  down; within 0.5 m, and a surface further off is a drop (no join to the ground there either).

- Grass on the Ponte Tresa deck (v3.1 test, visual check group 6, 2026-10-25): the deck, 11 m wide since v3.1, lies on
  its Italian bank (Copernicus meadow, no survey) and paved_edges raised that ground to 5 cm under the asphalt; the
  layer stayed Grass because no_cover (no GroundCover) is made from the road carve, and the decks are not carved, only
  capped. 22 grass vertices there, 45 under all the decks. terrain.build_terrain now gives the verge twins (no cover)
  to the ground under a deck within DECK_COVER m of its slab. render3d draws no GroundCover: check grass by the layer
  under the road faces (Grass/GardenGrass vertices less than 1 m under a top face), not in a render.
- The Via Golf rail deck was a flat grey slab in the game: mp_rail_deck was a plain colour (railway.build) and its uvs
  the (x + z, y + z) of the track parts. Now Italy's m_concrete_old with box uvs, as the road decks.
- The "road ends on a raised slab" points of the visual check (0055, 0352, 0373, 0440, 0479, 0576, 0577): 124 of the
  128 km of paved outer edges more than 0.5 m over the ground were in the paved_edges keep-out (2 m of 1 m cells round
  walls, buildings, fences, guard rails, railway, water, parapets), where nothing over KEEP_OUT_LIFT is raised. Most
  of it was not a slab but a TRENCH: the road carve lowers the ground to 0.1 m under the lowest face within one
  terrain step, so beside (and under) a road that climbs into a slope it dug up to 1.7 m (0576), and near a wall it
  stayed. A first rule "raise where no wall is closer than the road + HOLD" (hold()) changed only 43,446 vertices and
  no render showed it; the second rule (pits(): ground higher than the road by PIT_UP within PIT_N steps, not under a
  road) does the work. Its first version compared with the vertex's NEW height and took the ground between the road
  and a wall as "higher ground": 327,373 vertices, also beyond retaining walls. Compare with the road height
  (block() now returns it). Together: 227,040 vertices, edges over 0.5 m 127.8 -> 49.9 km. 0448 and 0561 are flush
  (the line just ends), 0352 is the lake (water kept out), 0577's yard stands 6 m over the ground (over EMB_MAX).
  A rerun of paved_edges on a released level is no preview of a change: later steps moved things and the rerun alone
  raised 321,241 vertices. Run it twice (with and without the change) and take only the vertices that differ into
  the released terrain (about 15 min a run, PATCH_WORKERS=3). render3d cameras 9 m out from an uphill edge end up
  under the ground: put them on the road looking out. Do not truncate a log a running process still writes (nohup
  restarted on the same file left NULs and the old run's last lines in it).
- The Ponte Tresa road ends at the border on the Italian meadow (no Italian roads in the level): the deck end is flush
  with the ground (checked along the axis and 6.5 / 9 m to the sides); the "slab" of the shots is the deck's side over
  the bank. Not changed.

## Checking a finish step in the cloud container

- Rerunning a finish step on the released folder for a preview: copy it with `cp -al` (bng.LevelWriter replaces
  files with os.replace, so the hard-linked original stays as it was). steep_skin on the whole map takes 10-12 min.

- Actions artifacts and run log zips are blocked by the proxy; `get_job_logs` with return_content works, and a
  long log is saved to a file to grep. The nightly also attaches its reports to the pre-release (nightly_reports.zip).
- The released zip downloads in seconds with curl from `github.com/.../releases/download/<tag>/<zip>`; extract it
  (5.5 GB) and run the step on the folder (`bng.LevelFiles`). jsdelivr is blocked: render3d's three.module.js comes
  from the npm tarball (`registry.npmjs.org/three/-/three-0.170.0.tgz`) into `WORK`.
- swissNAMES3D is not reachable, so `places.villages()` is empty: the spawn spheres of the released level
  (village names on their main road) stood in for testing direction_signs.
- OSM ways run where the level has no road (Italy, beyond the corridors): a prop placed along an OSM road must
  first check the carriageway mesh is there (87 of 295 junction poles were in fields).
- "Off the carriageway" is not free ground: yards and squares (`mp_hard_*`) are driven on too.
- Render cameras placed along an OSM line ended inside houses; put them over the carriageway mesh, at the
  height of the mesh, and aim at the object's real position, not the planned one (it moves when it is placed).

## Bridges and survey data (v3.1, Magliasina bridge at the Magliaso roundabout)

- The cloud container cannot reach data.geo.admin.ch, geodienste.ch or Overpass (proxy 403), and cannot download
  Actions artifacts; it can download release assets. `ponte_ref.yml` fetches a swisstopo/survey window on GitHub and
  commits it; `ponte_test.yml` builds the level to a DRAFT release (not public) whose zip the session can download.
  The raw window (rif/, 6 MB of swisstopo data) is not kept in git: run ponte_ref.yml on a scratch branch to get it
  again, and delete the draft release when the test is read.
- A force-push that rebuilds a branch counts every file as changed: it started ponte_ref.yml and ponte_test.yml
  (path triggers on their stamps) and the first would have committed the raw data again. Cancel them at once
  (`gh api -X POST .../actions/runs/<id>/cancel`) or give such workflows only `workflow_dispatch`.
- A bridge drawn as a strip along the swissTLM3D line is only as wide as one carriageway: the Magliasina bridge is
  one 25 m deck carrying two roads, and the strip left the river showing through it for three versions. The
  survey (SOSF ponte_passerella) has the true outline, swissSURFACE3D the deck top (LiDAR class 17).
- Two swissTLM3D pieces of the SAME line (split at a node on the bridge) were paired as "twin decks" by
  twin_pairs (collinear, 0 m apart): the twin test does not tell a split line from two carriageways.
- swissALTI3D slopes down 1-3 m out from a bridge end (the bridge is removed and the abutment smeared): read the
  ground 1-3 m out (the highest) before calling an edge a drop or a join, or parapets stand across the road.
- The survey marks channelised stream banks as 'altro_rivestimento_duro' (hard surface): meshed as asphalt they
  were grey ramps into the river. landcover.channel_linings turns steep ones along a 'corso_acqua' into stones.
- A big grid is stored by Grid.save as `<name>.npy` + `.json` and the `.npz` is removed: checking
  `os.path.exists("dsm05.npz")` found nothing and the first test build fit no LiDAR plane (line heights only).
  Check both names, load with Grid.load("<name>.npz"), and grep the build log for what the step really used.
- Compare a test build with the last nightly by the road mesh it covers (roads/road_*.dae on a 4 m grid), not only
  by check_level counts: network_holes rose 418 -> 1417 and the cells showed two causes, the intended banks and
  network.LakeCut removing the paved yards on the Tresa valley floor (at lake level, 2026-10-21).

## Pavements and kerbs (sidewalks.py, v3.1)

- Up to the v3.1 test zip every pavement (mp_sidewalk) was meshed flush with the road (dz 0 on the shared edges): no
  kerb anywhere. The finish step `sidewalks` raises them on the built level (works on a folder, so a zip can be patched).
- The AI roads are as wide as the carriageway: "no kerb within the AI road's half width" lowered 94 % of the kerbs
  (the kerb IS the AI road's edge). Only the part more than 1.25 m inside the half width stays flush (AI_CLEAR).
- A yard (mp_hard_*) next to a pavement is not always an entrance: the survey draws a garden wall as a line between
  the two areas, so check the walls and fences along the edge before lowering the kerb (barriers()).
- Merged pipeline shapes have their position at the tile middle with z 0: lifting objects by the ground under their
  position would lift a whole tile. Skip objects whose position z is 0.
- numpy 2: np.cross of 2D vectors raises ValueError; write the 2D cross product out.
- Parking spots (city.sites.json) can reach over a pavement: a car spawned on a raised kerb jumps. The build keeps the
  pavement flush under them; the nightly patched before that had its 8 spots removed (patch_parking_kerbs.py).
- Props merged per tile (delineators, direction signs, OSM furniture) are not moved by changing an item position: lift
  each connected piece of the DAE whose feet stood on the pavement (sidewalks.py, merged_pieces_raised).
- sidewalks.py is not idempotent: on a zip that already has roads/sidewalks it finds no pavement in roads/surfaces.
  A follow-up to a patched zip needs its own small patch, not the step again.
- Roundabouts (roundabouts.py): the survey draws the setts round the middle as an island (islands.py raised it and put
  a keep-right sign on it), leaves asphalt under part of the middle, and the terrain makes a mound there; a green top
  on a plane cut through both. The middle reaches out to that island ring, the road faces under it go, and the top
  never goes under the highest terrain vertex round each point. The mean of an OSM ring arc is off-centre: use the
  box of the joined ways.
- Mapillary photos and orthophoto crops for a few points: luoghi_ref.yml commits them to beamng/verifica/luoghi/ref on
  the thread branch (a check only: never merge that folder; the photos are CC BY-SA).

## Bus stop paint (stop_paint.py, v3.1)

- The road paint is laid by rules (markings_rules.py, v3.0), not traced: anything the rules do not know is missing
  everywhere. Bus stop paint (yellow zigzags, BUS) was on 17 of 265 Swiss stops. stop_paint.py lays it from the
  orthophoto. The v2 trace had them only in pieces: network_markings' 2x2 opening breaks lines 1-2 cells wide, and
  faded yellow (saturation 26-50 in a 10 cm cell) fails its S>45 test. Measure thin paint against the ground round it
  (median of R+G-2B over 3 m) and join pieces before classifying. A join wider than 3 cells merged the bars of every
  crossing into one blob (156 -> 61 crossings).
- A yellow car, a flower bed and the yellow van of a bus yard read like letters or bars: drop marks with dark cells round
  them (windows, leaves), crossings need 3 parallel bars, and paint must lie on the asphalt faces of roads/surfaces
  (whitelist the materials: the up faces of mp_road_wall are wall tops). Paint "off the road" far east (x > 4000) is
  outside the level's network: OSM covers more than the map.
- The v3.1 stop paint still laid every traced shape it could not name (G9 of the v3.1 visual check, 2026-10-25): BUS
  letters and crosses of a faded bus yard came out as yellow blobs, a star and L shapes (Caslano station), a yellow bus
  front and a motorcyclist's jacket in the lane passed the "mark" test, a sunlit shade edge on a mountain road became a
  5 m yellow bar across the lane, the corners of bay frames passed as zigzags (Ln >= 4 m, low fill: an L has both), and
  the real zigzags were their traced outline widened, a thick wavy band. Now marks are not laid, a zigzag must swing
  left and right 3 times with 1 m legs and is redrawn straight from its centre line, and strips need 2 m and a zigzag
  or crossing within 15 m: 626 pieces laid -> 107 on the v3.1 zip. Look at a traced class over the photo crops
  (overlay of the polygons on luoghi/gialli, kept on claude/project-thread-bpnv3b) before laying it, not only at counts.
- islands.py (v3.0) put a short white beacon with a yellow reflector beside every keep-right pole: no island of the
  area has one, the photos show the pole's foot in a black and yellow sleeve (155 poles). Check a street object's look
  against a photo of the area before modelling it from a norm or from memory.
- Game views at a Mapillary photo's pose: the pose is off by metres and the nearest AI road can be a side road or a
  yard, so a camera at "AI node z + 1.45 m" stood on a parking lot higher than the road and saw nothing of a roundabout.
  Snap to the road the photo looks along and take the height of the asphalt faces under it.
- render3d skipped every merged shape whose position (the corner of its 384 m chunk) was over 300 m from a small view:
  whole blocks of Agno came out without buildings and looked like a level bug. The margin is now 560 m.
- luoghi_ref read only one orthophoto tile: crops near a 1 km tile edge came out half white. It now mosaics every tile
  the crop touches.
- Bus shelters (bus_shelters.py): "the edge of the asphalt" was found on parking.Ground.S, which holds every paved
  surface (yards, pavements): where a yard joined the road no edge was found and the shelter stood at the AI lane's
  half width + 0.5 m, on the carriageway (6 of the 36 v3.0 shelters, one on a roof). Read the edge on the mp_road_*
  faces only. The shelter (Italy's model) is not in the cloud and render3d draws nothing there: check placements
  by drawing the footprints on the orthophoto crops (luoghi/gialli has 60 m crops of every bus stop). The step took
  33 min because the edge scan asked TriSurface.height one point at a time: one call for the 32 offsets, 5 min.

## Meshes

- The FLP track showed as a brown zigzag in michi's video beside the cantonale (2026-10-22): the geometry is straight
  (no rail triangle wider than 30 cm in the v3.0.40 zip, rails straight in plan); the sleepers stood 16 cm out of a flat
  bed and low sun threw the rails' shadow in steps. railway.CRIB brings the ballast up to 4 cm under the sleeper tops.
  Not seen in the game yet (PC unavailable that night).
- Floating roofs left in the v3.1 test build (2026-10-22): the 5 check_level counted were all swissBUILDINGS3D
  `Flugdach` records (station canopies at Magliaso and Caslano, the fuel station forecourt, Sessa): the survey gives
  them "walls" that are only the 10 cm edges of the slab, so `len(walls) > 0` made buildings_mesh treat them as houses
  and canopy() never gave them posts. Do not tell a roof without walls by an empty wall list: look at how far its walls
  reach under the eaves. The check could not see the other kind at all: a house's own roof reaching metres out over a
  porch or lean-to with nothing under it (the house's walls touch the roof outline). Finish step roof_posts finds both
  on the built level (roof plan minus what tall faces hold) and adds posts. A detector that tests only the outline of
  a roof flags every normal eave (0.6-1.5 m): measure the overhang from the walls, not from the outline. Facade
  plaster between windows is made of faces under 0.8 m high: a "tall faces hold the roof" test with 0.8 m missed such
  walls and stood a post along a facade (TALL 0.35 m, above the 0.27 m fascias of roof_details).
  The first runs also doubled the posts of buildings_mesh's canopies (a wide canopy left free strips between its own
  posts): roof_posts now skips every roof that has a post already, told by the post vertex colour (post_color).
  roof_posts was first put right after roof_details, before fuel_stations: its posts would have counted as walls under
  the survey canopy fuel_stations replaces. Anything new that stands on the ground goes before parking/street_life
  (they keep off the building meshes) and after the steps that cut or replace building pieces.
  Keeping posts off the carriageway MESH was not enough: build test v2 had 3 new 'edificio' obstacles (road 43 -> 44,
  paths 172 -> 174), posts under porches and yard roofs where a road or path runs with no mesh of its own (check_level
  drives the swissTLM3D line with its width). roof_posts now also keeps off the AI roads with their width and the OSM
  highways (1 m round): anything placed on the ground must test the lines, not only the meshes.

- Roofs were a sheet with no thickness and plain folds at the ridges; tegole/metal textures of 2 m with thin, low-contrast
  lines read as one grey surface from 30 m (michi 2026-10-22, lake-shore house in the cinematic video). v3.1: finish step
  `roof_details` (rim with tile heads and fascia, ridge caps; after house_details/house_extras, which read the bare
  roofs) and new 4 m textures for coppi, tegole and metal. Costs: +931k triangles on 2.61M of the buildings (+36 %).
  A first draft of the tile colours divided the blue by the "redder" factor: blue tiles. Changing ROOF_TILE changes
  the roof UVs only in a full build: to preview new textures on a released level, scale the roof UVs too, or the
  tiles come out at half or double size. The many plain grey roofs of houses are `metal` (facades.roof_kind: grey
  orthophoto, slope < 25 degrees), not tegole: check which kind a roof is before changing a texture for it.
- Floating roofs (v3.1): 620 roofs of swissBUILDINGS3D have no walls at all (canopies, covered parkings, boat houses,
  platform roofs; OBJEKTART says "Gebaeude Einzelhaus", only 5 are "Flugdach"), so a kind filter finds none of
  them. 3490 more records are roofs alone too, but their house's walls are a separate record under them: tell them
  apart by the roof plan over the ground plans of buildings with walls (buildings_mesh.canopies), never by
  `len(walls) == 0` alone, or every such house gets posts and a slab.
- Finding them in a built level: union the roof faces per tile and look for faces of other materials near the
  outline that reach down from the eaves (check_level.floating_roofs). Counting "wall feet above the terrain" per
  vertex column gave only noise (chimneys, upper storeys, plinth decals): drop that approach.
- Posts are not right for every roof without walls: the cadastral survey says which are open (SOSF riparo,
  altra_parte_di_edificio: posts) and which are houses (LCSF edificio: walls along it). The unknown ones got walls
  under the roof at first, which turned a roof 12 m over a railway yard into a box across the tracks: walls only up
  to eaves SHED_EAVE m high (buildings_mesh.close_roofs). A pack made without missing_buildings.py counts 912
  instead of 620, because the survey's buildings it adds stand under 292 of these roofs: test against the built level.
- An attempt to add posts under roofs that overhang their walls by more than 1.8 m (issue #13) found 1260 roofs,
  mostly garage decks at ground level and canopies merged into a house's roof: not done, #13 stays open.
- render3d.Renderer resolves the shapes by the level folder's name: a test copy of a level must be called
  `magliaso_pura` (a copy named otherwise renders terrain only). Use `cp -al` (hard links) and replace the files you
  change by new files, so the original level is not touched.
- The cloud container cannot reach swisstopo: data packs come from a workflow that commits them to the branch
  (roofs_pack.yml, landmarks.yml). prepare_work.py crashed on the folder dati/far_imposters (fixed: folders skipped).

- Check winding/orientation when placing text or UVs along an outline: the fuel station fascia text was
  mirrored on outlines that ran the other way.

- BeamNG 0.40 draws a forest shape's imposters as opaque squares (white or dark grey, from one far tree in ten to the
  whole slope, for the rest of the session) when it bakes them itself during the session: shape newer than its cached
  imposter (every new build) or an empty cache. In v3.0 and the first nightlies (2026-10-20). The baked files are
  byte-identical to good ones: only the in-session bake and hot reload break. The game's own trees ship
  `<shape>.dae.imposter.dds`, `.imposter_normals.dds` and `.dae.asset.json` and are never baked; far_trees.prebaked
  does the same from dati/far_imposters (baked by the game, md5 of the DAE in baked.json): no bake, no squares.
  A test with a warm cache shows nothing wrong: delete `temp/levels/<level>/art/shapes/trees/far_*` first.
  The imposters fit only the DAE they were baked from: when a far model changes, far_trees prints "no imposter of ..."
  and check_level `far_models_without_imposters` goes over 0. Then bake them again in the game (empty cache, load,
  copy the two DDS of each model from temp) into dati/far_imposters and update the md5 in baked.json.
  Nightly #2 was patched in place (nightly_patch.yml), not built with them: the nightlies from #3 carry them from the build.
  dati/far_imposters is the first folder in dati: prepare_work.py shutil.copy'd every entry of dati and a fresh build
  failed at its first step (IsADirectoryError, found by "Tetti fluttuanti"). It now skips folders; far_trees reads
  them from dati itself. A new folder in dati needs the same: check that prepare_work and package skip or read it.
- Translucent overlay materials need `"translucentZWrite": true` (as Italy has them): without it the game draws
  them in a pass that takes no shadows, and they glow under cars and trees (road wear, 2026-10-18). DecalRoads
  draw on the road meshes only with `overObjects` set, and they do not fix that by themselves.
- With `translucentZWrite` the overlay layers of one mesh must be drawn lowest first: a higher layer drawn first hides
  a lower one drawn after it (road wear, 2026-10-20). And a band laid over the road with only 3 rows across lets the
  road's crown and crests poke through it (holes in the wear): rows at most 2 m apart, lifted where the asphalt is
  too close (road_wear.clear_of).
- The game draws one side of a face, so any gap in a mesh is a hole you see through. The roadside walls
  (walls.build_roadside) were only a face and a 1.75 m cap: where a run ended one saw under the cap into the bank
  (issue #76, 2026-10-20). Close every solid: back and end faces (walls.roadside_shut).
- walls.wall_feet_step took "a vertex lower than another at the same x, y" for a foot: where two wall pieces of
  different heights meet, or the two faces of a thin wall touch, it pulled the lower TOP corners to the ground
  (5,831 notches in v3.0). Vertices of `*_top` triangles are never feet. A first fix (measure "wall on a bridge"
  from the highest terrain vertex) raised the notches to 7,986 before that exclusion: after moving vertices,
  check which triangles (top or side) they belong to.
- A road can stand metres over the terrain carved under it: wall feet measured only against the terrain hung over
  the asphalt (slots up to 60 cm). The road surface within 1 m is the ground too (wall_feet_step, FOOT_ROAD).
- Counting holes: an edge of only one triangle over the ground is a hole unless another face closes it. Weld all
  the wall shapes together and look across the edge in its triangle's plane, under a top's edge and behind a
  side's edge (check_level.wall_holes). A test only "15 cm under the edge" counted the edge's own quad as cover.
  Weld by distance (cKDTree pairs), not by rounding to a 5 mm grid: rounding split corners 1 mm apart across a grid
  line. The edge's own triangle is the one with all three of its corners: skipping every triangle that touched one
  end skipped a face doubled along another's side (10 m counted). Not holes, nothing to see: triangles of no width
  (slivers left by the `difference` cuts of wall_footprints), faces back to back, edges lying in other faces (T
  joints). With these the 56 m of the first v3.0.40 nightly were 8.5 m of cm cracks.
- Two walls side by side a few cm apart (the two lines the survey draws for one wall, left unjoined by
  walls.paired_lines; pillar notches) show a dark groove from above that the hole check cannot see (no open edge):
  1,100 gaps, 8.6 km in v3.0 and the first v3.0.40 nightly. walls.wall_gaps_step lays a lid on every gap narrower
  than 25 cm between the tops. Measure the rise across the gap per lid triangle: over the whole gap it skipped the
  walls climbing with the road (4.8 km left). A CDT of the outline joins three corners in a line into a mm-thin
  triangle that stands up as a fin (open edges): flip it with its neighbour (walls._no_slivers). Why paired_lines
  leaves these pairs is not known; one suspect is `ga.intersects(gb)` (lines that touch are never paired). Not
  changed: the AV survey is blocked in the cloud, so it could not be tested.
- A released zip can be checked in the cloud without a build: unzip the parts a finish step reads and run it on that
  folder (bng.LevelFiles takes a folder). pip install shapely pyproj rasterio opencv-python-headless playwright;
  render3d needs three.js from `npm pack three@0.170.0` (set render3d.THREE). Cameras placed by guess ended
  inside meshes: put them on a road vertex beside the target, at eye height, looking at it. The merged shapes
  (walls_m3_*) have their position at a corner of a 384 m chunk: a scratch script that read the shapes within
  200 m of a point missed the walls there.

## Undergrowth (understory.understory_step, groundcover.UNDERSTORY_COVERS)

- ECA's `lush_ferns_*` (art/shapes/groundcover) use the material `forest_vegetation`, which East Coast USA itself
  does not define (Cliff and driver_training do): a material lookup in the model's own level found nothing. The
  definitions of the undergrowth models are in dati/understory_materials.json (taken from the game, 2026-10-22).
- An edge band measured from "any other layer" made the whole wood outside the area a light-green speckle: the land
  cover leaves specks of meadow inside the forest. Openings under 400 m2 are no edge (SPECK_M2).
- The trees' crown radius from the model's bounding box (asset_bounds) is wider than the leaves (median 7.3 m): with
  it no forest floor was ever in a gap (0.03 %). The gap test uses the distance to the nearest trunk instead.
- A GroundCover places shapes upright on the ground, not along the slope: a 10 m fallen tree on a 30 deg slope hangs
  5 m in the air. The first limits (9 and 14 deg) still lifted an end 0.7-0.8 m (supervisor review): 4 deg for
  tree_beech_dead_b, 6 deg for _a.
- A GroundCover takes at most 8 Types (Torque3D MAX_COVERTYPES; every GroundCover of the game's levels has at most 8).
  The first version had 16, 34 and 18 in one object each: if the cap holds only the first 8 (all shade rows) would
  have stayed and the light zone would have had nothing (supervisor review, 2026-10-22). Now one GroundCover per
  layer, at most 8 Types each, which also stops one layer's types thinning another's (groundcover.density).
- GroundCover plants have no collision: stumps and 1.5 m stones near a road are drive-through ghosts. Keep them in the
  shade; in the light only small stones, and every model's reach checked against its box (check_light_reach).
- A finishing step can only be tried on a released level after undoing what the step itself added: the released
  .ter already has the verge twins and understory_step refuses it. Map the Verge layers back and drop their names
  from the .ter tail, terrain.json and terrain materials (done for the v3.1 test, 85 s for the step).

## Forest floor (understory, forest_mosaic)

- `understory.face_cells` over the terrain skin (`level_objects/terrain_skin`, 3.9 GB of DAE, ~20 M triangles) ran more
  than 30 min without finishing in the cloud; the SOLID groups alone take about 2 min. The skin's triangles are about a
  terrain square: rasterise its vertices (forest_mosaic.skin_cells, 23 s).
- understory.py imports trees.py, which needs scikit-image: a patch workflow that imports understory must install it.
- The shade rows of the undergrowth hold 10 m fallen beeches and 4 m clumps: understory kept the shade EDGE_M (10 m)
  from every edge. Narrowing the edge to 3 m along roads under the crowns (forest_mosaic) first put the shade 3 m from
  the asphalt; within SHADE_CLEAR_M of a solid mesh there is now only light (reach-checked models) or bare litter.
- A steep bank (Bank layer, >40 deg) is not an opening of the wood: counted as one, the cut slopes made every road in
  the wood look like a meadow edge (wide light bands). Thresholding one smooth noise field gives round blobs with
  smooth outlines: add a finer octave (forest_mosaic._field).
- The terrain skin is not in understory.SOLID, so the undergrowth (and at first the mosaic's woodland grass and outcrop
  stones of 2 m) stood on the forest layers under the skin of the road shoulders, through it beside the asphalt; the
  integrator saw it in a render of this thread (2026-10-23). The skin is ground of its own: no forest layer under it or
  within two squares (forest_mosaic: the verge twins there), outcrops ROCK_CLEAR_M and bank stones BANK_CLEAR squares
  from it and every solid. Check every new GroundCover against the road AND the skin footprint in a render.
- `/usr/bin/time` is not installed in the cloud container (a background run died at once): use resource.getrusage.
- "No grass in the wood" (michi, 2026-10-25, v3.1.1): v3.1 had grass only on the light twins; the shade had none, and
  the verge twins were both "near a mesh" and the mosaic's bare litter, so 75 % of the wood floor 5-10 m from an AI
  road and 50 % at 25-40 m had no plant at all. Measure the layer shares by distance to the AI roads (what the car
  sees) before tuning a cover's density. Now the litter twins (forest_mosaic.LITTER, +2 terrain layers) take the
  bare litter more than two squares from any mesh or skin, and SHADE_GRASS/LITTER_GRASS put grass there; finish step
  forest_grass does it on a level of v3.1. The ground right beside most woodland roads is the terrain skin (a mesh):
  no GroundCover can green it, only its own bushes. The first density (1 tuft per m2 in the shade) looked bare in
  the renders: 2 now. The renders draw each billboard as a 6-blade tuft, thinner than the game's textures: judge the
  density in the game.

## Tunnels (tunnels.py, finish step `tunnels`, 2026-10-26)

- The swissTLM3D tunnel lines of all of Ticino come from tunnels_ref.yml (beamng/ticino/dati/tunnels_tlm.json.gz): 436
  lines, 346 km. In the Malcantone level only the FLP Galleria del Vallone d'Agno (60 m, 2064,-54 -> 2091,0) joins
  the built meshes: Crespera has no track near it, the other road tunnels are in Italy or outside the network.
- A portal is "live" if a road or track mesh is there. Rail heads are 7 cm wide: a point-in-triangle test at the
  portal never hit one and the first run found no live portal. Tops.height takes the median rail-head z within 2.5 m.
- Holes are terrain layer 255 (no render, no collision). Anything that indexes a lookup table by layer crashes on it
  (render3d's layer colours did: IndexError 255). So the step runs last among the steps that touch the ground
  (after vineyards_ground). Steps that read layers (steep_skin, forest_mosaic, understory) must never run after it
  without handling 255. The assumed square convention (sample (r,c) owns [c..c+1] x [r..r+1]) is NOT checked in the
  game yet.
- The first tube had no straight walls: the inner sweep took ring[1:-1], so the vault started at the wall top and
  one saw the lake under it from inside. Sweep the whole ring.
- A yard of the roads group (mp_hard_bank of steep_yards, meshed on the DTM over the tube) stood inside the tube as a
  big curved grey sheet: the roads are cut too (in_volume only, so a road on top of the tube stays). Check the inside
  with a probe (points of every group inside the inner profile), not only with renders.
- In render3d the coarse far terrain (step > 1) spans the holes and draws a grey sheet through the tube that the game
  does not have. Lower it in the render script, as for the cut slopes.
- The camera "25 m out on the tangent" stood inside the bank: the track curves before the portal. Place cameras from
  the Tube's own stations.
- cut_meshes read every shape of the groups across the whole level (76 s for one tunnel). Skipping shapes whose
  position is more than SHAPE_REACH from a tube: 12 s.
- Importing config without MAGLIASO_ROOT made a folder "D:\beamng_magliaso" in beamng/pipeline (Windows paths taken as
  relative): export MAGLIASO_ROOT before any scratch import.
- In the game (laptop run 3) the vault stood bare behind the S headwall: the DTM's portal cuttings reach 4-8 m into
  the swissTLM3D tube and on the lake side the slope stands under the shell along the whole tunnel (holes there, the
  shell was what one saw). tunnels.mound raises the terrain over the tube (COVER_MIN over the shell, 1:1 down over
  MOUND_W, never over a road/track face beside it): shell points over the ground 38 -> 0, holes 100 -> 27. Raising
  vertices up to the headwall's back made the terrain and the hole caps in front of the face slope up into the
  opening (spikes on the track): only from the swissTLM3D portal in. A floor plate now covers the stretch under the
  headwall (one saw the lake through the holes beside the ballast). Check with a probe of shell points vs the
  terrain (square_height, holes skipped), not by eye.
- Laptop run 4: the headwalls stood on nothing on the lake side (ground 2.4 m under the floor beside the track, the
  wall's sides ended 0.6 m under it): a gap under the S portal at track level. Each side now goes FOOT under the
  lowest ground at its outer edge, with the triangle under the floor's edge closed.

- Galleria Vedeggio-Cassarate (zone ti_1_0, 2026-10-29, michi: "mi sembrava rotto"): swissTLM3D splits a tunnel's line
  wherever its class or a junction changes, and every piece was a tube of its own built only with a live portal. The
  29 m piece before the Cassarate portal had none: a 29 m gap in the tube, the main tube ending open in the hill. The
  portal's two one-way lanes (Einfahrt 15 m, Ausfahrt 11 m, 4.6 m apart) were two 6.6 m tubes standing in each
  other's lane. tunnels.chain joins pieces end to end (a node of two lines, or the straightest pair under CHAIN_TURN),
  makes two short lanes ending at portals PORTAL_SPAN apart one piece as wide as both (the whole tube takes the widest
  piece: Vedeggio-Cassarate is 9.2 m of carriageway now), and a branch left at a node of three lines (the 8 m service
  access) gets no portal at its joined end; open_junction takes out the faces of either tube standing in the other's
  clear space. A group of lines that meet is built when any of them has a live portal. All of Ticino: 436 lines ->
  340 tubes. Checked in the cloud on the pack alone (a plan view of the junction, no face in a driving envelope), not
  in the game. Look at the lines of a tunnel in tunnels_tlm.json.gz (the pieces, their classes, which ends touch)
  before blaming the tube geometry.

## Streaming helper process (beamng/ticino/helper, 2026-10-29)

- michi asked for a separate local process that streams to the game. Only DATA can come from outside: the terrain
  window (.ter + base map) is made by ticino_helper.py with numpy and handed over as files (temp/ticino/helper). The
  scene work (terrainFile/postApply, TSStatic, Forest, ProceduralMesh, reloadCollision, map.reset) has no API from
  outside the game thread; BeamNGpy would run its commands in the same Lua. A .exe cannot ship in a repository mod.
- In the simulator the Lua window was ~1/3 of the first jump's frame (382 of 1,106 ms); the in-game freeze at that
  jump (5 min, a core at 100 %) was in an engine call, not the Lua (thread "Far partire BeamNG con il Ticino
  completo"): the helper cannot fix such a freeze, check where the time goes before promising a gain.
- tests/sim_stream.lua had no TerrainBlock:getPosition stub (stream.lua checks the block after the swap) and crashed
  at the first jump; there is no luajit in the cloud: `python tests/luajit.py <file.lua> args` (lupa). `REALTIME=1`
  runs the sim in real time, else a helper beside it never keeps up with simulated driving.
- The perf csv of the sim is written 10 frames after a swap: a sim of 0.02 s writes none.
- In-game test on DESKTOP-OUPOLOA (2026-10-30, camera flight from ti_0_0_spawn_manno north, 33 m/s, 10 km, 7 moves,
  4 runs): the helper works (every move helper=1, buildMs 0, 52-104 ms wait at a jump, a window 5-16 ms .ter +
  17-28 ms base map) but the game is NOT smoother: 28.1 vs 28.4 fps mean at 30 fps with warm caches. Without it the
  Lua made the window in 104-307 ms spread over 25-37 frames at its 4 ms budget, so no frame was long because of it.
  The hitches are engine work: the swap frame (terrainFile ~105 ms, 207-256 ms frame), the forest after a spawn
  (~75 frames of ~190 ms) and the AI map re-read at a jump (25.6 s). Measure where the frame time goes first.
- The first pair of runs was useless: run 1 (helper) found the shape cache cold, run 2 (no helper) warm, and the
  game ran up to 105 fps. Run the A/B pair twice and compare the warm pair. The FPS cap is
  settings.setValue('fpsLimitEnabled', true) + settings.setValue('fpsLimit', 30) ('FPSLimiter*' does nothing).
- forest.PER_FRAME 250 -> 64 (ticino 12c25f3) did not remove the ~190 ms frames after a spawn (118 -> 110 forest
  slow frames, max 223 -> 202 ms): the cost is per frame that touches a Forest, not per item. Try touching fewer
  Forests / fewer frames (a whole tile's items in one frame), not fewer items a frame.
  Now forest.ONE_FOREST: a frame finishes the pass of one tile and stops (PER_FRAME only a cap of 4,000), and a far
  tile gets one pass, not the wave's two (each pass is a frame touching its Forest). Not measured in the game yet.
- Teleport bug (2026-10-30, spawn.safeTeleport from Manno to ti_1_3_spawn_bellinzona): the jump swaps the terrain
  (right window, heights right, spawn z 227.3 = terrain) but the ground stays plain grey and no object of Bellinzona
  comes for ~65 s: the objects queue keeps importing the ti_0_0/ti_1_0 shapes of Manno after the jump, the forest of
  the old place hangs on the horizon. A jump must drop the old queue and put the new place first. michi saw it.
  In the code: at a jump objects.step(clock, nil) broke after the first spawn over SLOW_SPAWN_MS (every shape of a
  zone never seen is a COLLADA import), so the paused jump made ONE object; the far ground (the mountains) was made
  only when the object and forest queues were both empty; and the old place's deletions sat behind the new rings.
  Now (ticino): a jump farther than twice the objects/forest radius deletes every streamed object and tree at once
  (objects.dropAll, forest.clear, while paused), makes the near rings whole (step untilRing, no heavy break without
  a budget) and FAR_JUMP_MS of far ground, and the far ground also gets FAR_EVERY_MS each frame beside the objects.
  The grey ground (base colour map, log "base 0.0 ms") is not explained yet: read the jump's log lines.
  PC test of 79f0e61 (spawn Manno, jumps to Bellinzona and Airolo, 30 fps, warm cache): Bellinzona's jump removed
  4,330 objects and 14,647 trees at once; slow forest frames 110 -> 0 (ONE_FOREST), frames over 100 ms 139-249 -> 96,
  mean 25.4 fps. The paused jump frame is longer (spawn 8.1 s, Bellinzona 8.7 s, was 3.9-5.2 s; Airolo ~4 s): the
  near rings and FAR_JUMP_MS are made inside it. Still seen: 2 object frames of ~0.9 s 60 s after a jump and 25 of
  ~215 ms at 100 s (the traffic starting). The ticino stream.lua without PR #105's aimap hook gives 12,849 "Map node
  could not be set" again: expected until #105 is merged. "base 0.0" at every jump, grey ground not confirmed.
  Now ring 0 is made whole at a jump, rings up to NEAR_RINGS only for OBJ_JUMP_MS (2.5 s), FAR_JUMP_MS 2000 -> 500 (the
  rest in the next frames, nearest first). "base 0.0 ms" is expected (setField only stores the path, the engine
  reads the texture later): setBase now logs a base map file missing at a swap and an empty list of base materials.
  PC test of b45a209: jump frame 6.55 s (spawn) and 7.35 s (Bellinzona), swap 110 ms, no "base colour map" line (the
  file was there): the near rings were not the cost. The jump frame is the SUM of its budgets: FOREST_JUMP_MS was
  3000, then OBJ_JUMP_MS 2500 and FAR_JUMP_MS 500. Now forest 1000, objects 1500, and the "jump to tile" line gives
  the ms of each part (files, drop, swap, objects, cols, forest, far). Airolo's jump wrote no "jump: window" line
  twice: jump() now logs its start and a failed window job, read those lines next time.
- 13 fps standing still in Lugano against Italy's 81 (2026-10-30, CPU-bound, GPU ~30 %): every streamed TSStatic was
  created with dynamic = true (copied from BeamNG.Earth, to spare the cached sun shadow map a redraw per added object),
  and a dynamic object is sent once per shadow cascade every frame. setField('dynamic', 0, 'false') on the 5,392 live
  TSStatics: 14.0 -> 83.2 fps. objects.DYNAMIC is false now (settings "dynamicObjects": true for the old way). Setting
  dynamic back to true at runtime did NOT bring the cost back: an A/B test must reload the level, not flip the field.
  The base scene's 57k AI DecalRoads and 4,343 SFXEmitters were not the cost (127 and 327 left near Lugano after a jump).
- After the static fix (2026-10-30 evening, PC sweeps at Lugano with the queues empty): 49 fps against Italy's 81, and
  hiding the 103 props TSStatics alone gave 85 (all TSStatics hidden: 116). No single prop shape mattered (hiding one
  at a time: nothing) and dynamicCubemap off on the 1,146 materials did nothing: the cost was material blocks.
  region.split_dae / clip_dae kept EVERY <triangles> block of the source in every piece, an empty one as a triangle of
  no area; the merged sign/prop shapes have hundreds of materials, so each 192 m piece was hundreds of draw calls per
  frame and shadow cascade. _write_kept now drops the blocks it keeps nothing of (60 materials split into 23 pieces:
  1,380 -> 222 blocks). Count the <triangles> blocks of a cut shape, not only its triangles.
- SETTLE_MS (objects made dynamic, then flipped to static in batches) was worse than static from the start: with the
  queues empty 13 fps against 50; an object flipped at runtime stays costly. Off by default, kept for tests.
- The queues while standing: an object costs ~8 ms of engine in the game; at 3 ms a frame the ~4,500 objects of Lugano
  took minutes, and every frame that changed the scene was slow (14-20 fps the whole time). Bursts (BURST_MS 40 once
  a second, every 200 ms below SLOW_MPS) made the flight 47 -> 94 fps. Giving the trees 40 % of each burst made 91
  slow bursts (up to 711 ms, 89 fps); "one Forest a burst + a clock check inside the tile" was WORSE (204 bursts of
  ~220 ms, 80.5 fps): a frame that touches a Forest costs ~200 ms whatever it adds, so more partial touches = more
  hitches. The objects take the whole burst and the trees only what is left (93.5 fps, debf2f8).
- Flight at 33 m/s (2026-10-31): the "near" frames of ~200 ms were forest passes (one Forest touched costs 185-230 ms
  whether it adds 140 or 1,305 items). Hysteresis of the shares (forest.HYST) did not change them; sharing one Forest
  among BLOCK x BLOCK tiles and doing their passes in one frame did: BLOCK 3 near-forest frames 63 -> 3, frames over
  100 ms 130 -> 52. With the props fix (empty material blocks) Lugano standing still is 84.4 fps against Italy's 81.
- Burst A/B/C flight (2026-10-31, second of two runs each): A standard (40 ms, adaptive) 80.0 fps, 1,030 frames over 50 ms;
  B fixed 1 burst a second 89.9 fps, 504, but the deletions (WAVE_DEL_AT, behind every new object) never came: 10,649
  live and 45,524 queued after 5 min; C BURST_MS 20 86.3 fps, 672, queue 3x A's. A deletion that waits behind the adds
  never runs while driving: objects.stepDels now takes the tail of the queue for BURST_DEL_MS of every burst, BURST_MS
  is 20 and the adaptive interval counts only the objects to make (addsQueued).
  PC flight of 83fabe4 (D, default): 94.2 fps, 87 frames over 50 ms (A: 1,030), 25 over 100 ms, no slow bursts, 2,231
  live at the end. E (one burst a second) 97.9 fps but the queue 3x behind: D stays the default. Left per 5 min flight:
  ~9 forest frames ~190-250 ms (one per new 3x3 block, every ~1,150 m), ~5 object frames 160-479 ms, 6 terrain swaps
  ~250 ms, the jump (swap 2.35 s: position 1.16 s + terrainFile 1.19 s). The object frames were the near ring after the
  jump, ONE building a frame (OBJ_BUDGET_MS 3 and the one-heavy-object break) with spawns of only 4-42 ms: the frame cost
  is the engine's per frame that adds a building. The near rings now get NEAR_BURST_MS (40) a frame with no heavy break.
- PC flight of ef915d5 (2026-10-31): 93.1 / 95.1 fps, frames over 50 ms 171 / 124 (83fabe4: 87): the near bursts
  work (225 objects in one 188 ms frame), but ~38 s after the jump 6 "near objects" frames of 122-461 ms added only
  2-8 objects each (road_wear, road_m3, skin pieces, slowest spawn 10-36 ms). The slow-frame line now gives the sum
  of the spawns and the streamer's own Lua time of that frame (st.luaMs): frame minus Lua = engine, to tell before
  guessing (shadow cache redraw, material first use, collision).
- PC tests of d945d41 (2026-10-31): sun shadows off (113 fps) and NEAR_BURST_MS 150 (worse, a 579 ms frame) did not
  remove the 2-3 frames of 450-580 ms that add 3-7 objects (Lua 40-50 ms, the rest engine). Hypothesis "PNG textures
  cooked on first sight" (1,838 PNGs, 578 Mpx outside the warm-up's mp_ch_/mp_fuel_) was WRONG on disk: the flights
  wrote only temp/art/terrainMaterialCache/<hash>.dds (one per terrain swap, part of its ~230 ms). The slow frames are
  a first use per SESSION: gone on a second flight in the same session, back after a restart. Next: tell material
  first use from shape first use (jump to another zone first, then fly).
  It was neither: spawning in Bellinzona and arriving in Manno later, Manno (first visit) had no slow frame, and the
  8 frames (125-483 ms, 4-8 objects each) always came in the 2 s right AFTER the first jump's map.reset frame (28-32 s),
  wherever that was; the AI map is read once a session (later jumps keep it), hence "first use per session". Not
  dropAIRoads either (same frames with DROP_AI_ROADS false, which costs 0.7-1 s a terrain swap). beamng.log shows only
  "GpuCull| registry: <n> instances" lines in those seconds (the engine rebuilding its GPU culling registry). stream.lua
  now keeps the game paused RESET_HOLD_MS (3 s) after that map.reset while the streamer goes on, so the tail passes
  in the pause. Read the frames before a slow frame too: a 30 s frame just before it is the likelier cause.
- BeamNG 0.40.4 GE Lua: ffi.cast('const uint8_t *', aLuaString) returns the string itself, and pointer arithmetic on
  an ffi.new('uint8_t[?]') array failed with "bad argument #1 to '__add' (invalid C type)" (aimap.lua:33/36): the
  precomputed AI map never loaded. Read binary files with string.byte / plain Lua there, and test in the game.

## Data from the cloud sessions

- swisstopo (data.geo.admin.ch, api3), Overpass and the BFS register (public.madd.bfs.admin.ch) are blocked from the
  cloud container (proxy 403). Compute anything that needs them in a small GitHub workflow that commits its result
  to the branch (strade_extra.yml, paesi_interi.yml), and test the code locally with stand-in inputs first.
- Growing the area (area.py) changes what the pinned extracts in beamng/dati must cover: re-pinning them pulls newer
  data for the whole map. Add only what is new (download_gwr.py --add) and check the OSM extract's bbox.
  It also leaves the README/website map (web/map.svg) stale: v3.0.40 grew to 58.6 km2 and the map still showed
  56 km2 without Caslano until v3.1 (michi noticed). Rerun `python web/tools/make_map.py` (needs shapely, pyproj).
- `osm_area.json.gz` is Overpass `out geom`: a way's points are in its own `geometry`, the `node` elements are only
  tagged nodes, and the `bbox` is the nodes' bbox. Looking ways up through node elements found none near a Caslano
  slipway and the integrator wrongly reported Caslano missing from the extract (2026-10-20).
- Overpass answered 502/504 from GitHub runners to every query on 2026-10-20, even 1 km boxes, for hours: read OSM
  from the Geofabrik extract with osmium instead (download_osm.py --add).

## Asphalt age from the photos (road_age.py, asphalt_survey.py, v3.1)

- In the 2024 SWISSIMAGE the shadows of trees are 0.15-0.4 of the asphalt and new asphalt is about 0.6 of old: shadow
  masks relative to a road's own median failed on roads that lie wholly in the wood (the median was the shadow). Mask
  against the asphalt of the 1 km photo tile and grow the mask by 2 cells: the half shadow reads as new asphalt.
- The first patch search found 1,178 "patches", nearly all shadow fringes, dark cars beside light ones and road
  edges: keep only dark rectangles with sunlit road all round them (ring test, no light car next to it): 36 left.
- The two halves of a road segmented apart rarely agreed where a stretch is new, and drew a joint along the axis
  almost everywhere: a half next to a new one that is unmeasured or nearly as dark is new too (Survey._halves).
- TriSurface.height(..., "near") needs a zhint for every point: a point without a height of its own goes through
  "high" first (road_wear.top_height), or it fails with IndexError.
- road_wear.outer_edges counts the edge against a pavement as a joint (the pavement is in Sall): kerbed edges never
  reached the drains; they are found on their own (outer_edges(..., Sk=...)).
- Mapillary's map features over the bbox of the AI roads: 89 drains, only about 20 near the map's roads (the bbox
  takes in Italy and the hills): the drains come mostly from the low points of kerbed edges.
- The sidewalks patch moved the pavement tops from roads/surfaces to roads/sidewalks while the road_age patch was
  queued behind it: road_wear would have seen no kerb on the patched zip (crumbled edges along every pavement). A
  step that reads another step's meshes must read them where either order of the finish steps (build or nightly
  patch) leaves them; cancel a queued nightly patch when the zip changes under it (run 39975412003, cancelled).
- Do not point a new material at a game texture the level never used (Italy's t_thin_damaged_edge): game_paths
  does not know where 0.40 keeps it, and a missing texture is a hole in the road. The crumbled edge is drawn here.

## Street photo reference (street_*.py)

- Google Street View terms forbid bulk download and derived data: michi asked twice, it was declined. Use Mapillary,
  Panoramax and KartaView (open licences) plus swisstopo; the step reads extra panoramas only from WORK/sv/pano.
- Mapillary, swisstopo and Hugging Face are blocked from the cloud container: run the network steps in
  street_reference.yml (token from the MAPILLARY_TOKEN secret) and commit only small results. Its devpack job
  commits photos (74 MB): purge them from a branch before it is merged (rebuild the branch without them).
- Pose fits: a fit with a big heading turn and a mediocre building overlap was a false match (a dashcam turned 31 deg).
  Gate on IoU >= 0.45 and >= 0.6 when the heading moved more than 12 deg (street_zone.accept).
- The scene render must open the alleys (street_scene.open_alleys): the 0.5 m DSM closes narrow alleys and
  every photo there failed to fit.
- Hedge votes landed on facades behind the strip when voted at the 3x3 max height: vote just under the cell's own
  top (street_hedges.VOTE_DOWN).
- Facade openings from Grounding DINO: about half the windows missed, eaves bands taken as balconies, a stone arcade
  as a garage. A facade with no detections must never blank a seen wall (facades.Measured.evidence); measured
  facades are off unless MAGLIASO_STREET_FACADES=1 (michi 2026-10-20).
- Roofs: the game's roofs agree with the photos within ~0.5 m (median bias +0.15 m); a one-photo difference is
  noise. Apply only with 2+ photos agreeing (street_collect ROOF_*).
- props_osm: a local helper named like the module-level box() shadowed it and would have crashed the build:
  grep for an existing name before adding a helper.
- Torch with default threads in parallel zone runs oversubscribed the CPU (hours): STREET_THREADS=1 per process.
- pkill with a pattern that is also in your own command line kills your shell (exit 144): kill by PID.
- The photo hedges were applied in understory.main(), which the build never runs: it copies dati/understory.npz
  as it is (prepare_work.py), so nightly #1 had none of them (2026-10-20). Hook new data where the build reads it
  (vegetation.py now applies understory.photo_hedges), and check the build log prints the hook's counts.
- A workflow's commit step pushed nothing: `git pull --rebase` refused because street_collect also rewrote a file
  that was not committed (street_facades.json). Restore the rest (`git checkout -- beamng/dati`) before pulling.
  Tile results stay in the run's artifacts: rerun only the collect with mode=area from_run=<run id>.
- The whole-area run measured 31 roofs off by 0.5-2.9 m, 28 of them too LOW in the game, while the three test zones
  had a +0.15 m bias and nothing to move: a one-sided shift smells of a measurement bias, so they are kept in
  verifica/street/roofs_measured.json and not applied (dati/street_roofs.json empty) until sheets of them are checked.

- Wall tops as a saw (2-3 m teeth, 1-2 m V notches; Magliaso-Pura hairpin at 645,-1005 in michi's video, 2026-10-22):
  walls.wall_geometry looked the photo caps (dati/wall_caps.json, measured every 0.5 m on the outlines of their day)
  up by the exact cm key of each vertex. The outlines are now segmented every 1 m and redrawn, so only one vertex
  in two to six matched, and the top jumped between the cap and the LiDAR crest from one vertex to the next. There
  the survey draws one wall as 2-4 lines 0.2-0.5 m apart and the caps disagree (kerb on the road line, 2.5 m on the
  lines behind, bank 4 m higher): taking the nearest cap only moved the teeth. walls.caps_at takes the highest cap
  within the wall's thickness. Never look up per-vertex data by rounded coordinates when the vertices can change.
  Found by a column check on the released zip (top of each xy column vs its mesh neighbours, ±0.6 m).
- The caps_at fix above did NOT reach the Cantonale: there (24 of 58 points with saw tops in the v3.1 screenshots,
  2026-10-25) the walls are the ROADSIDE walls (rwalls_*, walls.build_roadside from dati/roadside_walls.json), not the
  survey walls. roadside_walls.py smooths a run's height over 8 m but takes its foot station by station (where the DTM
  scan finds the steep rise, 0.25 m steps): the foot jumped 0.3 m every 0.5 m, up to 1.5 m, and the top (foot +
  height) with it. walls.roadside_runs smooths foot and plan line, joins runs < RUN_JOIN apart and drops runs under
  RUN_MIN (the 4-7 m stubs). Before fixing a wall, find WHICH builder made it (shape name: rwalls_ / walls_).
  The survey walls took each top rule per vertex (caps or none, near the road or not, paving or ground under a flush
  top): walls.ring_smooth now smooths the final top along the outline (2 m median + 1 m mean); stubs under CUT_MIN_LEN
  left by the drive-free cut are dropped. Neither builder can run in the cloud (no WORK data): both were checked by
  emulation on the released level (build_roadside with the road mesh as road surface reproduced the released rwalls to
  the mm; ring_smooth applied to the top rings of the released DAEs) and render3d before/after.
- render3d draws grey terrain rising in front of the roadside walls of the Cantonale that the game does not show
  (seen in every view of them, before and after): do not read it as a wall fault.

## Buildings closer to the real ones (edifici_veri.py, v3.1)

- The built shapes shift their uvs by whole tiles (bng.write_dae: `T - floor(T.mean)` when the mean is over 2): the
  openings' uvs are not in 0..1, and looking them up in the atlas found no module at all (6,352 of 6,352 triangles).
  Take the fraction, and give the whole-tile shift back when writing new uvs.
- Cameras placed by rule in front of a facade (in front of its middle, 20 m out, eye height) ended inside other houses,
  roofs and walls in half the views. Put the game camera at the photo's own position and heading (the credits of the
  pack): the views compare with the photos (what michi asked) and are on the road.
- The houses a photo shows are often not the site's own: the yellow corner house of Agno (e03) and the red house of Pura
  (e18) were the next block, and the first round toned the wrong houses (the one in the site red instead of white).
  Check each site's photo against its render before and after (look up the blocks near the camera), then fix the spec.
- `bng.LevelFiles` takes a level folder, not a zip: a patch of the released zip unpacks it, runs the step and puts
  back only the files newer than a marker (`zip -@`), which copies the other entries as they are.
- Wall tones are vertex colours = tone / mean(plaster texture), the same as buildings_mesh: light pinks come out
  greyish mauve in the renders; give pinks a little more saturation than the photo's sunlit wall.

## Races (time trials, races.py)

- Mission files go in `gameplay/missions/<level>/timeTrial/<id>/` beside `levels/`, not inside the level folder:
  a zip made from the level folder alone loses them (package.py adds them).
- The game's mission format was guessed at first (no game files in the cloud, beamng.com blocked): copy the keys of
  a vanilla 0.40 mission instead (Italy `timeTrial/002-Asphalt`, loose files in `<install>/gameplay/missions/`).
- Start positions: the game reads the quaternion as the inverse rotation of +Y onto the road, angle = 90 deg minus
  the bearing. v3.0.40 shipped bearing + 90 deg (turning -Y the usual way), checked only against Italy 002-Asphalt,
  whose start faces due east where both readings agree: in the game the car started across the road at Magliaso.
  Check an orientation convention on a vanilla example that faces north or south, not east or west.
- Plain shortest paths over the AI roads cut through village lanes: weight by drivability**4, and follow the
  measured cantonal road by name, including its split pieces `<name>_<n>` / `<name>_g<n>` (traffic thread).
- The cantonal AI road starts with a hook inside the Magliaso junction, and a start position on the start line
  spawns the car on it: trim turn-backs at the route ends and start the car 15 m before the line.

## Night lights

- The street lamps' lights were PointLights of 14 m radius under a head 8.4 m up, one lamp every 30 m: the road was lit
  only in a pool under each lamp (michi, 2026-10-21, "la strada non si vede"). Italy lights its road lamps with a
  SpotLight aimed down (rotationMatrix [1,0,0, 0,0,-1, 0,1,0]; s_lamp_post_street_single_01 1500 lm, range 30,
  inner/outer 100/140; highway 7500 lm from 12 m), brightness = lumen/5000, nightLight "1", isEnabled false.
  Read Italy's values from `content/levels/italy.zip` on the PC before guessing a light's numbers.
- Calibrating lights live in the game without a build: a GE extension in the user folder
  (`lua/ge/extensions/<name>.lua`), michi pastes one console line, it swaps the lights, takes one screenshot per variant
  (`require("screenshot").createScreenshotTracked`) into `screenshots/` and writes a report; read them through the
  approved user folder. In 0.40 `getObjectsByClass("PointLight")` returned nothing and `getField("nightLight")` did not
  match: list lights with `scenetree.findSubClassObjects("LightBase")` as core_environment does (two wasted rounds).
  A file-polling "run any Lua" hook in the game was refused by the permission check: keep the test fixed.
- In a night view from above, the big white cone was the player car's headlights, not a lamp: turn them off first.
- Spot lumen barely changed the picture (3000 vs 6000 alike); range and cone width did.
- fuel_stations.LIGHT (the canopy lights) is defined but never placed: the v3.0.40 zip has no light but the lamps'.

## Traffic and AI

- Splitter islands stood in the AI lanes (v3.1 visual check, spot 1102: a car set mid lane at the Magliaso
  roundabout exit stood on the island, where the traffic crashed): swissTLM3D draws most roundabout arms and many
  roads with a refuge as ONE line down the middle of the island, the AI road follows it and its two lanes (a quarter
  of the width either side) run along the kerbs or over the island. 85 lane lines crossed 45 of the 124 islands.
  islands.island_lanes (in the islands finish step, which knows the raised islands) splits such a road there into
  two one-way roads, one each side in the middle of the free carriageway, or moves it to the side with room.
  Measured on the released v3.1: 51 lane lines on 23 islands left (mostly the Agno junctions), network pieces and
  dead ends unchanged (34 / 647). Three things it took:
  - _ease must never move a road's end node (np.interp with the end both pinned at 0 and in the measured keys
    took the measured value): the first try cut 19 pieces off the network (pieces 34 -> 53, dead ends +76).
    Check ai_roads.graph_report before/after any change to AI road geometry.
  - two roads meeting end to end in the middle of a long median each converged on their common node: the lanes
    crossed the island in an X. Such ends (exactly two two-way roads, both with an island near) stay open and the
    pieces are joined at the midpoint of their ends.
  - races.route_line chains a named road by "<name>(_g?<n>)*": the pieces past an island are "<name>_i<n>"
    (the way on), "<name>_j<n>" (the other direction, not chained) and "<name>_i<n>_0" (after it); the regex
    now takes _i too. A new piece naming must be checked against every reader of the AI road names.

- Started a full build on GitHub Actions for one thread while the other v3.0.40 threads were still working;
  michi stopped it. In a combined round, build only once, when every thread is ready (traffic_build.yml is manual).
- Merging the whole scalini branch into the traffic branch pulled 490 fix_review dumps (~850k lines). Base a
  thread branch on the integration branch and bring over only your own files.
- The cloud container cannot reach data.geo.admin.ch and the other data hosts: run analyses that need the
  downloads on GitHub Actions (traffic_probe.yml), not locally.
- BeamNG 0.40 vehicle/ai.lua ignores the "yield" signal action (only stop/briefStop/alert are handled). At a
  junction without a signal the AI yields when it turns or when its road has a lower drivability than another
  road there, so give way is a short lower-drivability piece (markings_rules.give_way_drivability).
- DecalRoad `speedLimit` is in m/s; without it the AI guesses the speed from the width (too fast on narrow
  roads). signals.json `sequences` is an object `{}` as in Italy, not a list.
- With autoLanes the game gives a road one lane until 5.4 m wide, so two-way cars meet in the middle: set
  autoLanes false and one lane each way from 4.5 m (ai_roads.lanes).
- info.json country: the game only knows usa/germany/italy/france/japan; anything else weighs no country.
- Welding road ends by snapping to the nearest node made V-shaped zigzags: snap an end only onto the other
  road's end, otherwise insert a node on it (ai_roads.weld, NODE_SNAP 0.5 m).
- Village speed zone from building counts: 60 buildings within 100 m left Magliaso's roundabouts at 80 km/h;
  25 within 150 m matches the signs.
- Roundabout give-way points found on the OSM ways landed on the ring: move them onto the entry road's
  incoming lane (snap_ring_signals), or the game binds them to the ring.
- A workflow edited by a script got a mis-indented step and failed at once on GitHub (no jobs): check every
  edited workflow with `python3 -c "import yaml; yaml.safe_load(open(f))"` before pushing.

## Sounds

- Event names copied from an old forum list (BeamNG 0.2x: `Church_Bells_01`, `Jungle Rock>River Large 01`, Italy
  `Water QP04`...) do not exist in 0.40, and a whole feature (bells on the hour, birds/crickets by time of day with a
  mod Lua) was built on them and thrown away. Check the event list of the installed game (`dati/ambient_events.json`)
  before designing around a sound. 0.40 ambient events: `Ambient>Water>River/Waves/Waterfall`, `Roomtones>*`, `Wind>*`.
- Never rerun `ambient_sounds.py --scan` on 0.40: it finds no paths in the trie bank and would overwrite the
  hand-written `ambient_events.json` with an empty list.
- An FMOD event fixes its own range and looping (`isLooping`, `maxDistance` of the SFXEmitter do nothing with `track`);
  a 2D event (or a roomtone that may be one) placed as an emitter is heard everywhere at full volume. Turn such a
  sound on only after listening in the game (the "use" entry of `ambient_events.json`).
- The cloud container cannot reach documentation.beamng.com or the game files (proxy 403): get facts about the game
  from the PC (the integrator's RC session), not from guesses.

## Landmarks (churches, bell towers, cable car)

- The cloud container cannot reach swisstopo, Commons or Mapillary, and Actions artifacts and logs are blocked by
  the proxy: `.github/workflows/landmarks.yml` (bump its `# stamp:` line to rerun) commits a small dev pack to
  `beamng/verifica/monumenti/pack` and `landmarks_preview.py` renders before/after from it in about 4 min a site.
- Actions caches are per branch: the first run of a new branch downloads everything again (about 13 min).
- Contact sheets made of CC BY-SA photos must not go into git (they are derivatives, the repo is CC BY-NC):
  they are in .gitignore, only `sheets/credits.json` is kept.
- The survey often keeps a church's roof as a separate object without walls: query buildings by their boxes,
  and take the roofs over a footprint from those objects (`landmarks.roofs_of`), or towers come out roofless.
- Round towers are many narrow facets (none wide enough for a module): use `landmarks.round_faces`. A tower with a
  lantern on top: take the eaves of its widest faces, not the median of all.
- A facade polygon can be split by a slot of a few cm (a downpipe in the survey): close it before `fits`, or one
  side of a tower got no bell chamber.
- A sacred block of the survey can hold a whole village core (Bedigliora) and the register gives it to a house:
  `landmarks.split_tower` draws its tower anyway.
- Heights stored as uint16 cm wrap after 655 m: the cable car climbs 900 m (decimetres there, `dtm_unit`).
- `bng.write_dae` subtracts the origin itself; do not subtract it again in the geometry.
- `landmarks_preview.py --before` must also switch off `landmarks.USES`, or the "before" shows the new details.
- Force-pushing this branch or merging another thread's branch into it was blocked: hand the branch over and let
  the integrator merge it.

## Working with cat (the owner)

- Show the 3D renders and wait for cat's OK before running the GitHub Actions rebuild workflow. No PRs
  or merges without asking.
- Keep the README "Known limitations" up to date when one gets fixed.
- Reply in Italian, times in CEST, few subagents.
- v3.0.40 and later rounds: one thread integrates and builds; only it opens the release PR. Two other threads opened
  PRs (#80, #81) from branches that carried the whole integration branch to main and they had to be closed.
- Untested builds for michi go to the GitHub pre-release "nightly" (`nightly_build.yml`, started by changing
  `beamng/nightly/stamp.txt`), never the latest release; michi tests them on the main PC.
- Document every error and failed attempt in this file, under its topic (michi, 2026-10-20: "sempre").

## Ticino a blocchi (beamng/ticino, 2026-10-26)

- A second map in the same repo: level `ticino`, its own mod zip, never `levels/magliaso_pura` (michi: "devono convivere
  le due versioni"). Phase 1 cuts the released v3.1.1 into blocks (blocks.py) instead of building; on the PC all data
  goes on the 6 TB disk (pc_prepare.sh <disk>).
- The scene objects kept in the level (backdrop, landmarks) still pointed at /levels/magliaso_pura/ after the first cut:
  copy_level rewrote the files it copied but write_scene wrote the kept objects as read. Grep the cut level for the old
  level name after any change to blocks.py.
- A coroutine keeps the arguments of its FIRST resume: the yield function made in runJob read the first frame's start
  time forever, so every later call yielded at once and a window took 461 frames (7.7 s) instead of ~17. Read the frame
  start from a table the caller updates (job.t0).
- Writing the 12 MB window .ter in one f:write took ~40 ms (one frame): write it row by row with yields (writeParts).
  The PNG writer also never joins its 800 kB IDAT (CRC computed over the parts).
- `blocks.py --no-far` first deleted the far/ folder with the other outputs (a quick rerun lost the far tiles).
- Unknown until the game test: the terrain materials' *BaseTexSize unit. The pipeline writes metres (12288 = 8192 x 1.5),
  BeamNG.Earth measured samples in game; the window's maps assume samples (zone `base_size_unit`).
- BeamNG.Earth (github.com/TecnaGamer/BeamNG.Earth, MIT, cloned fine from the cloud) has in-game measurements of every
  engine limit the streaming needs (docs/research/2026-10-12-engine-limits-and-worldgen.md): read it before guessing.
- blocks.py hard-links the source level into the output and then wrote info.json over the linked file: the SOURCE
  v3.1.1 info.json got "Streaming test of the Ticino level:" once more per run (seen 4 times). Every write into the
  output goes through blocks.wopen (removes the path first). After a run, `find <src> -newer <zip>` must list nothing.
- michi tests the Ticino mod on the Windows PC DESKTOP-OUPOLOA (2026-10-26, "questo qua è un pc windows usa questo"),
  not on the Linux PC: no Python there, so ticino_test.yml cuts and packs on GitHub (draft release ticino-test) and
  tests/game/run_test.ps1 runs the test (autotest.lua, as the v3.0.40 runner did).
- First in-game look (2026-10-26, DESKTOP-OUPOLOA, 0.40.3): level ticino loads in 9 s, no missing material, streaming
  runs. Hitches: every tile change ended in be:reloadCollision and the physics rebuilt ALL static collision ("Loaded
  Static Collision" 0.3-1.5 s, 7.4 M triangles) once per 384 m; the window swap itself is 0.16-0.2 s. The first jump
  made all ~1,000 far tiles at once (7.8 s: the game converts every new DAE). Now far tiles come a few a frame, a
  deleted collider no longer forces a rebuild, and ticino_stream.setCollision(radius, groupsOff) switches groups (the
  skin is 26 of the 46 M collidable triangles) for measuring. michi drove east past Agno, out of the built zone (the
  airport runway is bare terrain there in v3.1.1 too): "no objects" at the zone edge is not a streaming bug.
- What a collision rebuild costs (console, standing still in ticino, 2026-10-26): the whole static collision 7.12 M
  triangles 3.40 s; without the Forest 1.12 M and STILL 3.40 s (274k tree instances share ~30 meshes: free); only
  the car's tile 156 k, 0.54 s; no streamed object at all 4.8 k, 0.002 s (the terrain costs nothing). The time is
  "Loaded Static Collision" after "Physics collision reloaded" (0.05-0.12 s): about 3 us per unique triangle, skin
  the worst (57 % of the collidable triangles, most of the time). Do not delete the Forest object to test: the game
  log stopped being written after it (the game went on).
- Quick travel into a zone never seen: about 40 s, nearly all "Importing COLLADA" of 551 shapes (the game converts
  each .dae once, cached afterwards) + 4 s of collision.
- Collision cells (collision.py, 2026-10-26): fast_simplification (quadric) on a road mesh left holes (1.2 % of the
  surface samples at 50 % reduction, 4 % at 70 %) and moved edges by up to 0.5 m (the skirts): roads, sidewalks and
  railway stay exact; only the skin (to 7 %), houses, walls and props are simplified. A sim run whose clock is CPU
  time (tests/sim_stream.lua) never let a "150 ms after the swap" wait expire: count such waits in dtReal.
  Collision .cdae with real normals and tangents were 1.1 GB (563 MB zipped); with constant normals 228 MB zipped.
- Laptop run 1 (2026-10-26, DESKTOP-EKDTIGL, 0.40.1, iGPU 512 MB): no crash, no Out of VRAM, load 48 s, peak 9.5 GB
  private, ~10 fps. The car fell through the road during autotest's own reload test (cells radius -1 for 12 s with
  the physics running: no road collision under it) into a yard 1.6 m lower and was stuck for the whole drive. The test
  now pauses the physics and puts the car back. map.findClosestRoad(vec3(x, y, 1000)) found nothing with 20,810 nodes
  in the graph: query near the ground (and the test falls back to the nearest node by hand, noting it).
  colPiece's ffi.cast of the Lua string raised "arithmetic on a string value" for one cell (10 times, the pos not
  advanced): the piece is now copied into an ffi buffer, and any failure turns ffi off for the session.
- Laptop run 2 (2026-10-26): that fix made it worse: `ffi.new('uint16_t[?]')` is an array, and `u + 3 * nv` on it
  raises "bad argument #1 to '__add' (invalid C type)" for EVERY piece (colTris 0, 2,126 failures, no cell had any
  collision; the car fell through the tunnel floor). The fallback never ran: the error came after the pcall'd copy.
  Index the array (u[3 * nv + k]); a failed piece now drops the rest of its cell (the read position is lost). Run any
  decoder change against a real cell file in luajit with stubs before a game test (the ffi and byte paths agree).
  The AI drove this time (2.3 km in 14 min, 9 stops, "moved 30 m on" worked). Every jump put the car at z 0.5: the
  AI map's nodes far from the start had z 0 (the AI DecalRoads clip to the terrain, which exists only in the
  streamed window; the json nodes have their heights). The test now takes the ground under the node and counts the
  z < 1 nodes before and after a map.reset() at each jump; the 3,124 core_trafficSignals "Map node could not be set"
  likely have the same cause. Also logged: material cbv array exhausted (8192 slots) at 113 s, a 16x448 bollard
  texture that is not a power of two (TextureCooker refuses it).
- Laptop run 3 (2026-10-26): collision cells work (colFailed 0, 1.7 M triangles made), no jump fell, the car stands
  on the tunnel floor. map.reset() after the window came gave every AI node within 300 m its height (0 of 59-281 left
  at z < 1), while 14-19 k of the 20,810 stayed at 0: stream.lua now reads the AI map again MAP_RESET_FRAMES after
  every window swap (perf row "mapreset"). A collision cell dropped half made left its pieces in the scene and the
  remade cell registered the same names (56 SimNameDictionary::insert warnings); colTris was a "made" counter, now live.
  createScreenshot2 takes the shot a few frames later: with the camera moved on at once, every tunnel shot showed the
  NEXT pose (and the last two were alike). Wait 2 s after each shot before moving the camera.
- Laptop run 4: that map.reset() froze the game 1.9-2.5 s at EVERY window move (perf rows "mapreset"): never call it
  on the fly. map.lua (0.40, loadJsonDecalMap) takes a DecalRoad's subdivided edges (clipped to the terrain) when
  useSubdivisions is on and edgeCount > 2, else its control points with their own z: blocks.py now writes the ticino
  AI roads with useSubdivisions false and MAP_RESET_FRAMES is nil. The AI left the road twice at Pura (250-290,-890,
  runs 3 and 4, into the wood against a tree): the same place as the known lamp/4 m AI drop of the piano video
  (Known issues), a map fault, not streaming.
- Laptop run 5: useSubdivisions false CRASHED the level load. map.lua (0.40.1) L459 edgeCompare compares `a.lanes <
  b.lanes`; the node reduction (RDP, ~L1985) builds a new edge with NO lanes when it removes a middle node between two
  nodes already linked directly, and compares it with that edge: "attempt to compare nil with string" when posMin/max,
  radii, drivability, oneWay and speedLimit are all equal (two AI roads joining the same two nodes, one with a node in
  between). Control points coincide exactly where subdivided edges differed by mm. The game then reloaded the level by
  itself and crashed in C++ (c0000005). In the ticino roads the ties were the two one-way halves of a road round a
  splitter island (X and X_j1, islands.island_lanes). beamng/ticino/aimap_check.py emulates map.lua's passes from
  the code read on the laptop and blocks.py stops if it finds a crashing compare (resolveT/XJunctions and
  mergeNodesToLines are not emulated).
- Laptop run 6: the first fix, a speed limit of its own per road, crashed the same way: 0.40.1 does NOT read a
  DecalRoad's `speedLimit` from items.level.json (an in-game probe read r.speedLimit nil and getField '' on all 3,451
  roads; vanilla Utah writes none), so createSpeedLimits gave both halves the same value. The emulation had read the
  json value, so it said 0. Emulate only what the game is shown to read. Now blocks.ai_roads gives every road a node
  width of its own (+2e-6 m per road, float32 keeps it), which ends the compare at the radii: 11 crashing compares in
  3 orders before, 0 in 8 after, with the speed emulated as one auto value and the nodes as float32. Not drivability:
  a lower drivability makes the AI give way at the joint. (The probe also read useSubdivisions as nil, yet runs 1-4
  without the key had subdivided z 0 nodes and no crash, and 5-6 with false crashed: the key is read.)
- Laptop run 7: the width offsets loaded (47.9 s, no crash) but the control-point graph did not help: far nodes kept
  z 0 all the same (the control points' z is also clipped where no terrain is loaded) and the AI drove 762 m against
  2,383 m in run 2 (more stops, it hung at joints the subdivided graph had smooth). Reverted: the ticino AI roads are
  written as the source has them (subdivided, no width offsets, aimap_check.py kept as a tool), and stream.lua calls
  map.reset() once at each jump, while the game is paused for the reload (MAP_RESET_ON_JUMP), never on the fly.
  Between jumps the far nodes stay at z 0 (only the window's are right). Also seen: 4,857 core_trafficSignals errors,
  hitches up to 260 ms at jumps. The S tunnel portal showed the lake through two small gaps at the jamb feet: an
  apron (tunnels.APRON, 1.6 m of ballast/asphalt 3 cm under the floor) now runs out in front of each face.
- Laptop run 8: loads (48.7 s), no crash, jumps fine, the reset at a jump reads every node near it (1.8-2.5 s inside
  the paused jump), the jamb gaps are closed. But the apron stood out past the S headwall as a plate 1-1.5 m over the
  lake-side slope: its open edges now go FOOT under the lowest ground beside them. The AI drove only 873 m: in "span"
  mode it turned into a 3.4 m village lane north of the start (630-690,-790..-850), spun its wheels there and looped
  with the "moved 30 m on" helper, never leaving the first window. Not a streaming fault: the cell collision there
  matched the exact meshes on every road cell (0.25 m raster, 0 cells over 3 cm; only the skin moved, up to 0.67 m,
  off the road), the lane is smooth at 14 %. Which way span mode turns is luck: the drive now follows the scripted
  route (16.8 km, Magliaso-Pura-Ponte Tresa-Caslano-Agno) first, then the AI. The autotest's own map.reset at a jump
  doubled stream.lua's (6,553 trafficSignals errors): removed.
- Laptop run 9: load, jumps, cells and the tunnel all fine (the apron skirt closes the S portal; tunnel done). The
  scripted route flipped the car after 155 m: it started inside the Magliaso roundabout, hung there 26 s, then
  scriptai raced the late timeline at 14 m/s (it keeps to the times, not to a speed) and at the bend at 684,-1040 the
  car left the cantonale and fell 2 m on its roof into the lane below. make_route.py now starts on the cantonale,
  weights the path by drivability ** 4, drives at most 40 km/h and slower in bends (A_LAT). The AI drive after it went
  1.16 km west through Pura with 6 short stops. The jump check 1 s after stream.lua's reset log still saw the old
  heights; 5 s later all were right (the reset lands a few frames after its log line).
- Laptop run 10: the slower route (A_LAT, 40 km/h) flipped at the same place, 684,-1040, at 3-7 m/s: not speed. The AI
  road strada_cantonale_i1_0 there lies on the EAST EDGE of the cantonale, and its 7.7-9 m width covers the lane
  tlm_1052 1.2-1.6 m lower beside it: every car on that AI line (scriptai, span AI) goes over the edge. Making the route
  graph directed for one-way roads gave a 33.8 km detour (reverted). New finish step ai_lanes (pipeline/ai_lanes.py, in
  ticino_test.yml after tunnels): every AI node walks the road surfaces across its width, and a step over 0.5 m inside
  it moves the node away and narrows the width (lane 0.3 m from the drop, never under 3 m), spread over 2 nodes each
  side, faded out 6 m from the ends. On v3.1.1: 9 of 3,451 roads, 48 nodes, at most 3.2 m (the cantonale 2.9 m west).
  route.json regenerated from the fixed roads. Not run in the main build yet (only on the Ticino test level).
- Laptop run 11: the ai_lanes fix held (the car stayed on the cantonale at 684,-1040), 2.3 km of route, 6 window moves,
  no fall. Two stops: (1) at 59,-748 the car hit a street lamp standing 2.2 m inside the cantonale's AI width and stood
  40 s: 17 of the 2,108 lamps stood inside an AI width (also the known one at Pura, 287,-892). ai_lanes.lamps_clear moves
  those out to the half width + 0.6 m with their lights, or removes them where the ground there is 0.8 m off (2). A first
  version moved every lamp closer than half width + 0.6 (1,447): the lamps stand 0.3-0.5 m beyond the edge on purpose;
  only lamps INSIDE the width move. (2) the route ran into dead ends and back over the same nodes ((-240,50) and
  (-250,-1000) were places on side roads), and scriptai cannot turn round: it stopped at -259,61. make_route.py now
  makes roads already driven cost 20x, cuts spurs under 120 m and reports longer ones; new places, 19.6 km, no
  turn-round (cos < -0.8) left. Unwinding every A-B-A with no length limit collapsed the route to 7.7 km (whole legs).
- Collision cells as ProceduralMesh (EarthNG's way, michi: "basta che non cambia la grafica"): decoding a piece in Lua
  is the cost, not the file: a 2,500-triangle piece took 7-10 ms in luajit with s:byte, so a frame went over budget.
  ffi.cast of the string to uint16_t* and pieces of 1,200 triangles keep a piece under ~5 ms. The cells hold
  triangles by their centre, so a piece reaches up to ~70 m outside its cell (long road triangles): a range check of
  a cell file must allow that (XY_OFF_CM). Not known until the game test: whether setRenderEnabled exists on
  ProceduralMesh in 0.40 (pcall; the materials are alpha 0 anyway) and whether the winding (clockwise) lets the car
  stand on it.
- Zone builds (zone_build.yml, MAGLIASO_ZONE, 2026-10-27): download_worldcover failed at once on the probe zone ti_1_0
  (Lugano): the window of tile N45E006 rounded to start one cell west of the map's box, c0 = -1, and `out[r0:, -1:...]`
  is an empty slice ("boolean index did not match ... size of axis is 0"). The Malcantone box never touched a tile
  edge. Clamp a pasted window's offsets, never slice with a start that may be negative.
- Next on ti_1_0: network_surface.cantonale_hold -> roadheight.build crashed (NaN bounds): the corridor surfaces are
  cut along the Malcantone Street View route (poses.json main_run), which no other zone touches. With no polygons
  roadheight now saves an empty Surface (distance inf, height nan). Expect more such Malcantone-only data (poses,
  road_profile, photo markings, wall caps): a zone has none of it in reach and every reader must take "nothing".
  The Actions cache saves only when the job succeeds: the zone workflow saves the downloads right after them.
- More Malcantone-only assumptions found on ti_1_0 (2026-10-27), all fixed so the Malcantone build is unchanged:
  stage_roads with no corridor polygons (bb of an empty list); vanilla/carryover read the reference zip under
  levels/<LEVEL_NAME> (the zip's level is always magliaso_pura) and carryover took over the v1.1 route paint and props
  (now none in a zone); the Monte Lema cable car/summit outside the zone's terrain; guardrails_final.json and the
  photo rails (NaN feet outside the zone's DTM: savgol "array must not contain infs or NaNs"): area.in_zone drops
  photo data outside a zone; spawns from poses.json (zone_route picks main roads near the core); races skipped.
- A dense zone is slow on one process: ti_1_0 stages roads 81 min, walls 21, buildings 36, vegetation 20, canopy 28,
  finishing optimize 11, unpaved 17, markings 13, road_wear 12 (cloud container). wintryserver (6 cores) ran the
  stages in 73 min. GitHub stops a job at 6 h: zone_build.yml runs the stages and the finishing steps as two jobs.
  NET_WORKERS forks the network tiles (results added in tile order, same level). MAGLIASO_CHECKPOINT=1 pickles
  (scene, ctx) after every stage (700 MB on ti_1_0) and `build_level.py --reuse-roads --resume` goes on after a crash.
- The cloud container's disk (about 30 GB usable) fills with a zone: the raw swisstopo tiles (data/swissalti3d_05,
  dsm_05, buildings3d) are not read after build_rasters/extract_buildings and can go during a build.
- skimage was missing in the cloud container (vegetation's watershed): pip install scikit-image before a local build.
- wintryserver (michi's Ubuntu server, 6 cores, 14 GB, /mnt/disk8tb): RC sessions work only inside /mnt/disk8tb/ticino.
  Claude Code's auto-mode check refused to run the cloned repo's Python ("Code from External") until michi wrote the
  exact permission in the thread; sudo asks a password (osmium-tool unpacked from the .deb into /mnt/disk8tb/ticino).
  `claude remote-control` in a terminal registers the folder as a device; an RC started inside a running session did not.
- Traffic lights (markings_rules, 2026-10-27): OSM highway=traffic_signals on an arm makes the junction signalled
  (3+ arms): every way in gets a stop line, an instance of a two-phase sequence (axes) and the stock boom
  /art/shapes/objects/s_trafficlight_boom_sn.dae on its kerb side, local +x to the kerb (as BeamNG.Earth places it,
  tested by them in 0.40.3; not yet seen in our level). Controllers and instances share one id count.
- signs_net had `levels/magliaso_pura` written in (KeyError in a zone after 6 min of the signs step): grep the pipeline for
  the old level name, every reader must use LEVEL_NAME.
- wintryserver OOM (2026-10-27, ti_1_0): the finishing step unpaved peaked at 12.95 GB RSS + 2 workers of 1.7 GB, and
  immich/java hold ~3 GB with 3 GB swap: the kernel killed build_level (rc 137, no traceback). PATCH_WORKERS=1 passed
  (633 s). Run the zone finishing steps there with PATCH_WORKERS=1.
  Then paved_edges went OOM even with PATCH_WORKERS=1 (12.36 GB peak; Minecraft with -Xmx8G and immich run there too):
  unpaved_step built the two TriSurfaces (7.9 M faces, ~1.5 GB each) in main although Python 3.14 starts the pool
  workers from a forkserver, which build their own. Main builds them only under "fork" now (same output).
- lamps_step read props/street_lights, which only props.py makes from the panorama lamps of the Malcantone: KeyError in a
  zone. It now makes the group (and its SimGroup line in props) when it is missing.
  The first version of that fix crashed in pits(), which reads ALL in main too (the cloud container's Python 3.13 forks,
  so the local run never took that path): ALL is built from al.npy there when it is missing. Test a change that depends
  on the start method under "forkserver" too (multiprocessing.set_start_method).
- signs_more planned 0 signs in a zone (then crashed on an empty DAE): its in_ch() needs the Swiss commune outlines
  (dati/osm_communes.json.gz), which download_osm.zone_main leaves empty. In a zone without them everything counts as
  Swiss for now; the zone extract should get the communes from the pbf before the border zones are built.
- fuel_stations.new_canopy (a station with no survey canopy, never reached in the Malcantone) used the 2D np.cross that
  numpy 2 refuses: crashed in the zone. A code path the Malcantone never took is untested: expect more of these.
- parking.Ground.terrain converted the whole 8192x8192 terrain to float64 at every call (three calls a parking spot):
  more than 20 min of parking on the dense zone ti_1_0. It now converts only the four samples it reads (same numbers).
- roof_posts took 36 min on ti_1_0 (union_all of the buffered roof faces of each shape); not changed yet.
- The finishing steps ran one after the other in ONE process and the memory they left added up (wintryserver: 7-10 GB
  at the start of each step after two hours, OOM at road_seams with 13.1 GB). build_level.finish now runs each step in
  a forked child (MAGLIASO_STEP_FORK=0 turns it off; no fork on Windows): the steps share nothing but the files.
- tunnels.holes tested every terrain square of a tube's bounding box (16 KD queries each): the Lugano zone has 32 live
  tunnels, some kilometres long and reaching out of the zone (a box of 2,650 x 3,410 squares), and the step ran over
  40 min. Only the squares within a band round the tube's line are tested now.
- First full zone ti_1_0 on wintryserver (2026-10-27): zip 1.88 GB (5,020 files, level 10.6 GB unpacked), stages 1 h 46
  min, finishing steps about 4 h with the restarts (tunnels 42 min with the old holes(), paved_edges 32, roof_posts 24,
  steep_skin 19), package 7 min. Server setup: python3-venv missing (venv --without-pip + get-pip.py), osmium-tool
  unpacked from the .deb (no sudo), long runs under setsid/nohup. Peak RAM after the fixes ~10 GB; it shares 15 GB
  with Minecraft (-Xmx8G) and immich. No gh there: the zip stays in /mnt/disk8tb/ticino/bm/dist.
- download_osm.pbf_communes checked on the server: 25 municipalities over the Malcantone-Lugano box in 19 s, 2 GB.
- GEOS constrained_delaunay_triangles raised "Unable to find a convex corner" on a wall polygon of ti_m1_7 (stage walls):
  config.py wraps it for every caller (retry on the cleaned polygon, else no triangles and a log line).
- zone_build.yml: zone_retry_stamp.txt builds only zone_retry.txt (failed zones after a fix) in its own concurrency
  group, so it does not cancel the run of the whole list (a push of zone_stamp.txt would: cancel-in-progress).
  A retry commit must have "[zone retry]" in its message: the first test (head_commit.modified/added holding the
  stamp's name) came out false in the workflow and the retry started all 71 zones (cancelled at once). Check the
  setup job's zone list of a new run before leaving it.
- GEOS union_all stopped on "TopologyException: found non-noded intersection" (zone ti_1_3, clearance._tile in the
  vegetation stage, 22 min in). config.py wraps shapely.union_all/unary_union like the CDT: on a GEOSException it
  retries snapped to a 1 mm, then 1 cm grid (shapely.ops.unary_union goes through shapely.union_all, so it is covered).
  Then ti_1_6 (after its CDT fix) stopped in landmarks.band_all on an intersection ("Ring edge missing"): the wrapper
  (config._safe_overlay) now covers shapely.intersection/difference/union/symmetric_difference too (the Geometry
  methods and operators call them), with make_valid inputs as the last try.
  ti_1_6 failed again: make_valid turned a facade polygon into a polygon + line collection and the retry stopped on
  "Overlay input is mixed-dimension". The last tries now clean polygonal inputs with buffer(0) (stays a polygon).
- canopy.run crashed in zone ti_0_m1 (int(NaN) in TileRasters.cell): TileRasters.intrusion returned a NaN direction,
  so _fix moved the tree to NaN (0 * NaN is NaN even at the step d = 0). Some drivable raster cell had a NaN height:
  a mesh of that zone has NaN vertices somewhere (not found yet: look at the zone's road/yard DAEs when the zip is
  there). intrusion now treats a NaN cell as no intrusion, _fix falls back to (1, 0), items with no ground are dropped.
- zone_route (spawns) took the nearest 6-10 m Strasse: zone ti_0_3 (mountains) has none and argmin of an empty list
  crashed. It falls back to any Strasse, then any segment. A new retry push REPLACES a retry still pending (one pending
  run per concurrency group): put the pending run's zones into the new list too.
- Zone ti_m1_7 crashed in buildings_mesh (None.strip on b['uuid']): some swissBUILDINGS3D features of the Lugano sheets
  have no UUID, and extract_buildings merged all of them into ONE building keyed None. They now get a key per EGID,
  else per feature (the Malcantone has none: unchanged).
- props_osm.build wrote its DAE even with no furniture at all (zone ti_2_m1): bng.write_dae fails on an empty
  MeshBuilder ("need at least one array to concatenate"). Every writer of a merged shape must skip an empty one.
- Zone ti_m4_3 has no road segment at all: zone_route now puts the three spawns on the ground of the core (facing
  east), and the village spawns are skipped when no main road exists (a cKDTree of no points).
- Zone ti_0_6's finish job stopped in unpaved with "The runner has received a shutdown signal" (exit 143, no
  traceback): the GitHub runner's 16 GB ran out (unpaved peaked ~13 GB on wintryserver too). zone_build.yml now adds
  a 16 GB swap file in /mnt to both jobs and runs the finishing steps with PATCH_WORKERS=1. A "shutdown signal" with
  no Python error in a zone job is memory, not a cancelled run.
- Zone ti_1_3's finish crashed in poles.roadside_step (network_mesh.terrain_top: IndexError, row -13659): a zone's AI
  roads reach far out of its terrain. terrain_top now clamps points to the terrain's edge (inside it nothing changes).
  Zones ti_m1_2 and ti_m2_2 (same row) both crashed at row -8539, ti_1_3 at -13659: the SAME absolute point south of
  every zone: ai_roads.build added the Malcantone's Street View route (strada_cantonale, road_profile.npz) to every
  zone's AI roads. A zone now leaves it out unless it lies wholly in the zone's terrain (the network lines take it).
  Zones built before this fix (main run 40595329416) still carry it: drop strada_cantonale when merging them. The same log showed wall_feet lowered_m_max 354 m: some wall vertex was far off in that zone; not looked at yet.
- Zone ti_0_7's finish crashed in markings_rules (KeyError roads/markings/items.level.json): the group is made only
  by the v1.1 route paint (carryover, Malcantone). markings_rules makes it (and its SimGroup line in roads) when missing.
- Zone ti_1_6 has no railway: the finish step catenary read railway/items.level.json and stopped (KeyError). It now
  skips a level without a railway group. Other zones without a line will reach the same steps: expect more of these.
- Zone ti_0_6's finish was shut down in unpaved again WITH the 16 GB swap (32 GB in all, 6 min into the blocks): one
  block asks TriSurface.height for 1.7 M points, and its work arrays hold one entry per point and face of the point's
  2 m cell (a face is listed in every cell of its bounding box: long faces of a dense zone fill many). height now
  answers more than HEIGHT_CHUNK (200k) points in pieces (same result, checked on random faces); the finish step
  prints [mem] lines every minute so the next such stop shows what grew. With it ti_0_6 passed unpaved (peak 11.1 GB RSS, no swap).
- Zone ti_0_1 stopped in house_details (KeyError 'gbaup'): a GWR record of a zone may lack the period of construction
  (download_gwr counts records with gbauj or gbaup: both are optional). house_details reads gkat, egid, gbaup with .get.
- Every zone of the full run 40614904081 failed in its finishing steps (gbaup, catenary, memory) after 2 h of good
  stages. zone_build.yml now takes "[zone finish <run id>]" in the commit message (with a zone_stamp.txt change): no
  stages, the finish jobs download that run's root-<zone> artifacts (run-id + github-token, permission actions: read;
  kept 2 days) and run the finishing steps of the new commit. Use it whenever a fix touches only finishing steps.
- Zones ti_m1_2 and ti_0_2 (with a railway) stopped in catenary: a railway shape had an mp_sleeper part with no top
  face, and vid.max() of the empty part raised. sleepers() skips such parts, catenary skips a level with no sleepers.
  A finish run with "[zone finish <run>] [zone retry]" takes zone_retry.txt and has a group of its own (no waiting).
- Zone ti_1_1 has no lake: water.lake_step stopped on "no WaterBlock LagoDiLugano" (SystemExit). It now skips the level.
- Zone ti_m2_3: 3 tunnel lines, none with a live portal, and cut_meshes concatenated no tubes. tunnels_step now stops
  right after the portal check when no tube is live.
- Zone ti_0_3 (mountains) has no traffic island: sidewalks read roads/islands/items.level.json unguarded (KeyError).
  It now reads the group only when it is there (roundabouts and direction_signs already did).
- Zone ti_m3_3 has no sign at all: signs_net wrote props_signs.dae from an empty MeshBuilder (concatenate of nothing).
  With no sign it now writes no shape and no object (mb.empty() is a method: `if not mb.empty:` is always False).
- Zone ti_0_m2: signs_more planned signs but placed none (all outside the map or left out) and wrote an empty DAE.
  It now stops before writing when nothing was placed (it already stopped with nothing planned).
- Zone ti_2_7 has no carriageway face at all (paths only): markings_rules.paint_level concatenated nothing. The step now
  paints nothing there and only makes the empty roads/markings group the later steps read. Other steps that read the
  carriageway (road_wear, stop_paint, parking) may meet the same zone next.
- Zone ti_2_0 has no prop at all, so no MissionGroup/props group: poles.roadside_step read props/items.level.json and
  stopped (KeyError), and lamps had written its group file under a props group that did not exist. build_level.finish
  now makes an empty props group (props_group) before the steps when a level has none.
- ti_2_7 then stopped in road_wear (no asphalt face: concatenate of nothing). road_wear now writes only its overlay
  materials and textures there (yard_wear needs them), and the other readers of the carriageway (yard_wear, islands,
  direction_signs, bus_shelters, stop_paint) take markings_net.tops_of, an empty (0, 3, 3) array when nothing is there.
- Zone ti_0_m1 (the one with NaN mesh heights) raised no terrain vertex at all in unpaved and the report's percentile of
  the empty lift crashed; then the job hung until GitHub's 6 h limit: the [mem] loop started with & kept running after the
  failed step. The loop is now killed by a trap on EXIT. That NOTHING was raised there likely comes from the NaN vertices
  (optimize warned "invalid value encountered in cast" in bng.py): still to be found in that zone's road meshes.
- ti_2_7 then stopped in road_seams (sags: no AI road sample over a carriageway, an empty cKDTree index). sags returns
  nothing there and road_seams_step stops after the sags when the level has no carriageway face.
- ti_0_m1 then stopped in house_extras (int(NaN): the windows of a building with NaN corners). optimize, the first
  finish step, now drops every triangle with a NaN corner while it merges the shapes (no change where there is none),
  so the later steps read clean meshes; house_extras also skips NaN pieces. Where the NaN come from is still unknown.
- Of the 46 zones without GWR buildings, those wholly outside Switzerland (ti_3_m1, Italy) stop at once in
  build_rasters (FileNotFoundError swissalti3d_05/*.tif: no swissALTI3D tile there). They are not Ticino: leave them out.
- Zone ti_m3_1 (mostly Italy) has no road at all: ai_roads.graph_report concatenated nothing. ai_roads.build now leaves
  an empty AIRoads group there (the many readers of AIRoads/items.level.json find an empty file).
- Joining zones into one streaming level (beamng/ticino/region.py, 2026-10-28): every zone is built with its own Z0/MAXH,
  terrain material names (GUIDs) and TextureSet: requantize the heights to one global range, match the layers by
  internalName and rename the TextureSet, or the window's TerrainBlock keeps the first zone's set. The 1152 m merged
  shapes straddle the core edges: clip them per triangle (by centre) to each zone's core, never keep them by position
  (two zones would both draw their overlap). A region's forest (millions of items) cannot be one Forest: forest.lua
  streams one small Forest per tile from a pool (BeamNG.Earth's way). The first forest.lua remade whole tiles at every
  tile change: a pass now compares each row with what is made and adds or removes only the difference.
- Welding the region's roads (region_net.py, 2026-10-28): the zones build a road crossing a core edge with the SAME
  nodes (122 of 123 crossings of ti_0_m1/ti_1_m1/ti_0_0/ti_1_0 within 5 cm), so region.py's first cut ("one node
  beyond the edge") was already linked in the AI graph (pieces 90 and dead ends 2,298 before, 90 / 2,296 after): what it
  really did wrong was doubling the last segment of every crossing road (122 doubled segments, two parallel edges for
  the traffic). Roads are now cut exactly on the edge and the two cut ends welded into one point; every cut end left
  unwelded (58) lies on the region's outer border. Check a merge with graph_report AND a count of doubled segments.
- Do not drop strada_cantonale from every zone: in ti_0_m1 and ti_0_0 the Street View route lies wholly in the zone's
  terrain and is the ONLY AI road of the Magliaso-Pura cantonale (swissTLM3D lines along it covered 0-13 %: the route
  replaced them, ai_roads main_zone). region_net.stale_cantonale drops it only from a zone where it reaches beyond the
  zone's terrain (the zones built before the fix of ai_roads.build).
- signals.json of a zone: `sequences` is a LIST, ids of instances and controllers come from one counter, the stop and
  give-way controllers (ids 1, 2, isSimple) are in every zone. A light group (sequence) goes to the zone whose core holds
  the middle of its lights: by single position the lights of one junction on a core edge would split between zones.
- A release zip of the draft release can be read in parts with HTTP range requests (zipfile over a seekable reader on
  the asset's redirect URL): the scene files of four 1.5-2 GB zone zips came down in seconds, no full download.
- ti_0_m1 then stopped in sidewalks (merged_pieces_raised: max of an empty array): a merged prop DAE has NaN vertices,
  so `W <= W.min() + 0.05` found no feet. The piece is skipped. Props DAEs carry the NaN too (not only roads/buildings).
- Sparse zones (ti_m1_m1: one road shape, no unpaved road) crash in one finishing step after another on empty data
  (network_mesh.top_faces concatenated nothing). In a zone, build_level.finish now leaves out a step whose child ends on
  "need at least one array to concatenate" / "zero-size array to reduction operation" or a KeyError of a group's
  items.level.json the stages never made (ti_m3_1: no buildings group) (nothing_there, exit code 3) and
  goes on; the Malcantone build still stops on them. A step that wrote some files before such an error keeps them.
- Zones ti_m4_2, ti_m5_3, ti_m5_4 have Swiss terrain but no swissTLM3D road at all (network.nodes_of: max of nothing):
  mostly Italy, left out for now. About 25 zones of the 46 without buildings stop in build_rasters (no swissALTI3D).
- Zone ti_3_8 has no building of the Federal Register: markings_rules built a cKDTree of np.array([]) (shape (0,), not
  (0, 2)) and stopped. Every GWR point array (markings_rules, lamps, poles, signs_more, street_life) is now
  reshape(-1, 2): an empty KD tree answers inf / 0 counts.
- The first region with Magliaso (run 40721234941) stopped at once: ti_0_m1's TerrainBlock had position z and maxHeight
  NaN. One NaN height anywhere made terrain z0 = floor(H.min()) NaN and every height of the .ter garbage (the build log
  said "terrain z0 nan maxHeight nan" and nobody read it; the NaN mesh vertices of that zone likely have the same root).
  build_terrain now fills NaN heights from the nearest finite ones and logs where they were (nan_report), and each
  terrain post step (walls, lake, rivers, railway) prints how many NaN it left. Grep a zone's build log for "nan" in
  the terrain line before joining it.
  The rebuild (run 40723783273) showed the source: "terrain post 0 left 909 NaN heights", i.e. walls.carve_terrain /
  adjust_terrain_roadside (post 0) writes NaN at 909 vertices of ti_0_m1; not looked into yet (z0 240, maxHeight 874).

## All of Ticino in one level (region_plan / region_slice / region_base, 2026-10-29)

- region.py loaded every zone at once: 87 zone zips are 65.6 GB (not 120), too much for one runner anyway. Now one
  GitHub job per zone (ticino_all.yml, region_slice.py) writes the zone's blocks, far ground, clipped shapes, tiles,
  forest and collision cells, and one small job (region_base.py) the scene, roads, signals, materials, info.json and
  stream.json from the zones' small files read by HTTP range (87 zips' scenes + materials in about 1 min).
- What the slices share is fixed in zones/ticino_plan.json (region_plan.py, lists only grow with --add): heights
  150..3650 m (5.3 cm a step; the Malcantone alone had 1 cm), 21 layers, 43 forest types, 15 ground types. The zones'
  own z0 went down to -116 m (ti_1_2, ti_1_3) and -704 m (ti_m3_9): carved lake beds / bad ground, clipped at 150.
- No level shape of any zone is used by more than one TSStatic (all single-use merged chunks): every zone's shapes go
  under z/<zone>/. Same path, different content across zones: 15,000 shapes (roads, buildings, skin...) and 7 sign
  PNGs (osm_stop/timetable) and material files: shapes are per zone, the PNGs first zone wins, materials merged by name.
- A slice writes only the tiles and 64 m collision cells of its own core (Src.core_cell, collision.build bounds): a
  clipped DAE keeps all its vertices, so dae_center (the box of the first geometry) can lie outside the core, and two
  zones would have written the same tiles/o_*.json or col/c_*.bin (one file wins in the game's mount).
- warmup_shapes.json of all Ticino lists every tile shape (hundreds of thousands): the warm-up of the 4-zone region
  had 13,707 (10,212 took 968 s on michi's PC). region_base writes warmup/<zone>.json and stream.json zoneCores;
  warmup.lua warms only the zones within RADIUS_M (3 km) of the camera.
- First run of the 87 zones (run 40830705580, 2026-10-29): 78 slices in about 45 min (20 at a time, the densest
  ti_1_0 19 min), 9 stopped in collision.write_cell ("a vertex out of the cell's range"): triangles with a corner up
  to 560 m from their 64 m cell (the 4 Magliaso zones never had one). write_cell now leaves such triangles out and
  counts them (colStats tris_out_of_cell_range: ti_0_5 20,799 of 10.5 M, ti_m3_9 272, ti_1_2 100). Which meshes they
  are is not looked at yet: if a car falls through something in those zones, look there first.
- The base of 87 zones took 2 min (86 s of HTTP range reads): 452 spawns, 57,051 AI roads (4,737 km), 1,534 welded
  cut ends, the main AI piece 1,879 -> 2,944 km, 122,091 parking spots, 306,957 collision cells in stream.json.
  89 zips, 51.8 GB. The old ticino_region_*.zip hold the same levels/ticino paths: never install both.
- `gh api --paginate` on release assets follows a next link with repositories/<id>/..., which the cloud proxy refuses
  (403): page by hand (&page=N).

- Loading in a wave (michi, 2026-10-29, "prima le cose vicine, poi quelle lontane a onda"): objects.retarget queued the
  drawn objects in the raster order of the tiles, so a building 6 tiles out could be made before the wall beside the
  car, and while the next terrain window's files were written (many frames) no object was made at all. Now the queue
  is sorted by ring (colliders first, deletions after ring 1), forest.retarget makes rings 0-1 whole, then the far
  rings at WAVE_PART of their share, then the rest, and stream.lua makes rings 0-1 before the window's files. The
  forest rows of the next ring are read in idle frames (they were read in the frame of the first tree). Checked
  only outside the game (tests/wave_order.lua); not measured on the PC yet. There is no luajit binary in the cloud
  container: `pip install lupa` gives LuaJIT 2.1 (`from lupa import luajit21`).

- Phase 2 of the wave (region.split_dae, 2026-10-29): a streamed single-use shape over SPLIT_BYTES (2 MB) whose kept
  triangles reach a 192 m square or more is cut into 192 m squares, each its own tile entry (z/<zone>/<shape>_q<i>_<j>.dae).
  clip_dae keeps ALL vertices of a geometry: cutting into many pieces that way would carry every vertex in every piece,
  so the pieces are compacted (each source cut to the indices its triangles use; sources must look as bng.write_dae
  writes them, else that geometry is not compacted). A piece with no triangle of some block gets one of no area on the
  corner nearest the piece (a placeholder at idx[0] lay anywhere in the shape and opened collision cells there).
  ti_0_m1 before/after: same 22,558,815 triangles with the same world centres per group, z/ 3,050 -> 2,905 MB, DAEs
  1,829 -> 3,357 (p95 7.2 -> 3.3 MB; the 128 m skin tiles stay whole), one more tile and collision cell, slice 152 -> 227 s.
  First run on all 87 zones (run 40881073781): ti_3_6 stopped in _write_kept (argmin of an empty sequence): a
  <triangles> block with NO triangles in the source shape asked for the placeholder's nearest corner. An empty block
  now stays empty.

## Motorways and missing textures in the Ticino zones (2026-10-28, first region test)

- Street lamps, benches and delineators were red "missing texture" models in the region: a zone never runs props.py
  (carryover.props returns at once in a zone), so art/shapes/props/vanilla.materials.json (italy_poles_lights_etc,
  eca_bld_wood, m_oldwood, italy_bld_metal, trafficlight...) and the mp_delineator_* definitions were never written,
  while lamps_step, street_life and props_osm place those models in every zone. dati/vanilla_shape_materials.json holds
  the v3.1.1 definitions; carryover.zone_materials writes them in a zone, region.py adds any the zones lack. Compare
  a zone's material keys with the released Malcantone's (and the DAEs' `<material name=` against them) after adding a
  step that places game models.
- Motorways had no AI road, paint or guard rail: ai_roads.TLM_DRIVE had no "Autobahn" (the Malcantone has none), and
  markings_rules and the rails work from the AI roads / measured runs only. In a zone Autobahn is now drivable (one-way
  by RICHTUNGSG, lanesRight from the width, 120 km/h, no village 50), markings_rules.lay_lanes draws 6/12 lane lines and
  the hard-shoulder line on one-way roads of 2+ lanes, guardrail_mesh.motorway_runs lays rails on both edges, open
  where another road comes within its half width + 0.8 m at the same level (z within 3 m: not under a viaduct).
- swissTLM3D draws the two carriageways of the A2 2.5-4 m apart along the MEDIAN, not in their middles (survey at
  Lugano: carriageways at -11.5..-0.5 and 2.5..14.3 m across one line). Meshed 11 m wide on those lines they overlapped
  into one 14 m slab. network.separate_carriageways (zone only) moves each line away from its twin to carriageway +
  MEDIAN apart before measuring: share of line points inside the survey road 0.1-0.6 -> 1.0 on most of ti_1_0's lines.
- Twin tunnel tubes (Galleria della Collina d'Oro, lines 10.5-18 m apart) ran into each other: a 10.5 m motorway
  carriageway made 13.5 m tubes and 16.7 m headwalls, each closing half the other's opening ("tunnel mezzi rotti").
  Motorway tubes are now 8 m of carriageway, and twin_heads stops a headwall TWIN_GAP short of the twin's inside wall.
  The two halves of a tube across a zone core edge matched to the cm (both zones build the whole tube): not the cause.
- None of these can be fixed in region.py (it only reads the built zones): they need the zones rebuilt (stages ai,
  guardrails + finishing markings, tunnels). Only the materials went into the region of 2026-10-28 evening.
- The first Magliaso region (ticino_region_1..5, 2026-10-28) opened West Coast USA on DESKTOP-OUPOLOA: region.py took
  the first zone's info.json as it was, with spawnPoints spawn_magliaso... (the region names them ti_0_m1_spawn_* )
  and a preview ti_0_m1_preview.jpg the copy skips (*.jpg). beamng.log: "Spawnpoint validation failed", 404 on the
  preview, and freeroamConfigurator.json kept west_coast_usa: the level was never requested. region.py now lists the
  region's own spawns and packs the preview as ticino_preview.jpg. A local fix (info.json + jpg) sits in the user
  folder levels\ticino on that PC: delete it once a fixed zip 1 is installed. After any change to object names, check
  info.json's spawnPoints and previews against the packed level.
- With info.json fixed, 0.40.3 crashed as soon as forest.lua registered a Forest: the engine reads EVERY *.forest.json
  of the level as old-format forest data (ForestData::readAppendJsonV23Format "string pointer is null" on
  tiles/t_10_0.forest.json, the streamer's row format). The tile files are now t_<cx>_<cy>.trees.json (region.py,
  forest.lua M.FILE). Never give a file of our own a name ending the game claims (.forest.json, .materials.json,
  items.level.json...). warmup_materials.json (region.py) broke the same rule: "loadJsonMaterialsFile| unable to
  deserialize" at every load of all Ticino (2026-10-31); now warmup_mats.json. michi's zip 1 was rewritten by hand on DESKTOP-OUPOLOA (original in
  %LOCALAPPDATA%\BeamNG\ticino_backup\ticino_region_1.orig.zip).
- First region drive on DESKTOP-OUPOLOA (2026-10-28 evening, fixes tried there as user-folder overrides, then ported):
  - Shipping .dae: the game imports each COLLADA file on first use (~0.1 s, up to 46 s for bld_*/river_*) -> 30 s of
    stutter in every new zone (13,707 shapes, ~27 GB of XML). Ship .cdae or warm up once. A warm-up from the main menu
    writes grey stub main.materials.json next to the shapes in the user folder (level materials not loaded): run it
    inside the level or delete them. Now ticino/warmup.lua (extensions.load('ticino_warmup') inside the level, once)
    reads warmup_shapes.json and warmup_materials.json that region.py writes.
  - Textures (412 sign PNGs, mp_ch_*) are cooked on first sight, 0.05-0.14 s each: warm up (one ProceduralMesh quad
    per material in front of the camera for a few frames, ~4 s) or ship cooked DDS. Same warmup.lua, after the shapes.
  - Terrain window swap 0.6-0.9 s every 384 m: the 12,639 invisible AI DecalRoads re-clip to the terrain at every swap
    (+0.1-0.35 s), 7 distinct base colour maps force 7 terrainMaterialCache repacks (~50 ms each), and the window moved
    at every tile. stream.lua: the window moves only when the car's tile leaves places FOLLOW_LO..HI (2..5 of 8), then
    by 4 tiles; DROP_AI_ROADS deletes the AI DecalRoads after the first map.reset (later jumps keep that map);
    BASE_COMBINED makes one base map for all materials. ~0.22 s every ~1.5 km. setField('position') costs the same as
    setPosition. The AI roads need heights of their own, read once, not clipped to the terrain (to do).
  - Reading 4.9 MB terrain blocks from the zip inside one frame: 150-230 ms frames. stream.lua yields after each block
    read (yieldingCache) and pack_region stores blocks/ uncompressed.
  - be:reloadCollision costs ~0.15 us per ProceduralMesh triangle: 9 collision cells of 128 m in Lugano were 60-110 ms
    a rebuild (radius 2: 25 cells, 170-250 ms). collision.CELL_M is 64 (25-35 ms, hysteresis colCell / 8). Rebuilds
    only for props or trees wait up to RELOAD_DEFER_MS for the cells' next one; street clutter never collides
    (objects.NO_COLLISION_SHAPES, 60 % of the colliders).
  - A GE extension named ticino_warmup is looked up as ticino/warmup.lua (an underscore is a folder).
  - The PC keeps user-folder overrides (lua/ge/extensions/ticino/, levels/ticino/{info.json, ticino_preview.jpg,
    stream.json, col64/, blocks/}) that win over any zip: run D:\ticino_tools\pulizia_override.ps1 before new zips.

## Ticino as a product (branch ticino, install/, settings, 2026-10-29)

- The branch `ticino` holds all Ticino work (n0o5te + wave loading + helper + parking cap); thread branches open PRs
  against it, not main. beamng/ticino/diag (test overrides) was dropped from it: get it from history if needed.
- The traffic signal errors of the full Ticino ("Map node could not be set", 4,020 of 4,065 instances, each logged
  twice: at the load and at the jump's map.reset) are the AI map's z 0 nodes: the 45 that worked all lie within
  ~2.5 km of the spawn (the only terrain at load). trafficSignals.getBestRoad uses map.findClosestRoad, a 3D
  distance searched up to 200 m. Checked against the json first: every signal is 0.6-4.3 m from an AI road node in
  xy and within 0.1 m in z, so the data is right and the game's graph is not. In 0.40 map.reset IS loadMap and takes
  ready nodes (loadMap(customMapNodes): only convertToSingleSided, no linkMap): the way out without DecalRoads.
- ticino_perf.csv of the first jump on the full map: posMs 1,711 + terMs 1,811 (the 57,298 AI DecalRoads re-clip on
  the block move), next1Ms 11,684 (frame after the swap), then a 30.5 s frame (the map.reset of the jump).
- stream.lua reads <user>/settings/ticino.json (preset, helper, diagnostics, field overrides); the csv files are off
  unless "diagnostics": true. A PC test that reads ticino_perf.csv must write that file first.
- The installer's helper and installer zips must not be called ticino_*.zip: the installer (and the game's mods
  folder logic of every earlier script) treats every ticino_*.zip as a level zip. They are helper_ticino.zip and
  installer_ticino.zip.
- Windows PowerShell 5.1 (Win11 5.1.26100) returns a JSON array as ONE object when a function returns
  Invoke-RestMethod straight (`return Invoke-RestMethod ...`): @(Api ...) had Count 1, the asset pages stopped after
  the first and the installer said "no ticino_base zip" (PC test 2026-10-30). Assign the result first (`$r = ...;
  return $r`). The pwsh parse check of ticino_tools.yml cannot see this: run -ListOnly in 5.1 after any change to Api.
- Installer test on DESKTOP-OUPOLOA (2026-10-30, 12c25f3): 5 zips downloaded, 84 sha256 checked, overrides moved,
  cache cleared, settings and shortcut written; the shortcut starts the game and the helper, which ends with the game
  (level 2.4 s, first jump swap 125 ms). One fault: ticino_tools.yml replaced helper_ticino.zip on the release while
  the installer ran (new asset id) and curl got 404 (error 22) six times on the old id. Get-Asset now reads the
  assets again after a failed try and takes the new one. Run from PowerShell with `*>&1`, curl's progress bar on
  stderr shows as NativeCommandError (not from the .bat): cosmetic, not changed.
- Helper test on DESKTOP-OUPOLOA (2026-10-30, 4 flights Manno -> north at 33 m/s, warm cache): the helper works
  (window wait at a jump 62-72 ms) but changes nothing in the frames (28.1 vs 28.4 fps at the 30 cap). The real
  hitches: the terrain swap frame 207-256 ms at every window move (terrainFile ~105 ms + the frame after), the forest
  after a spawn (~75 frames of ~190 ms for ~100 s at PER_FRAME 250, the budget was looked at only every 64 items) and
  the AI map read at a jump (25.6 s, PR #105). forest.PER_FRAME 64 did not help (see Streaming helper process).
- Installer on an incomplete release (2026-10-31, ticino-all-cdae while two slices were rebuilt): every ticino_*.zip in
  mods not named in the release counted as old, so the valid ti_2_4 zip was moved out, and the Move-Item error
  ($ErrorActionPreference Stop) ended the install (the PC run discarded stderr, so no message). Now only zips of a zone
  the release has under other names are old, the others are kept with a warning, and a failed move does not stop it.
  Capture stderr (`*>&1`) when running the installer in a test.
- The cloud session could not run a downloaded pwsh to check the PowerShell scripts (auto mode refused code from
  outside): ticino_tools.yml parses every install/*.ps1 in pwsh and in Windows PowerShell 5.1 before packing.
- `gh api --paginate` on release assets failed through the proxy (it follows a "repositories/<id>/..." next link,
  403): page by hand with &page=N.
- Pushing a branch for the first time (or the same commit to a second branch) starts every workflow whose push
  paths the branch's commits touch, as if every file changed: the first push of claude/project-thread-361hr5 (a
  merge of n0o5te) started zone_build.yml for the 59 zones of zone_list.txt, ticino_region.yml, ticino_all.yml and
  ticino_test.yml (2026-10-29 19:28Z); pushing ticino's commits also to claude/project-thread-mfvmk9 doubled
  ticino_all/ticino_tools (both write the same draft release). The zone build and region run were cancelled after
  25 min (19 runners busy). Push Ticino work only to `ticino`; check `actions/runs?branch=<new branch>` after any
  first push and cancel what was not meant.
  Again 2026-10-30: merging origin/ticino into claude/project-thread-qgsibb (.cdae) and pushing started ticino_all
  (4-zone retry list + base), ticino_tools and ticino_helper on the thread branch; cancelled at once (the base job had
  to be force-cancelled: a plain cancel left it running; it stopped at its first step, nothing uploaded). Before
  pushing a merge of ticino, check whether it brings changes to all_stamp.txt, helper/** or install/**.

## Stutters of the Ticino and what BeamNG.Earth does about them (thread "Eliminare gli scatti del Ticino", 2026-11-01)

- BeamNG.Earth (github.com/TecnaGamer/BeamNG.Earth, MIT) clones fine with `git clone --depth 1` in the cloud. Its
  answers to the same problem: (1) governor.lua: streaming gets ~2 ms a frame from a token bucket, and a heavy step
  (terrain commit) runs alone with 2 quiet frames before and after, because the engine moves the world by a smoothed
  frame time (median of 3 + slow average): a LONE slow frame is dropped (a hitch, game speed right), two or more in a
  row pass and the game runs slow then fast. Our PC flights had 8 "near objects" bursts in 1.6 s, one EVERY frame,
  exactly the bad pattern. (2) framepacer.lua: frames shorter than the recent 70th percentile sleep the rest
  (socket.sleep in onPreRender), on by default, costs up to a tenth of the fps. (3) server/staging.py: temporary files
  outside the user folder (the game's file watchers fire for every file made or renamed in it, up to ~1 s a frame)
  and one read of every new file on Windows before the game opens it (the antivirus scan of a first open cost the
  game 20-184 ms a tile file). (4) TerrainBlock castShadows 0 (every block move redrew the cached sun shadow map). (5)
  pooled shape and Material names (the frame cost grows ~0.3 ms per 1000 distinct shape files ever loaded in a
  session: "long sessions get more stuttery"). Not ported: (5) needs the server to serve fixed slot paths.
- Ported (ticino/pace.lua, stream.lua): the gate (every scene-changing step: near objects, bursts, forest, collision
  cells, rebuilds, the terrain swap waits for QUIET=2 calm frames, open while paused, CALM_TIMEOUT 30 frames), the
  pacer (settings "pacing"), engine subsystems in the slow-frame lines (Engine.Debug.getLastPerformanceMetrics), the
  helper/server write_atomic with staging + warm read, terrainShadows as a setting (default still on: mountain
  shadows must be checked in screenshots first). The window job's files and its swap are now in different frames.
- Forest frames (~200 ms a touch "whatever it adds", PC 2026-10-30/31) fit BeamNG.Earth trees.lua: a frame adding or
  removing Forest items costs the engine ~0.5 us for every item in the level of each SHAPE touched (any Forest), and a
  pass touches nearly all 43 tree shapes. Earth splits the populations with SHAPE_VARIANTS path spellings
  (dir/./name). forest.SHAPE_VARIANTS (default 1 = off) does it per block; to be checked on the PC with 4 (frames, and
  no imposter squares: a respelled path may need its own imposter bake).
- tests/sim_stream.lua cannot judge the gate: its frame "wall time" is the Lua's CPU time, so every frame is calm;
  it only proves no Lua error and the same throughput (2,402 vs 2,406 objects in 120 s with SPAWN_MS=30).
  tests/pace_test.lua emulates the engine's filter for the effect. sim_stream needs a level: curl ticino_base_1.zip
  and ticino_ti_0_0_1.zip from the public pre-release ticino-v1 (2.1 GB, ~1 min) and unzip both into one folder.

## Shapes compiled to .cdae (beamng/ticino/dae2cdae.py, 2026-10-29)

- The zones' shapes are all bng.write_dae files (one node `<name>_a<size>` per detail level, one <triangles> per
  material, VERTEX/NORMAL/TEXCOORD/COLOR with the same index for every input): dae2cdae parses only that and refuses
  the rest (trees' bb_autobillboard, transforms, polylists), which stays .dae. Forest shapes (managedItemData) and
  shapes with prebaked imposters beside them (x.dae.imposter.dds) are never compiled: the imposter names follow the
  shape file's name.
- cdae.encode's `lods` follow BeamNG.Earth's convention (the main mesh drawn from lods[0]'s size up), NOT Collada's
  (each node's trailing number is its OWN size, nothing drawn under the smallest): cdae.encode_details writes our DAEs.
- First self-check failed on 6 of 709 shapes: the test flipped v in float64, the writer (as the engine) in float32
  (2048.0325 vs 2048.0322 on large building uvs). Compare in the writer's precision before suspecting the writer.
- region_slice compiles AFTER collision.build (it reads the .dae) and rewrites the tiles itself; the base cannot see the
  slices' files, so the shared shapes are decided on both sides by the same test (dae2cdae.compilable) and the
  slices list what they left as .dae (slice.json "cdae.kept"). objects.lua falls back to the .dae if a .cdae is missing.
- The proxy blocks `gh api --paginate` on a release's assets (it follows a repositories/<id> URL: 403): page by hand
  with `?per_page=100&page=N` (a draft release with 178 assets showed only 100).
- `rm -rf zsrc/*` after a `cd` in the same command was blocked by the safety check (relative glob): use absolute paths.
- Golden check against 43 .cdae the game wrote on DESKTOP-OUPOLOA (tests/test_dae2cdae.py --golden, 2026-10-30): the
  game TRUNCATES vertex colours (floor(c*255), our first writer rounded: off by 1), computes tangents in float32, skips
  triangles of zero uv area and falls back to (0,0,1) for a zero tangent (not orthogonalised); it orders the triangles of
  a primitive its own way (same set, same picture). After matching that: 33 comparable pairs identical in positions,
  normals, colours, primitives and triangles; tangents differ on 2.5 % of the vertices, all with degenerate uvs. Ten
  pairs came from another version of the shape (the cache was older than the zips): compare positions first and drop
  such pairs before calling the converter wrong.
- First full .cdae build (run 41095920457): slice ti_1_m2 stopped in compile_level (min of an empty array): a shape whose
  <triangles> blocks are all empty. parse now refuses it (stays .dae), and any other error of one shape keeps that
  shape as .dae (listed in cdae.kept) instead of stopping the slice.
## Ticino server (thread "Studiare la mod tutta nel server", 2026-10-29)

- With the 88 Ticino packs in mods the game spends 75-81 s at EVERY start in initDB (beamng.log: the last
  "mountEntry" at 5 s, "took ... to reorganise 596326 files" at 80-86 s): mounting is per file or per byte, not free.
  Runtime FS:mount of one zone pack would cost about 1 s on the game thread: the server puts loose files under temp
  instead. Read the game's own log for a cost before guessing it.
- The game's .cdae cache of our zone DAEs lives at temp/<same path>.cdae (12 GB after four zones on michi's PC).
  dae2cdae.py output vs those files: same geometry; the engine keeps the DAE node tree (base00, start01) and names
  the details detail<size>, sets smallestVisibleSize to the smallest detail (a shape is hidden below it: cdae.encode
  drew everything down to 2 px), takes the LOD meshes' own normals (encode ignored them), stores colours truncated
  (floor(c * 255)) and reflectanceMap = the material's index. Device files more than 7 folders deep cannot be staged:
  copy them to a shallow folder first (temp/claude_cmp on michi's PC, left there).
- raw.githubusercontent.com is blocked from michi's PC device shell too (403): files reach it only through the thread.
- The pkill self-kill again (exit 144): `pkill -f "[t]icino_server.py"` in a command that also ran
  `server/ticino_server.py`. Kill by PID in a call of its own.
- Server mode, first try: re-asking for late tiles called forest.retarget at every ready.json change; the forest queue
  restarted each time and the far ground (made only when objects and forest are idle) was never made (10 far tiles
  instead of 1,155). Ask again only for tiles that were late and are ready now, at most once a second.
- The "packs in mods" probe must not test one tile file: the first key of stream.json tiles may be a zone that a test
  install does not have.
- ticino's own dae2cdae.py (build-time .cdae, PR #103) replaced the server's: the server calls compile_bytes(bytes).
  A shape it raises Unsupported on is counted as failed and NOT served (the tile names it as .cdae): watch "failed" in
  the server's status line. Zone packs built with the .cdae already are copied as they are.
- PC test of the server (2026-10-31, kit c77c2de): game start 85 s -> 4 s, level load the same, flight 94 fps, but
  standing still in Lugano from an empty cache the scene never settled (live 1,357 -> 6,943, 27 fps after 6 min). In
  the simulator: every tile the server finished made the streamer re-queue its objects and trees and force a collision
  rebuild (68 rebuilds against 1 with the packs). files.poll now holds the tiles that came until none came for
  SETTLE_MS (at most SETTLE_MAX_MS, at once within URGENT_RING of the car), and a refresh rebuilds the collision only
  for a tile within one ring and touches the forest only within its radius: 5 rebuilds, the scene still in ~40 s.
- tests/sim_stream.lua without REALTIME=1 runs its clock on CPU time: with SPEED=0 the bursts wait forever ("wait
  burst") in BOTH modes. Compare server and packs standing still only with REALTIME=1.
- adopt with shutil.move hit WinError 32 on a zone zip held by a ticino_helper.exe left running (a PyInstaller onefile
  child survives Stop-Process of its parent): the 1.85 GB copy was made and the original stayed. adopt now probes every
  pack with a rename first and moves nothing while one is open, and a cross-disk copy goes to .part and is removed
  again if the original cannot be.
- PR #104 was merged with conflict markers left in beamng/ticino/README.md (the merge of ticino into the thread branch:
  only CLAUDE.md, stream.lua and dae2cdae.py were checked). Run `git grep -n "^<<<<<<< \|^>>>>>>> "` before every
  commit of a merge.
- Restarting the thread branch from ticino after the merge and pushing started ticino_all.yml on the thread branch
  (the ticino commits new to the branch touch all_stamp.txt): force-cancel at once. ticino_tools.yml now runs only on
  ticino (a thread branch with installer changes replaced the release's tools); installer changes are tested with
  ticino_install_check.yml (check_stamp.txt: parse, Move-Zip, Test-BaseServes, -ListOnly, no upload).
- Windows PowerShell 5.1's ZipFile.CreateFromDirectory writes entry names with backslashes: a check of a zip entry by
  name must take both separators (Test-BaseServes said "no files.lua" on the test zip).
- It happened a second time when the branch was restarted from ticino again to bump exe_stamp.txt: every restart of a
  thread branch onto ticino commits that touched all_stamp.txt starts ticino_all there. Bump a stamp on the branch
  only after checking `git log origin/<branch>..origin/ticino -- beamng/ticino/all_stamp.txt` is empty, or force-cancel.
- A new server flag (--game-pid) was merged into the installer while server_ticino.zip on the release was still built
  without it: the shortcut would have started a server that stops at once (argparse error). Rebuild the exe (exe_stamp)
  in the same round as any installer change that passes a new flag.

## View distance of Ticino (farlod.py, objects.lua FAR_LOD, 2026-11-01)

- Up to ticino 8008a51 nothing stood past the far tiles (16 tiles of 384 m, ~6 km) and LevelInfo.visibleDistance was
  12 km: the mountains ended in the sky. farlod.py (run by region_base.py) makes 3,377 coarse tiles (levels 2-5: 1.5 /
  3 / 6 / 12 km, 33 x 33 vertices like a far tile) from the 39,300 far tiles (read by HTTP range from the slice zips in
  ~90 s), ~300 MB raw, ~107 MB zipped in the base; objects.lua shows them as BeamNG.Earth's quadtree (~500 more drawn
  tiles). stream.lua sets visibleDistance 60 km and haze 6e-5 (settings viewKm, fog) only when the base has them.
- A far tile's .cdae vertices are reordered by the writer (cdae first_use) and the skirt repeats the border's xy 4 m
  lower: read a far tile by the xy of its vertices, keeping the highest z, never by vertex index.
- First Lua version, checked by tests/far_lod.lua (every far tile covered exactly once each frame): at a teleport the
  old coarse tile under the new terrain window stayed drawn with the terrain (64 tiles doubled). Coarse tiles that
  reach into the window are hidden now (a few holes round a jump while the new far tiles come, never two layers).
- Not tested in the game yet (2026-11-01): FPS with ~500 more static tiles and 60 km view, and whether the borders
  between levels show (each coarse border vertex is the highest far height of its stretch, skirt down to the lowest).
- First look in the game (PC photos from San Salvatore, 2026-11-01, bases 69a1db7 .. 4a53bd1): the ground ended ~6 km
  out in a straight edge (the square of the fine far tiles), no coarse tile anywhere, although the log had "far levels
  2..5: split within ..." (no override, current base, packs mode). The coarse tiles were queued and never made: after
  the jump's FAR_JUMP_MS (which made the fine tiles, nearest first) only the bursts make far tiles, and a burst gave
  stepFar what the objects and the forest left of BURST_MS, i.e. nothing while objects were queued (always, driving or
  in a town). The far trees are stepped INSIDE stepFar, so they never came either (FAR_TREES_MIN_MS could not help:
  stepFar was not called). The sim showed it only with SPAWN_MS > 0: 166 far tiles (all from the jump) for a whole
  150 s flight with 1,255 queued; with free shapes every queue drains at once and the starved step looks fine. Now
  stepFar gets FAR_BURST_MS (6) of every burst before the objects: REALTIME=1 sim, 1 ms a shape, 0 -> 252 coarse tiles
  in 2 minutes of flight. Judge any budget change with REALTIME=1 and SPAWN_MS > 0 (the burst clock is CPU time
  otherwise: 18 bursts in 60 s of driving instead of 170).
- The thin dark straight lines over the plain and the lake in the same photos (they ran on from the land into the lake,
  so not the WaterBlocks) were the far tiles' NORMALS: cdae.write without normals takes face_normal_sum, and the
  skirt's vertical faces share the border vertices, so every border vertex leant 45 degrees out of its tile (a slice's
  far tile: border median 45.0, inside 0): a line of shade along every 384 m tile edge, and every coarse tile edge. A
  ray-cast render with Lambert shading of those normals made the photo's grid of lines; with central differences on the
  height grid they were gone (scratch view/shade.py). farlod.build_fine now writes the far tiles again in the base
  (farlod/l0_<cx>_<cy>.cdae, stream.json farFine, objects.lua loads them as they are, never from the server): the
  slices' heights and colours to the mm, the far ground's own normals across tile and zone borders (normals_at), 39,300
  tiles in ~30 s; the coarse levels get normals_at too, blocks.far_cell far_normals (for a future slice build). Give
  any mesh whose border vertices are shared with a skirt or other extra faces its own normals.
- Since then the base comes in four parts (region_base, pack_region.pack_fixed: sorted, one date and mode, bytes that
  depend only on the files): 1 scene, Lua, map, textures and the rest; 2 the far ground (farlod levels 0-5, ~1.2 GB);
  3 the far trees; 4 the far houses. The installer keeps a zip with the release's size and sha256, so a base rebuilt for
  its Lua sends ~0.3 GB instead of everything. Anything that handles "the base zip" must take every ticino_base_<n>.zip
  the release lists and read info.json / files.lua from ticino_base_1.zip: the server's download command removed every
  other ticino_base_*.zip when it took one (fixed in ticino_server.py, exe not rebuilt) and the GUI app of PR #106
  retired the others and read the last-sorted one.
- A fixed packing is not enough: the FILES must be the same bytes too. Part 4 changed between two bases with no change
  to farbld (the sha256 of the 6705113 base), and two local runs of fartrees on the same rows differed in 30 of the 36
  coarse tiles: the coarse tiles and blocks were assembled in the order the pool's imap_unordered handed the tiles
  back, and bng.material gives every material a random uuid4 persistentId (pipeline/bng.py pid()). The coarse sets
  are now joined in tile order and the far materials take a uuid5 of their name: two runs with 4 workers, 0 of 390
  (trees) and 287 (houses) files differ. Build a part twice and compare the files before trusting it to stay put.

## Ticino map and spawn names (worldmap.py, 2026-11-01)

- The stock big map (M, freeroam/bigMapMode.lua) is a 3D camera over the loaded level framed on
  `core_terrain.getTerrain():getWorldBox()`: in the streamed Ticino that is the 3 km window round the car. A first plan
  (a photo mesh shown only in big map mode, the terrain box faked) was dropped for BeamNG.Earth's way (michi: "prendi
  spunto da beamng earth"): replace toggleBigMap / enterBigMap with a 2D UI route of our own drawing level-file tiles.
- The far ground's vertex colours (12 m, every zone, `farlod.Ground`) already look like a map; no imagery service is
  needed (swisstopo WMTS is blocked in the cloud anyway). `farlod.read_release('ticino-v1', ...)` reads them by range in
  ~2 min for a local test.
- Every zone's route spawn points are called spawn_magliaso / spawn_mid / spawn_pura (build_level.stage_spawns copied
  from the Malcantone): 452 points, "magliaso" at Airolo. The village points carry an ASCII slug only. swissNAMES3D is
  blocked in the cloud: worldmap.fetch_settlements falls back to the slugs; check `spawn_names.json` of the base run.
- Lua 5.5 (lupa, for a quick stub test of a mod file) has no math.atan2; LuaJIT in the game does.
- The first names (base of 2026-11-01) took the NEAREST swissNAMES3D "Ort" of any size: alp hamlets (Pardé, Büèe,
  Ligiazun) over the village 1 km away, labels 10 km off ("Cioss Prato (10 km SW)") and repeats numbered ("Stabio (2 km
  SW) 2"). Second try (base 12:00Z): "never give a place twice" pushed points onto unknown hamlets (Manno (0.6 km S) ->
  Taiáda) and a strong town weight gave "Andermatt (13 km W)"; and swissNAMES3D lists every name of a place as its own
  row (UUID shared): "Bellinzone (3 km SW)", "Lucarn" (Locarno) slipped past the village names. Now: one entry per
  UUID with its official name, never an exonym (a zone's village point "ligiaun" is Lugano: its Romansh exonym was
  the village slug, and taking the village's spelling first renamed Lugano Ligiaun in the third base), a mild weight by EINWOHNERKATEGORIE
  (x1-2.5), a used place again with distance and direction, beyond FAR_M the plainly nearest place. Compare the whole
  spawn_names.json of a run with the one before (changed labels), not a few samples. spawn_magliaso_paese is a
  VILLAGE point: strip "_paese" only after the GENERIC test (its slug is "magliaso").

## Far trees of Ticino (fartrees.py, objects.lua far trees, 2026-11-01)

- michi: "non puoi anche aumentare la distanza degli alberi?". More rings of Forest were not the way: every frame that
  touches a Forest cost ~200 ms on the PC. fartrees.py (run by region_base.py) bins each tile's tree rows (the slices'
  t_*.trees.json, read by HTTP range) on a 28 m grid, one card per cell (two crossed quads, a clump texture made in
  numpy: fartrees.png 4 kinds x 2), and objects.lua shows them as plain TSStatics (collisionType None) from the Forest's
  RADIUS out to FAR_TREES_RADIUS (12 tiles, settings "treeKm"). A tile coming into the Forest's rings keeps its cards
  until forest.made(key) (at most 20 s): no gap at the line where the real trees begin.
- A ProceduralMesh was no option for them: it always enters the static collision (EarthNG: disableCollision does not
  take it out; every rebuild would pay for ~400k card triangles). Render-only things must be TSStatic + collisionType None.
- Size on ti_0_0 (397 tiles): 30 MB raw, 6.4 MB zipped; all of Ticino ~0.5 GB zipped in the base. Cells of 24 m were
  only 20 % bigger than 28 m (most cells hold few trees). Not tested in the game yet.
- v2 (michi 11:37Z: "gli alberi devono vedersi sempre come anche le case", "metti gli alberi low poly lontani del
  Malcantone"): the clumps are now drawn from the side views of the Malcantone's far trees (dati/far_imposters, 8 side
  views per model at 256 px, cells 8-9 are from above). The game bakes those imposters' albedo in LINEAR light (the
  fir's crown reads 8,12,7 in the DDS): convert to sRGB before using one as a colour map, and it still reads pale
  (SATURATE 1.4). The bare trunks of the imposters stood out as pale bars in a clump: below the fill line, pixels with
  no green take the under-fill's shade too. Coarse tiles l2_<bx>_<by>.cdae (4 x 4 tiles, cards of 64 m, +20 % of the
  fine bytes) carry the woods to FAR_TREES_RADIUS 40 tiles (~15 km); fine tiles only in the blocks within
  FAR_TREES_BLOCKS0 (2) of the car's block. A level change keeps the old shape until its cover is there.
  tests/far_trees.lua checks it: its first holes were the test's own (a first move of 7 tiles, and a made-up Forest
  that dropped its old rings before the far tiles came): count a tile the Forest still shows as covered.
- PC A/B flights at Manno (2026-11-01, base of 00:19Z, 150 s): gate+pacing on 83.1/84.6 fps vs off 90.1/80.5 (noise),
  frames over 100 ms 7-8 in every run. The gate as first written let more steps into a frame that had already changed
  the scene ("costs nothing new"): it concentrated the same cost into 2-3 frames of 400-550 ms. Now one scene-changing
  step a frame (pace.SAME_FRAME false). Pacing: no measurable difference, off by default. SHAPE_VARIANTS 4 was worse
  (a 537 ms near-forest frame with 255 ms "Ticking"): stays 1. The near-forest frames of 195-270 ms were the streamer's
  OWN Lua (createNewItem ~70 us a tree, 2,400-4,000 trees a pass), not the engine: forest.PASS_MAX_MS (30) splits a pass.
  After the jump's map.reset LuaGC took up to 520 ms in one frame: a full collectgarbage at the end of the paused hold
  (GC_AFTER_HOLD; the sim shows 180-245 ms there, inside the pause). A 482 ms frame with lua 0 in the streamer was other
  Lua (traffic/AI?), not looked at. Terrain swap 226-272 ms = terrainFile ~115 ms Lua + RenderShadows 102-135.
- PC round of fc13b35 (2026-11-01, 3 runs): the full collectgarbage('collect') at the end of the hold took 1.2 s in
  the frame the game went on ("near objects 1342 ms, lua 1217 ms, LuaGC 104": an explicit collect is counted as the
  caller's Lua, not as LuaGC), worse than the 520 ms it was meant to remove. Now collectgarbage('step') for
  GC_STEP_MS a frame during the paused hold until two cycles end (the hold waits up to GC_HOLD_MAX_MS more), and the
  game goes on in a frame of its own. The "near forest" frames of 185-205 ms that added 7 trees ("forest passes 0
  items +7", lua 177-198) were the jsonDecode of the tile's rows before the pass loop (PASS_MAX_MS only looked at the
  clock inside the loop). forest.lua parses the rows itself, PARSE_MS a frame (a 2,593-row tile: 5 ms in luajit, same
  rows as json.loads), prefetches the queued tiles first, and a block's next pass waits for the next frame after
  PASS_MAX_MS. CACHE_TILES 120 was under RADIUS 4 + the prefetched ring (121 tiles): 200.
- PC round of 4a53bd1 (2026-11-01): the 1.2 s frame was gone, but the hold ended "not all collected in 75 ms of
  steps": a time cap (3 s past the hold) let only 3 frames of steps happen (the paused frames are long), and LuaGC came
  back as 210-370 ms in 3 frames of the drive. The hold now waits for the two cycles by FRAMES (GC_HOLD_MAX_FRAMES).
  The 4 "near forest" frames of 186-196 ms (Lua) were still there with the own parser: about one per new 3x3 block
  early in a flight, when the Forest pool is empty and the frame creates and registers a Forest. forest.POOL_WARM
  makes 24 Forests at init, and the slow-frame line gives the step's parse / new Forest / slowest item ms to tell.
  terrainShadows false moved the swap's RenderShadows 110-122 ms into Render: no gain, stays on. A "wait burst"
  frame of 443-519 ms (Lua 382-435, streamer lua 0) ~10 s after the hold in every run is another extension's Lua.
- PC flights of 00e48dc (server mode): near-forest frames gone (POOL_WARM), frames over 100 ms 4-5, but over 50 ms
  190-226: ~15 "burst" frames of 120-430 ms, lua 66-79 + LuaGC 36-336. Each part of a burst (deletions, far houses,
  far ground, the far sets' <P>_MIN_MS inside stepFar, objects) looks at the clock only AFTER a spawn, so each made
  one shape past the burst's 20 ms. The burst now passes each part only the time left, and stepFar gives the minimum
  to one far set a call in turn. The forest row cache was a table a row (~600k live tables in 200 tiles), walked by
  the collector every cycle: the rows are one flat array a tile now.
- The "wait burst" frame of ~480 ms (engine Lua 411-417, streamer lua 0, traffic off) ~2 s after the hold was the stock
  minimap: ui/apps/minimap/roads.lua drawRoads builds a kd-tree of every navgraph link at its first draw ("if not
  kdNodes"), the 57k roads after the jump's map.reset, and resets it only at mission start/end. The traffic signals
  were ruled out first (their setup runs inside the map.reset frame). Found from BeamNG.Earth's notes
  (long-distance-gps.md 1.4). stream.lua now resets and builds it in the paused hold, once onNavgraphReloaded says
  the new map is there (map.reset lands a few frames after its call). The hold after the map read holds a live Lua
  heap of 1.1 GB (the AI map): every GC cycle walks it, the root of the LuaGC frames; a smaller AI map is the lever.
  PC flight with the minimap off (2026-11-01): the ~420-460 ms frame gone; left 3 bursts of 143-395 ms, nearly all LuaGC.
  The streamer's own share of every GC cycle: stream.json's colCells (307,321 "x_y" strings) and far (39,300) were kept
  as string sets and as the decoded lists in cfg: a full collection of such a set alone took 47-51 ms in luajit (lupa),
  as number keys 2 ms. objects.lua keeps both as number sets (nk) and drops the lists. tiles / forestTiles (~50k
  strings) are still string sets. A set of many string keys costs every cycle: use number keys for big lookups.
  michi 2026-11-01 17:38Z ("intanto disattivala completamente"): stream.AI_MAP false by default (settings "aiMap"):
  stream.noAIMap deletes every AI DecalRoad at the start and reads the map empty (map.lua drops the graph it built at
  the load), no map.reset, hold or minimap build at the jumps. No AI traffic or AI driver in Ticino meanwhile.
  The first PC run (76c3d7e) logged "(map.reset failed)" with no reason (a bare pcall): the empty read at the start
  raised and map.lua kept whatever it had. noAIMap now logs the error with a traceback and tries again AI_RETRY_MS
  (3 s) later, up to 3 times ("AI map read empty again"). Never swallow an error with a bare pcall: log what it says.
- "IMPORTING TEXTURE" on the house walls (PC 2026-11-01, server mode, cold cache, still there after 10 min): the log
  had t_bld_plaster_b / t_bld_ashlar_b cooked without error but no "reloadResource File changed" for them (there was one
  for plaster_nm and ashlar_ao): a material bound while its colour map is being cooked keeps the placeholder. No
  descriptor or slot error. texwarm.lua now draws one quad per material of the level art (113: buildings, roads, walls,
  skin, trees; not the 4,000 sign/prop plates) for 120 frames at the start, game paused, before any streamed object
  (settings "texWarm"). Not seen in the game yet. The same log: "Could not open /levels/ticino/z/ti_0_0/.../
  cableway_ropes.cdae" (and pylons, cabins, lema_summit): the base scene's landmarks name zone files, which in server
  mode are not there at the load. region_base.static_shapes copies them into the base (static/<zone>/...).
  PC flight j_A of 76c3d7e: no placeholder walls, no cableway error. Left: the first spawn of a zone's sign shapes in
  one frame (direction_signs.cdae 195 ms, props_signs 230 ms in ti_0_1, warm cache): one shape names 45-270 sign
  materials, each a PNG of its own. texwarm.roll (settings "signWarm") holds such a shape in the objects queue
  (objects.warmReady, S.waitWarm) until each sign material it names (warmup_mats.json, found in the last 128 KB of
  the .cdae, where the material names are plain strings) was drawn on a 4 mm quad 0.5 m in front of the camera, 3 new
  a frame for 3 frames, at most ROLL_WAIT_MS. Sim at tile 20,19: 271 materials of 3 shapes, scans 27 ms. Not seen in
  the game yet: if the spawn frames stay, the cost is the material instances, not the textures.
- PC test of the far trees v2 (base 69a1db7, 2026-11-01): treeKm 15 and 0 gave the SAME picture from San Salvatore,
  no far tree anywhere, while the sim made them. The base held the shapes, the material and stream.json farTrees /
  farTrees2 (checked by range read). Suspect: stepFarTrees only got what stepFar's budget left after the far ground,
  and in the game a far ground queue that each shape takes ms of keeps the whole budget. Now the far trees get
  FAR_TREES_MIN_MS of every call, and the log says "far trees in stream.json ..." at start, "far trees at tile ..."
  at every update and "far trees: first shape ..." once: read those before guessing again.
  The real cause (found with the missing far levels, see View distance of Ticino): stepFar itself was never called
  in a burst while objects were queued; FAR_BURST_MS gives it a share of every burst.
- PC photos of base 00e48dc (2026-11-01, San Salvatore, far trees on): the far trees were PALE grey-green boxes in a
  checkerboard over every hill, far brighter than the far ground's forest beside them (~165,180,170 against ~90,100,95
  on screen at 3 km). Three causes, all in fartrees.py: (1) the card normals pointed straight up, so every far view saw
  them at a grazing angle (N.V ~0.1) and they took the sky's reflection (Fresnel), pale blue-white; a double-sided back
  face may also get the normal flipped straight down (dark), hence a bright and a dark face per card; (2) the atlas kept
  the imposters' own mean colour (broadleaves 80,94,73 sRGB: twice the far ground's forest 62,65,41 in linear light),
  while a flat card has none of the self-shadowing that makes a wood dark from afar; (3) the dark under-fill below pale
  crowns made each card read as a box. Now each quad is two single-sided faces back to back, counter-clockwise from
  their side, each with its side's normal tilted TILT (40) degrees up (no doubleSided), the crowns are scaled to
  CROWN_RGB per kind (36,48,30 conifers .. 50,64,34 broadleaves) and the under-fill is UNDER (0.65) of them. The
  trunks are told from the crowns BEFORE the scaling (scaled, a grey trunk passed as green and stood as a light bar).
  The tiles are twice the bytes (16 vertices a card): base part 3 ~0.42 -> ~0.83 GB. Not seen in the game yet.
- The "boxes" had a cause in the geometry too: a card stood level on the LOWEST tree foot of its cell with its top at the
  tallest tops, and on a slope a 28 m cell spans 8 m (median) to 21 m (90th pct) of height near Lugano: a quarter of the
  cards were 1.5 times the trees' height or more, flat-topped, and every wooded hill a staircase of blocks with a
  stepped skyline. A card now follows the plane of its cell's tree feet (fartrees.plane, ridge-regularised so one tree
  or a row gives no slope across; each quad sheared, its sides still vertical): cards over 1.5 times the trees 25 % ->
  0.9 % (coarse 64 m cards 9.6 %). The three.js preview (scratch farview2.py: far ground, far houses and far-tree
  tiles in headless Chromium) shows the stepped skyline gone, but NOT the game's light: the old pale cards came out
  dark green in it (Lambert, no sky reflection). Judge colours and brightness only on PC photos.
- PC photos of 547c25a (2026-11-01, San Salvatore and over the lake towards Paradiso): the cards were STILL pale
  grey-green whatever their atlas and normals (big light triangles on the Morcote/Campione hill, a pale dotted carpet on
  the slopes) and their even spacing still drew a comb on every ridge at 2-5 km. Cards were dropped: fartrees.py now
  makes a CANOPY, a height field on the far ground's own 12 m grid (farlod.Ground, region_base passes it; 24 m in the
  coarse tiles) at the trees' height over the ground, with the far ground's material setup (vertex colours, no texture,
  roughness 1, no shadows of its own) and normals of its own heights, so it is lit like the terrain, which reads dark
  from afar in every photo. A vertex is in the wood by the crown cover of the 2 x 2 cells round it; out of the wood it
  goes DROP under the ground (a steep wood edge, nothing on open ground), skirts close every tile border (the next tile
  may be real Forest or the other level). Blocks of 4 x 4 tiles are made with their neighbours' trees: the 11,468 fine
  and 1,496 coarse points two tiles share near Lugano are identical, two runs (2 and 4 workers) the same bytes. Lugano:
  21 MB raw, 7.9 MB zipped (the cards v2 about twice). A height "mean + 0.3 (tallest - mean)" made one tall tree
  (a few are scaled to 40-50 m) a pinnacle on the skyline: crown-weighted heights smoothed over the vertices round it.
  A pinnacle that stays in a render may be the far ground's own (a rock outcrop): render without the canopy first.
  Isolated garden trees are no canopy (cover under COVER_MIN): towns from afar have only their woods.
- PC flights of the canopy (1860ef2, l_A cold / l_A2 warm, 2026-11-01): the woods looked right, but the fps fell along
  the flight (78-91 -> 55-60) while the far trees grew 0 -> 448 live, "removed 0" on every far trees line. Three faults
  of the far sets, all found in the log lines, none in tests/far_trees.lua (it let every move settle): (1) fsUpdate
  cleared every shape's doomed timer at every tile change, every 11.6 s at 33 m/s, under the trees' 20 s hold (so since
  the far sets were written); (2) 1860ef2's "busy" rule restarted it while the set's queue had anything to make, and the
  trees' queue never emptied (~2 shapes a second from their 1 ms minimum in turn inside stepFar; a 33 m/s flight needs
  ~3); (3) the coarse blocks the fine tiles behind waited for were queued by distance, after every fine tile, and never
  came (0 coarse after 250 s). Now a wait counts from when the shape was first doomed for the same cover, the covering
  blocks go first in the queue, a coarse block waits only while its own fine tiles are queued (F.pend2), the trees get
  FAR_TREES_BURST_MS of every burst. tests/far_trees.lua "starved flight" (one shape a frame, 20 frames a tile, the
  20 s hold): the old code held 1.71 times the shapes the tile wants, the new 0.51. A test of a hold must run with the
  queue slower than the moves, not settled after each one.
- The dark flat pieces among the near trees under the Lema (PC photo of 1860ef2): canopy tiles kept over the real Forest
  (inner tiles wait for forest.made). Their drop check (fsDrop) ran only inside the set's own step (while its queue had
  work) or when every queue was idle, so while the objects or the forest worked it never ran: now in every burst.
- stream.lua logs a "counts:" line every COUNTS_EVERY_MS (10 s): fps and frames over 50 ms of those seconds, objects
  live / to make / to delete / houses held, far ground, far trees and far houses (live, to make, over real ones, waiting
  for a cover, dropped, timed out), collision cells, distinct shapes seen in the session, forest items, Lua heap. Read
  what grows next to the fps before guessing. extensions.ticino_stream.farSets(treeKm, bldKm) sets the far sets' reach
  at run time (0: none) for an A/B standing still.


## Far houses and the free camera (farbld.py, objects.lua far sets, stream.lua followFreeCamera, 2026-11-01)

- michi 11:37Z: "ottimizza la mappa in modo che si possano fare riprese aeree comunque dettagliate", "gli alberi devono
  vedersi sempre come anche le case"; 12:12Z: "nello streaming puoi fare che segue anche la cam libera quando schiaccio
  SHIFT + C?". Up to here the houses ended at the buildings' radius (6 tiles, ~2.3 km) and the far ground beyond was
  bare. farbld.py (run by region_base.py after fartrees) makes far houses from the level's OWN building shapes (the
  buildings group of each o tile, read from the slices by HTTP range): fine b_<cx>_<cy>.cdae per tile = the roof planes
  (rims, tile heads and ridge caps of roof_details dropped: pieces under MIN_AREA / MIN_WIDTH) + plain walls down from
  every free roof edge to the house's foot; coarse l2_<bx>_<by>.cdae per 4 x 4 tiles = one box per house of 40 m2 or
  more in the roof's colour. Lugano (ti_1_0, the densest zone): 256 tiles, 30,605 houses, 1.0 M triangles, 93 MB raw
  in 7 s; 30 blocks 18 MB. Roof winding: the engine's is clockwise seen from outside (normal = (p2-p0) x (p1-p0)).
- The far trees' code in objects.lua is now one "far set" for both (farSet/fsUpdate/fsStep/fsDrop; S.ft, S.fb):
  tests/far_trees.lua gives the same result as before the change (3,024 moves with a moment of two layers). The houses
  need it both ways: a streamed house leaving the radius is held in the objects queue until its far tile or block is
  made (bldHold, released to the queue's tail by onMade or after FAR_BLD_HOLD_MS), and an inner tile whose streamed
  houses are not all made (after a jump, a long queue, a fast free camera) shows its far tile until they are (F.fill,
  objects.bldMade). After a jump the objects took every burst and the far queue never ran: far houses get
  FAR_BLD_JUMP_MS in the jump frame and FAR_BLD_BURST_MS of each burst. tests/far_bld.lua: its first run reported 48
  holes at a jump that were the test's own (dropAll removes the old place's houses at once, by design): reset the
  "drawn before" set at a jump.
- The free camera: commands.isFreeCamera, else core_camera.getActiveCamName() == 'free' (BeamNG.Earth core.lua).
  Beyond FREE_AWAY_M (500 m; back at FREE_BACK_M 400) the focus is the camera and the game is paused (the car would be
  left without ground and collision); collision cells and rebuilds stay with the car meanwhile; the game goes on
  FREE_BACK_FRAMES after the car's near rings and cells are made again. A jump's own pause runs as usual inside it
  (pause(false) never unpauses while st.carHold is set). Not tested in the game yet.
- tests/sim_stream.lua FREECAM="x,y,t0,t1[,v]" emulates it (the sim's car time stops while paused, so t0/t1 count
  frames). A release asset being replaced answers 404 for a minute (the base was being uploaded): list the assets again.
- Merging the far sets with the other thread's far-tree fix (9af14dc, FAR_TREES_MIN_MS and its log lines): the fix and
  the log lines now live in the generic far set (fsUpdate/fsStep log "<far trees|far houses> at tile ...", "...: first
  shape ...", farSet "... in stream.json: ..."), and both sets get their <P>_MIN_MS of every stepFar call.
- `local function` defined BELOW its first caller is a nil global at the call (fsCount used by fsUpdate): move it up.
- PC test of the free camera (base 00e48dc, 2026-11-01): no "free camera away" line in the log after a flight far from
  the car. Not explained (the calls are BeamNG.Earth's; a scripted flight leaves followCamera(true) on, which skips
  the free camera logic, and the flight may have stayed within 500 m). freeCamera() now asks commands.isFreeCamera and
  core_camera.getActiveCamName with the player 0 and without, logs "free camera on/off, <m> from the car (<which call>)"
  at every change, and any camera more than FREE_FAR_M (1,500 m, or twice freeCameraAwayM) from the car takes the
  streaming whatever the game reports (tests/sim_stream.lua FREECAM: on, away, off, back in order).
- PC run g6_A of 547c25a: the camera far from the car took the streaming (FREE_FAR_M), but at the level's START too: the
  camera stood where the level put it, 6.2 km from the car at Manno, the first jump went there, paused the game and
  jumped back to the car (a 7.7 s frame); "free camera off, 6161 m from the car" was the first state logged, not an
  inverted word. The camera now takes the streaming only after it has been within FREE_BACK_M of the car since the
  start or the car's last teleport (CAR_JUMP_M in a frame); tests/sim_stream.lua CAMSTART="x,y,s" (the camera elsewhere
  for the first s seconds) shows the first jump going to the car. No call has ever said "free" on the PC: what each one
  answers is logged at every change ("camera calls: ..."), read those lines after a Shift+C test.
- The "light grey patches" of the 547c25a photos from San Salvatore (behind Paradiso, 1-2 km out) were a BAND of tiles
  with no house and no road at all, bare terrain and trees, between the made houses near the camera and the far houses
  beyond the inner radius: compare the same crop over all the runs of a view before blaming a colour (the 15:43 runs had
  the band in one shot and far houses in the next). After a jump the objects queue of Lugano takes minutes, and every
  hold of the far sets ran out after FAR_BLD_HOLD_MS (60 s) whatever was still coming: the far tiles over the town
  (F.fill) went while their houses were queued, and the coarse blocks round the camera went while the fine tiles that
  replace them were still in the far queue (~1 far house tile a burst). tests/far_bld.lua set the hold to 1e9, so it
  never saw it. A hold now counts only from when nothing more is coming: inner tiles while the objects queue has
  objects to make (F.coming), doomed shapes while their own set's queue has shapes to make. far_bld.lua "jump3 (short
  hold)": 249 frames with a hole before, 0 after. Test a timeout with the value the game uses against a slow queue.
- Under such a band the window's paved ground was what showed: the streamed asphalt map is the orthophoto (yards and
  streets as greys up to ~200, not one colour: a statistic over the first 6 blocks of a zone, all outside its towns,
  said "uniform") and the concrete under every house a flat 156. region_base.tone_window_greys tones every light grey
  window base texture (mean over GREY_CAP, low saturation) to farlod.tone_grey's colour (asphalt 133,131,126, concrete
  134,131,125) and takes its map out of baseTextures (the window and the helper take baseFlat, test_helper: same map).
  The paved ground of the window loses the photo's detail (it is under the road and yard meshes once they are made).
- michi 19:07Z: "e le case voglio che si vedono sempre! se mai usa un LOD per le case più lontane però voglio che si
  vedono". The houses ended at FAR_BLD_RADIUS (40 tiles, 15 km) while the far ground went on to the 60 km of view.
  farbld.build_levels adds levels 3-5 (blocks of 8, 16, 32 tiles: 3, 6, 12 km; the houses of each 16, 32, 64 m cell one
  box of their plan area, height and colours) and objects.lua's far set a quadtree over its coarse levels (fsWant,
  fsCover/fsCovered: a block that splits or merges goes once the shapes over its square are made), out to the view
  distance (stream.lua, unless "bldKm" is set). Lugano: +20 MB raw for the 111 MB of b_ + l2. All Ticino (base
  b6348de): level 3 459 blocks (1.8 M triangles), 4 139 (1.0 M), 5 40 (0.4 M), base part 4 233 -> 271 MB zipped.
- The far ground's coarse levels lie far from the 12 m ground under the houses (Lugano: level 5 vs 0 more than 10 m off
  under 29 % of the houses, p99 38 m; level 2 only 0.3 %): boxes at their true heights were 9.5-28 % under 1 m of their
  coarse ground (buried). A house quadtree on its own rings (2 blocks a level) would have stood a level on 3-4 ground
  levels across the presets; splitting a house level k block where the far ground splits level k - 1 (fsSplitD reads
  S.lod.D) puts it on ground k - 1 or k only, in every preset (level 2 on 0 or 2), and farbld.stand keeps the house's
  height over the higher of the two (mean of centre and corners) and its foot under the lower: 0.01-2 % under 1 m.
  Measure what the game draws under a far object (farlod.coarse_heights + drawn_height) before standing it on the DTM.
- First run of tests/far_levels.lua hung (far_bld.lua too, 20,000 frames a move): the cover of a coarse block counted a
  wanted inner fill tile that fsStep then skipped (its streamed houses had come) as missing, so the block waited
  forever. An inner tile's cover is its real things, never its fill shape (fsCovered). Run the old far set tests against
  any rewrite of the far sets: far_bld.lua and far_trees.lua gave the same live counts as before (213/219 fine, 0.51x).
- Then a drive of far_levels.lua stuck at 120,59 with two far tiles over the car's tiles for good (the 60 s hold in the
  game): objects.bldMade answered nil for a tile no longer in the tile cache (S.tiles keeps the CACHE_TILES 400 last
  read, first in first out), so its far tile never saw its houses made. Older than the levels (the old test's map was
  too small to evict anything); bldMade reads such a tile again. A cache that can forget must never be the only record
  of what is live.
- And after a jump its level check found level 3 and 4 blocks 66 tiles from the car (R 60): the band beyond the radius
  (kept for a car going back and forth) kept any shape of the old place that fell in it. A shape stays in the band only
  if it is of the level the quadtree would draw there (fsLeaf).

## White patches and lines on the lake from above (PC photos from San Salvatore, 2026-11-01)

- The light grey / white patches "like rock or snow" on the plain and the slopes from ~1 km out were the combined base
  colour map of the terrain window (stream.lua combinedRows, BASE_COMBINED): each pixel took the streamed map of the
  material under it, and the materials WITHOUT a streamed map (base texture under 2048: ForestFloor*, Bank*, Concrete
  and their twins, 61 % of the ground of ti_0_0) took the first one, t_base_asphalt_b, light grey (166). The near
  ground looked right (detail textures), the base colour shows from the detail distance on. The far tiles' colours were
  right (dark forest). Now stream.json baseFlat (blocks.base_flat: the mean of each material's window base texture)
  gives those pixels their own colour, in the Lua and the helper (tests/test_helper.py: .ter and map identical).
  Seen in a render of the map before guessing: decode a window's combined map from the blocks (scratch combined.py).
- tests/test_helper.py had been failing since the csv files became opt-in ("diagnostics"): the sim never wrote
  ticino_perf_sim.csv. sim_stream.lua now sets stream.DIAG (DIAG=0 turns it off).
- The straight light and dark lines across the lake: every zone lays its lake with WaterBlocks on its OWN 25 m lattice
  (water.py: rectangles of 25 m cells, gridElementSize 25, reaching far under higher ground) at its OWN level (median of
  its DTM over the lake: Lugano 270.477-270.482), and region.clip_box cut them at the zone cores into sizes that are no
  whole cells, side by side with blocks of other lattices and levels. In the Malcantone level (one lattice, one level)
  no line was ever seen. region.unify_water (region_base, before write_scene) lays every lake again on ONE lattice
  (the offset of a zone's own blocks that leaves the fewest cells to decide; a lake inside one zone keeps its blocks)
  at one level: a cut cell is water when half covered, always when the far ground in its covered part is under the
  lake (the carved bed must stay wet), never when the far ground in its uncovered part is 0.5 m under the lake (a
  river below a weir, the foot of a dam: water.py's forbidden cells). Region of 87 zones: 52 lakes, 335 -> 300 blocks,
  Lugano 52 -> 34 on one lattice, 459.4 -> 460.0 km2, 4 cells both wet and dry (keep the zones' own pieces). With the
  plain world lattice (0, 0) 318 cells were both (dams of the alpine lakes): pick the lattice per lake.
  The base zips also gave every block the name LagoDiLugano_NN of its zone (duplicate names in one scene): now
  Lake<level>_NNN. Not seen in the game yet: if lines stay, look at the window edge and the far tiles under the water.
- With baseFlat the window was right, but the PC photos with the far trees off (2026-11-01) still had pale patches "like
  rock or snow" on the villages 2-6 km out (Collina d'Oro): the FAR ground's colours. Under every building its terrain
  layer is Concrete at the fixed 156,154,148, and one 12 m vertex on a footprint spread that grey over the squares round
  it; the orthophoto maps of the open ground carry the roofs, streets and yards as greys up to 200 (17 % of the far
  ground of the Collina d'Oro was a grey over 130). farlod.fill_buildings (region_base, after worldmap so the M map
  keeps the footprints) gives the footprints the nearest other ground's colour (the far houses stand there) and tones
  greys over GREY_CAP (130) down, half way to a warm grey (scaled alone, the faint casts of 200,195,197 made the towns
  mauve); the mountains' rock (133,133,121) stays. Over all Ticino: 183,119 samples filled, 1,100,428 toned. Checked in
  the ray-cast render of the far ground (scratch view/shade.py), not in the game yet.

## Switzerland Builder (branch switzerland-builder, beamng/builder, 2026-11-07)

- 2026-11-12 the branch moved to its own repo wintrymichi/switzerlandNG (main, full history). The first push copied the
  code only: the installers, app/update.py, the README download links and the workflows' branch triggers still named
  magliasinaNG/switzerland-builder, and michi's download gave the old version. When code moves to another repo or
  branch, grep for the old owner/repo AND branch name (update.py, launch/install.*, README, workflows) in the same push.
  Installs made before the move still poll magliasinaNG/switzerland-builder: they reach the new repo only if that
  branch gets one last commit with the new OWNER_REPO.

michi: a localhost app that builds any part of Switzerland from open data, click and run, detail at least the
Malcantone's, tunnels and galleries done well. The app (beamng/builder) writes a zone file with "builder": true and runs
the pipeline's own zone build (downloads, stages, finishing steps), then recenter.py, the zip and the mods folder.

- The branch was started from ticino WITHOUT the Ticino/Malcantone workflows: the first push of a branch starts every
  workflow whose push paths its commits touch (zone_build.yml ran by mistake once). Only builder_*.yml live here.
- The cloud cannot dispatch a workflow off the default branch: builder_test.yml runs on a push that changes
  beamng/builder/test/stamp.txt. "[builder finish <run>]" = finishing steps only on that run's build artifact (kept 3
  days) with the new code (cli resume --update-code); "[builder windows]" = the Windows job; "[builder area <name>]" =
  test/<name>.json instead of area.json (logs test_<name>_part1/2). Concurrency: all finish runs share one group (a new
  "[builder finish]" push CANCELS a running finish run), plain stamp pushes share another, every area run has its own
  (its sha). Check actions/runs?branch=switzerland-builder after every push.
- Malcantone values hard-coded in the pipeline, found by the first builder areas:
  water.lake_level returned 270.5 (Lake Lugano) when no lake was surveyed, and every caller took ground at 270-272 m
  for lake (network.dry_ends dropped the dead-end roads of a flat valley at that height, forest_fill its trees, the
  backdrop drew water): now None. download_swisstopo had the Copernicus tiles N45-46 E008-009 written in: now the
  1x1 degree tiles within 25 km of the block. download_gwr read ti.zip only: MAGLIASO_GWR_CANTONS. info.json had the
  Malcantone's title: the zone's title and sources. The spawns were spawn_magliaso/mid/pura in every zone (Sisikon's
  info.json, read by HTTP range from the zip): builder zones name them after the nearest swissNAMES3D place of 20+
  people within 2.5 km (fuel_stations.village_of reads the new names).
- Guard rails: every zone had rails only on the motorways (0.2 km on the Axenstrasse, a cliff road over the lake): the
  Malcantone's came from its panoramas. guardrail_mesh.drop_marks / drop_runs (zones only) put them where the ground
  falls 2 m (3 m beside a 3 m road) and 1:2 within 6 m of the edge, plus OSM barrier=guard_rail, not beside paved faces,
  parapets, buildings or in villages. First version: closing gaps of 10 m bridged a station left out for a yard, and
  to_edge then pushed the rail across the yard: never close a gap over a blocked station. Its synthetic test: bng.write_dae
  subtracts the origin itself (the test subtracted it twice), and a test road of two huge triangles was dropped by
  edge_fn's centroid filter (make synthetic roads of small faces).
  The first Axenstrasse build with them: 97 % of the 3,037 modules stood within 1.5 m of a road's height, on the side
  where the ground falls. 45 stood 10 m under a road climbing a ramp (Sisikon, road as built 462-468 m, the DTM under
  it 455 m): drop_marks takes a rail's height from the DTM across the carriageway, network_surface builds the road on
  a smoothed line that rejects such DTM data, and to_edge, finding no road face within 1.5 m of the rail's height,
  left the rail at the DTM's. guardrail_mesh.edge_drops cuts the stretches over 6 m with no face at the rail's height.
  Check rails against the road heights (scratch rails_side.py: ground beyond the rail and the nearest road's z), not
  only in plan.
- Floating guard rails (michi 2026-11-07: "controlla anche che i guardrail non siano volanti"): on that build 28 % of the
  3,037 modules had a post more than 0.3 m over whatever was under it, 11 % over 1 m, a few over 20 m. Measured per post
  foot (two per module, one per end piece, from the models' local x, y) against the terrain's higher split and every up
  face of the level (scratch rails_float.py). to_edge puts a rail 0.3 m beyond the road's edge, where the carve and the
  1.5 m terrain grid let the ground fall away from 1-2 m inside the edge, and paved_edges kept the 2 m round every rail
  out (KEEP_GROUPS), so the embankment that fills a road's edge everywhere else was never raised under the rails. In a
  zone the rails are no longer in the keep-out (they are laid by rule, not measured), and the finishing step rail_walls
  (after tunnels: the ground is final then) stands what still hangs on a concrete edge beam on a wall down into the
  ground; over a fall deeper than BEAM_MAX (8 m) only the beam, listed as too_deep (a road over a gorge with no
  swissTLM3D bridge). On the old level: 897 modules over 0.25 m -> 0, 2.45 km of wall, 62 s. Its first version left 275
  hanging: deep stations got no beam at all, the end pieces' feet lay beyond the chain's ends (the wall now runs 2 m
  past them) and a post was "held" when its gap after the wall was small, which its own beam's face fooled: held is
  now every foot inside a beam's footprint. In concrete the wall stood 0.4-0.8 m in front of the survey's stone walls
  the rails hung over and hid them: beside the top of a survey stone wall the beam and its wall are stone too
  (stone_runs). The DAE material symbols are "<name>-mat": a test of tunnels.dae_triangles' material against
  "mp_wall_stone" found nothing (stone_m 0) until the suffix was taken off.
  Full build with paved_edges and rail_walls (run 42419181586, concrete only): 3,220 rail items, none over 0.25 m, 853
  held on 2.25 km of wall, 7 too_deep; paved_edges raised 301,246 vertices (edges over 0.15 m 79 % -> 11 %), but
  25.6 % of the modules still hung before rail_walls: the rails stand where paved_edges cannot raise the ground.
- Asphalt climbing the rock faces of the Axenstrasse (renders of the rails): 3,718 paved faces over 3 m tall and steep
  (mp_road_asphalt 1,188, mp_hard_bank 916, mp_sidewalk 787, mp_hard_asphalt 737), found by listing the steep faces of
  roads/surfaces and clustering them (scratch steep_paved.py), then the faces by shape, material and height band at each
  cluster. Two causes. (1) Rock overhangs: under an overhang swissALTI3D is the rock above the road, and network_mesh's
  floor (no cell more than SUNK under the lowest DTM within 1 m) lifted the carriageway's edge up the rock in a vertical
  notch. In a zone the cells on a line (within its half width, not past its ends) take the lowest DTM within
  OVERHANG_REACH (4 m), the valley side of the road, in tile_surface and in mesh_tile's vertex floor. (2) Galleries:
  network.SKIP drops the swissTLM3D Galerie LINES, but the survey's road polygons under a gallery were still meshed on the
  DTM, which there is the roof and the slope over it; tunnels.cut_meshes cuts roads only inside a tube's volume
  (over_gallery, the cut in plan, is for the skin, walls and fences). network_mesh.gallery_footprints (half width +
  GALLERY_CLEAR) are holes of the survey polygons now, like the bridge decks, and the slivers left beside them go.
  Neither can be tried locally (no swissTLM3D in the cloud's DATA, gallery_footprints is empty there): only a build.
  The build with both (run 42419181586): 2,721 steep paved faces left, over 20 m 85 -> 18, carriageway 1,188 -> 502.
  1,774 of them stood within 30 m of a tunnel or gallery mesh (counted against the vertices of the level's tunnels
  shapes): thin asphalt spikes 10-20 m up the rock beside the portals, single vertices and small groups at the
  carriageway's edge (top vertices at 0.93-0.99 of the AI road's half width). A render with roads/surfaces emptied (a
  cp -al copy with an empty items.level.json) tells them from the terrain: the big smooth grey sheets of the "after"
  views were the bare cliff (terrain), not asphalt. Third try (network_mesh OVERHANG_DZ): a cell of a line that runs
  more than 2 m under the DTM within 15 m along it is never lifted onto the ground, and a vertex takes the floor of the
  nearest paved cell (a polygon's edge vertex lies in a cell outside it, which kept the old 1 m floor: the rock).
  Away from the tunnels 947 faces are left, 39 over 8 m: steep yards (mp_hard_bank) and sidewalks on the DTM.
  Third build (run 42426108736): steep carriageway faces 502 -> 372 (the worst portal 188 -> 62), but steep yard faces
  451 -> 569 and a new 10 m grey wall at Sisikon (-375,2725 in the zip): a yard between a road and another road 5-9 m
  above it (edges 0-2 m apart). The DTM over the lower road is the upper road's embankment, so the lower road was taken
  for a road under rock, the yard cells beside it kept its height and the yard's harmonic fill ran from them up to the
  terrace. A rule that holds cells "under the ground" must tell rock from another road's embankment, and must not hold
  a polygon that only borders the line (yards, sidewalks: their own lift was right). Now only the survey's carriageway
  is held, and a station is no overhang where another line (not a path) stands over it with its edge within ABOVE_GAP
  (4 m) of the station's edge. Compare a fix per material AND per 50 m cell against the build before it: the total
  (2,721 -> 2,742) hid a gain on the carriageway and a loss on the yards.
  Fourth build (run 42431521109): 2,686 steep paved faces (carriageway 352, yards 478 + banks 908, faces over 12 m
  138 -> 72 against the second build), the Sisikon wall gone, the portal fix kept. A match of every paved vertex of the
  second and fourth builds by xy and material (scratch vdiff_all.py: 697k vertices) found 81 moved down over 2 m (the
  spikes) but 20 moved UP over 2 m, up to 7.4 m: a pavement's edge vertex beside a portal took the floor of the cell it
  lies in, and on a cliff that cell is often another polygon's on the terrace above. The nearest cell's floor may now
  only lower a vertex's own floor (np.fmin). Count vertices that moved both ways between two builds, not only faces:
  a few new spikes hide in a total that went down.
  Fifth build (run 42436145298): 2,531 steep paved faces (carriageway 308, faces over 12 m 70), against the second
  build 81 vertices down over 2 m and 12 up over 2 m, all 12 at one portal where they were already 10 m spikes. Rails:
  0 posts over 0.3 m, 853 held on 2.25 km of wall (1.34 km stone), 7 too_deep. The portal and Sisikon renders clean.
  Most of what is left is the OLD Axenstrasse: a road cut into the cliff with tunnels and galleries of its own, now a
  footpath, which swissTLM3D gives as "2m Weg" / "3m Strasse" (tubes and galleries built that narrow) while the survey's
  carriageway is the old 6-7 m road: strips of it beside a gallery climbed its roof (up to 20 m), and the hold under the
  rock reached only OFF_LINE half widths (1.5 m) from a path's axis. A probe of the steep faces against the AI roads
  must read the tunnels group too (tunnels.py writes the tunnel_* DecalRoads there, not in AIRoads): without it every
  face at a portal looked "far from any road".
  Sixth build (run 42440861766: galleries cut at least GALLERY_HW_MIN 3.5 m + GALLERY_CLEAR from their line, a narrow
  line's cells held PATH_HOLD 3.5 m from its axis): 2,357 steep paved faces (yards 451 -> 328: the yards over the old
  road's galleries went), carriageway 308 -> 316, faces over 12 m 70 -> 72; 13 vertices at the old road's portals came
  down 2-15 m, none went up over 2 m; rails unchanged. Two cells got taller faces, both at portals of narrow lines
  (1875,175: 2 -> 12 faces, up to 7.8 m; at -1872,-3002 a 15.4 m needle whose neighbours came down): a vertex match does
  not see them (the wider cut makes new vertices), only the faces per cell and the renders do. The terrain moves with
  the paved faces (6,269 vertices over 0.5 m between builds 5 and 6, up to 26 m where a yard over a gallery went and
  its carve with it): compare the .ter of two builds too. Left at the old road's portals: survey cells past the end of
  the path's line (E > 1) or beyond PATH_HOLD are filled from the DTM, which there is the rock over the tunnel. Next
  step, not tried: tubes as wide as the survey's road at their portals and an approach cut over the crown. The scratch
  vertex match keyed (x, y in cm) * 1e5 + material in int64, which overflows beyond |x| ~ 920 m: the material read as
  "other" there (the match itself held).
- The reports of a build are in pipeline coordinates, the zip's level is moved by recenter.py (levels/<name>/recenter.json
  dx, dy; Axenstrasse +21234, -106065): add them before looking a reported point up in the zip.
- The Malcantone's own data were built in EVERY zone at the Malcantone's coordinates, 100 km off a builder level, at
  the height of the nearest edge of the zone's DTM (1,383 m on the Axenstrasse): the panorama fences (fences.build: 46
  fences in 16 chunks and 27 guard rail modules), the edifici_veri sites (68 m of fence), the roadside walls of the
  cantonale (walls.build_roadside: 6 shapes whose vertices were all NaN, because roadheight is empty in a zone) and the
  understory hedges, street-photo hedges and photo shrubs (vegetation.py: about 7,000 forest items). The Ticino region
  hid it (its slices clip everything to the zone cores). Found by listing every object, forest item and shape vertex box
  of a built zip outside its terrain block (scratch scene_bounds.py, dae_bounds.py; the shapes' position arrays are
  "g-pa", "g1-pa"...); all now dropped by area.in_zone. The NaN roadside walls are also the likely source of the 909
  NaN terrain heights of ti_0_m1 ("terrain post 0"): adjust_terrain_roadside lowered and raised vertices to NaN feet
  and tops. build_roadside takes np.fmin/fmax with the empty road height now (the measured foot and top).
  After a build of a new area, list what lies outside its terrain block before anything else.
- Cantons without an open survey on geodienste.ch (probe 2026-11-07, builder_probe.yml): LU, OW, NW, VD, VS, NE, JU;
  every open canton answers av_0/ita in the Italian vocabulary the pipeline reads. In a closed canton the land cover
  raster was 'none' everywhere, which the pipeline reads as "not Switzerland": no measured trees, no lake, no rivers, no
  OSM furniture. landcover.tlm_cover lays swissTLM3D TLM_BODENBEDECKUNG where the survey has nothing and ESA WorldCover
  on the rest of the Swiss land (WorldCover's water, code 80, as meadow on purpose: swissTLM3D decides the water).
- HTTP 403 from geodienste.ch on an OPEN canton (a user's log, 2026-11-13: av_0/ita LCSF, a 1 km box in Aargau) is
  not a closed survey: the same URL answered 200 with features from michi's PC. geodienste.ch/terms-of-use: bots with
  high request rates are not allowed and access "can be restricted or refused" for excessive use; offline use should
  take the STAC / export API instead. The builder sent up to 4 layers x every 1 km box back to back, retried a 403
  once and the job runner reran the failed download step: the ban got longer. download_av now waits PAUSE (1 s)
  between requests and on a 403 builds without the survey (empty layers + data/av/BLOCKED.txt, retried next build).
  netio.DownloadError carries the HTTP status. The error in a netio DownloadError is cut at 300 characters (the user's
  line was exactly 300, COUNT and STARTINDEX cut off): do not read the request's parameters from it. Not done: the STAC
  fallback (geodienste.ch/stac, collection av: one INTERLIS .itf per municipality, a GeoPackage per canton, AG
  351 MB zip), which needs a DM01 reader with the German/French attribute names.
- The 2026-02 swissTLM3D package splits big layers in two (TLM_BB\swissTLM3D_TLM_BODENBEDECKUNG_OST/_WEST.shp, also
  EINZELBAUM and GEBAEUDE_FOOTPRINT): download_tlm looked for one file, logged "not in the package", and the Vitznau
  and Montreux builds had no swissTLM3D land cover and no lake (water.lake_level measures the specchio_acqua cells). It
  now reads <layer>, <layer>_OST and <layer>_WEST. Read the package's file list in the log before calling a layer missing.
- No river had water on the Axenstrasse (rivers: surveyed 37, 6.5 ha -> polygons 0), Vitznau kept 1 of 12: rivers.surfaces
  cuts the rivers with the lake's WaterBlocks, and the blocks are rectangles that may reach kilometres over land higher
  than the lake (6 blocks over 202 km2 for 34 km2 of lake; Montreux one block of 155 km2). In the Malcantone the low
  Tresa valley kept them small. In a zone the rivers stop at the lake's own cells + one cell (water.lake_shapes).
  Read the "rivers: {...}" line of a build log: "polygons" is what got water.
- Python environment (micromamba, conda-forge, environment.yml): exact pins of rasterio and pyogrio did not solve
  together (one GDAL): pin numpy/scipy/shapely/scikit-image minors only. conda-forge's pyogrio has no pyogrio.libs, where
  ogr_tin looked for GDAL: extract_buildings stopped on Windows; it now looks in the environment's prefix too. A
  micromamba source can be blocked (the cloud proxy refused one): the launchers try GitHub's release, micro.mamba.pm,
  then a pinned conda-forge build. conda packages break on spaces and accents in their path: the runtime moves to
  %SystemDrive%\SwissBuilder\runtime or ~/.swissbuilder/runtime then.
- Windows: no "fork" context (stage_roads: ValueError cannot find context for 'fork'): one process there; finish steps
  run without the forked child. Steps started with CREATE_NO_WINDOW ran on alone after the app's console was closed:
  they share the console now (own process group, so Ctrl+C reaches only the app). start.ps1 must not have a param()
  block: an advanced script refuses "--no-browser" as an unknown parameter; it reads $args.
- cli --until first cancelled the next step once it had started (a race): the Manager stops after the named step.
- The app's first time estimate (1.2 + 0.065 h per km2) came from the dense Lugano zone: Sisikon (32.8 km2 of mountains
  and lake) took 38 min against 3.3 h (its first build, 2026-11-07; by the sixth, 2026-11-08, the same area took 60.6
  min of steps, 70 min on GitHub with the hand-over between the two jobs: paved_edges and rail_walls in zones, the
  gallery cuts. A build time is worth only as much as the run it names). The build time follows the buildings and roads, not the area, and the app cannot
  know them before the downloads: it now shows a range, 0.25 + 0.012 h/km2 (Sisikon, Vitznau) to 0.4 + 0.07 h/km2 (the
  Lugano zone); Montreux, a town of 8.7 km2, took 31 min with the swissTLM3D land cover (36 min before it, with none).
- wmts.geo.admin.ch and api3.geo.admin.ch are blocked from the cloud: the app's map tiles and search cannot be seen or
  screenshotted here (the page renders with a grey map); they work on a user's PC.
- far_trees prints "<kept> of <measured> ... left out by the thinning": the first number is what stays (not a bug).

Tunnels and galleries (tunnels.py, finishing step; tested on ti_m1_8 San Bernardino and the Axenstrasse build):
- Galleries (swissTLM3D KUNSTBAUTE Galerie, the avalanche galleries) were closed tubes, and the old mound then raised
  the valley side over them (ti_m1_8: 13,782 vertices, up to 8 m, mean 1.88 m): buried. Now gallery(): hill wall, roof
  slab, pillars on a parapet, foundation wall; valley_clear keeps the ground under the parapet. railway.py built rail
  galleries itself too (double): Galerie is left to tunnels.py (railway SKIP).
- A tube running out of the terrain block (San Bernardino) hung in the void: it is cut at the terrain's edge and closed.
- Renders of the galleries showed: a sky-coloured band over the roofs (the terrain kept over the roof stopped ~1 m above
  it: fill cap at max(ground, roof + 0.02)); rock ramps in the gallery openings (hole squares at a gallery end capped on
  the DTM's smear of the roof, 2-5.5 m: end_clear); skin "curtains" and survey stone walls on the roofs (cut in plan over
  the footprint, over_gallery); ground up to 0.25 m over a road deck not holed (DECK_CLEAR); a faceted vault (12 flat
  segments: normals follow the curve); escape-sign text over the running man at 54 px (the font fits the room).
  The cap drew 72 triangles per square: a square drawn whole is 2 now (-25 % cap triangles, same look).
- Checking tunnels in render3d: it drew terrain holes as grey ground (Level.holes added); textured materials use flat
  normals (computeVertexNormals), so a smooth vault shows only with textured=False, dae_normals=True; the grey cone is
  render3d's proxy of a game model, not a mesh of ours; find which group owns a mesh by rendering without that group
  (Level.statics items are (group, shape, pos, frame) tuples: a script that unpacked them as (shape, pos) failed). The
  scratch harness filled the old mound with a Laplace fill that made spikes the build does not have: judge spikes on a
  real build. Playwright: pip install in the builder environment (with timeout); three.js from the npm tarball.
- Views of cliff roads in render3d: the coarse far terrain (step > 1, lowered only 1 m) stood in front of the camera and
  hid the road below it: monkeypatch Renderer._terrain to lower it 60 m (scratch rails_render.py). Cameras placed
  "16 m out on the valley side" ended inside the cliff: take their height from tunnels.Terrain and never under the
  rail - 2 m. render3d draws the guard rails (render3d_models) also with trees=False.

Test builds (draft release builder-test, GitHub runners of 4 cores, from the launcher to the zip): Axenstrasse and
Sisikon 32.8 km2 in 38 min on 2026-11-07 and 60.6 min of steps on 2026-11-08 (run 42440861766, 70 min of wall time;
the earlier "38 min" in these notes was the first build, before paved_edges, rail_walls and the gallery cuts), zip
0.86 GB (44 tunnels and galleries, 22.4 km); Sisikon 0.9 km2 on Windows in 18 min.

Faster builds (switzerlandNG, thread "Velocizzare la creazione delle mappe", 2026-11-09; plan: the Claude Doc of
"Pianificare switzerlandNG più veloce"):
- What a build spent (build.json of run 42440861766, Axenstrasse 60.6 min of steps): downloads 14.6 min one after the
  other (OpenStreetMap 9.1: one connection to Geofabrik), stages 10.1, finishing steps 29.8 (steep_skin 8.7 on one
  core, tunnels 3.1, unpaved 2.2, paved_edges 2.1, forest_mosaic 1.9), zip 2.8 on one core. Fixed costs paid by every
  build however small: the buildings' procedural textures 110 s (bld_textures.build, the same files every time), the
  skin's textures 31 s twice (steep_skin and skin_blend), the 12.3 km terrain block for a 1 km area.
- system.workers took 16 GB as "low" (PATCH_WORKERS 1): every GitHub test build ran unpaved and paved_edges on one
  worker though the Axenstrasse's finishing steps used 2-5 GB. Read the [mem] lines of the job log before choosing
  workers by memory.
- Done: the downloads and the steps that need only swisstopo's files side by side (jobs.EARLY, each step's log in
  logs/<key>.log, put into build.log when it ends); the finishing steps in one build_level.py --finish process
  (FINISH_CHAIN, not on Windows), its progress read from its "== finish:" and "[finish ...]" lines; steep_skin's and
  skin_grass's tiles in forked workers (tilepool.py, TILE_WORKERS); the zip deflated in threads (package.py,
  ZIP_WORKERS); OpenStreetMap in 4 byte ranges and the municipal boundaries kept beside the extract; swissTLM3D in 8 MB
  ranges read ahead, its layers side by side and its members kept in data/tlm_pkg; the textures kept between builds
  (texcache.py, MAGLIASO_TEXTURE_CACHE); a 4096 terrain block (6.1 km) for areas up to 2.1 km a side (zone.TER_MARGIN
  2 km, as the biggest area had). Not done: parallel lanes of finishing steps (plan measure 5): the steps read and
  rewrite the same .ter and level files one after the other, and with the pools the finishing steps of the small
  Sisikon took 3 min in all.
- Every pool must give the level of one process: steep_skin and skin_grass were run old (git archive HEAD) and new on
  two cp -al copies of the released Axenstrasse level and compared file by file with the uuids masked (cmpdirs): 0
  files differ; the zip is compared by entry sizes, CRCs and offsets (the dates are the packaging time). A step's
  report is merged in tile order (tilepool.merge_report: "max" keys take the larger value), so it matches too.
- The first round with the downloads side by side lost what it won: swissTLM3D took 583 s (84 s alone the day before)
  because download_tlm read the package with one 4 MB range request after the other, a new connection each, and the
  small area's landcover waited for it. A step that streams a remote file must read ahead in parallel, not only the
  big downloads. And a cached file needs the cache folder in app/cache.py SHARED, or the next build downloads it again.
- download_osm.fetch_big: the HEAD request's final address (a redirect to a signed S3 URL) answered 401 to GET: send
  the GETs to the original URL. Geofabrik is blocked in the cloud: the range download was checked against a local
  HTTP server that answers ranges (scratch srv.py), byte for byte.
- Scratch mistakes of this thread: a text replacement meant for main() matched the same lines in the new function
  written just above it and replaced the wrong block (locate the function first, then replace inside it); a git
  stash ran while a background job used the working tree (it worked, but run the old code from a git archive copy
  instead); `cd dir && rm -rf *` was refused by the safety check (use absolute paths). forest_mosaic and tunnels do
  nothing on a released level (already done there): profile them only in a build.
- Measured after (wall time from the first step to the zip, two GitHub jobs): Axenstrasse 66.6 -> 41.4 min (run
  42680459047) and 45.4 min (run 42687155488: the same code, steep_skin 170 -> 232 s and tunnels 113 -> 184 s on
  another runner: GitHub's runners differ by up to 50 % a step, compare two runs before calling a change slower);
  downloads 5.2 min, stages 11, finishing steps 16-22. Sisikon 0.9 km2: Windows 17.6 -> 13.7 min, Linux 14.7 min.
  The Axen zip of the new code differed from the 2026-11-08 zip in 11 building/prop files and 3 new house_pv files,
  terrain and skin identical: newer daily data (GWR, OSM), not the pools. Left the biggest: stages (buildings_mesh),
  tunnels, forest_mosaic (whole-block rasters), landcover.

### Builds that never hang, downloads with a percentage (thread "Rendere la costruzione mappe a prova di blocco", 2026-11-09)

- multiprocessing.Pool waits FOR EVER when one worker dies (OOM killer, SIGKILL): the task is lost and the Pool only
  starts a new worker (reproduced by the reviewer thread; the 2026-10-17 "optimize deadlock" above). tilepool.py,
  build_level's NET_WORKERS and optimize_level used it. Now all go through tilepool.pmap (ProcessPoolExecutor, fork;
  spawn with pickled=True on Windows): a dead worker is BrokenProcessPool, and the items left run again with half
  the workers, down to the step's own process. Note: ex.submit() itself raises BrokenProcessPool once a worker died
  (first test crashed there, not in result()). Workers alive but idle (a lock inherited across fork) count as broken
  after MAGLIASO_POOL_STALL s (900) with no result and < 2 s CPU (psutil, else /proc).
- jobs.py had no limit on any wait. Watch: a step is hung when for SWISSBUILDER_STALL_MIN (20) min its log has not
  grown and its process tree used no CPU (> 0.5 s per 30 s) and no disk (> 1 MB): SIGUSR1 to its group first
  (config.py registers faulthandler: the stacks of every thread go to the log), then killed, then run again
  (SWISSBUILDER_STEP_RETRIES 2). The downloads run again after ANY failure (they keep their finished files). A hang
  re-runs a finishing step from its start: the same as the user's "resume", but a step that is not idempotent (see
  sidewalks, skin_grass) may see its own half-written output.
- Steps now start in a process group of their own (start_new_session / CREATE_NEW_PROCESS_GROUP) and kill_tree also
  kills the group (os.killpg): when build_level.py was OOM-killed its forked workers ran on, held their memory and the
  stdout pipe, and run_finish_chain's `for line in p.stdout` waited until they ended. The chain now writes to
  logs/finish_chain.log, which is tailed. A group does not get Ctrl+C or SIGHUP from the terminal: the app and the cli
  stop the steps themselves (Manager.shutdown, stop_on_signals) and build.json keeps the pids, so a start after a
  hard kill stops the old ones (kill_stale). server.py's old `manager.current[1].pid` raised AttributeError while the
  downloads ran side by side (a list) and left them running.
- download_swisstopo.stac_items looped for ever when a later STAC page failed 5 times (the stale page's "next" was the
  failed page again, its features added each time); download_av paged for ever if a server ignores STARTINDEX;
  swisstopo exited 0 with files FAILED and osmium then failed on a missing pbf. All fixed (raise / stop / exit 1).
- requests' timeout is per socket read: a server that sends a byte a minute never trips it. netio.py (every download
  of the build) has a watchdog thread that shuts the socket of a transfer under 4 KB/s over 120 s (shutdown() wakes
  the blocked recv; resp.close() from another thread does not), then resumes it with a Range request. GDAL /vsicurl/
  has no timeout by default: GDAL_HTTP_* in jobs.env and download_worldcover. Launchers: curl --speed-limit 1024
  --speed-time 60, wget --timeout, Invoke-WebRequest -TimeoutSec, PIP_DEFAULT_TIMEOUT, micromamba without -q.
- Progress lines: "[download] <step>: 45 % (12 of 30 files, 0.84 of 1.9 GB, 6.2 MB/s)" every 10 s (netio.EVERY), and
  one per file of 16 MB or more. Percent of a step whose sizes are not all known yet is marked "~" (the mean size of
  the known ones stands in). The swissTLM3D total is the compressed size of the members it reads.
- A test server that sends past the end of a byte range made get_range write the range 3x too long: ranges are cut at
  their end now (real servers honour it, but a proxy may not).
- Review 2 of the reviewer thread found what the first round missed:
  pmap's stall test compared the CPU since the LAST RESULT, so a worker that computed more than 2 s and then
  deadlocked was never flagged: the first stall check was cumulative, found by the reviewer thread with a test
  (a worker burning 8 s of CPU, then blocking on a lock: it hung until `timeout` killed it). The window now rolls: the clock restarts
  whenever the workers used 2 s of CPU. A test of a stall must deadlock only in the CHILD (os.getpid() != parent): the
  serial fallback runs the same function in the main process and a test that deadlocks everywhere hangs there too.
  A retry after a hang reran steps that are not idempotent (skin_grass, sidewalks, road_seams, steep_skin...): a hung
  step now runs again only if it is not in jobs.NOT_REPEATABLE and wrote no file into the level or WORK since it
  started (LevelWriter writes at the end, so a step stopped while computing has written none), with half the workers
  per earlier hang (swap thrashing looks like a hang). recenter wrote its marker at the END: a kill half way and any
  rerun moved the first files twice; it keeps recenter.journal now (one line a file moved, fsynced) and goes on.
  netio.fetch resumed any old .part: the caches outlive builds and the pbf / GWR zip change daily, and a 416 on a part
  longer than today's file was taken as "complete". A part is resumed only with its <dest>.part.json (If-Range with the
  ETag or Last-Modified, a 206 must start at the part's end and keep the total) and every download asks for
  Accept-Encoding: identity (a gzipped answer decoded by requests never matches Content-Length). Before forking a new
  pool after a break, join the old executor's manager thread (a fork beside a live thread can inherit a held lock).
  Without psutil the step watchdog is off (it would see 0 CPU and kill a long silent computation).
  The test builds of that round (f0d038c, 074a0e6) were green but the swissTLM3D line said "2.0 GB of 1.7 GB": the
  range reads (read-ahead, the zip's directory) went into the percentage while the total was the members' compressed
  size. The percentage now counts each member's compressed bytes as it is unpacked; count a total and its progress
  from the same thing.

## switzerlandNG updates (app/update.py, launch/install.*, 2026-11-10)

- Until 2026-11-10 the builder had no update path at all: the README link was the branch zip (always the newest, but a
  user had to unpack it again by hand) and VERSION was a fixed "1.0.0". Now `.switzerlandng.json` (commit) and
  `.switzerlandng-files.txt` (file list) at the top of an install say what it has; app/update.py takes only the files
  GitHub's compare lists (each checked against its git blob sha1), the whole codeload archive when the commit is not
  known or the compare lists 300+ files. Delete only files in the old file list: a data folder may be put inside.
- The cloud container has GITHUB_TOKEN set: urllib sent it as Bearer to raw.githubusercontent.com, which answered 404
  to every file (curl without the token: 200). It looked like the CDN lagging after a push and cost a retry loop and
  ~5 min of a test. Send a token only to api.github.com; compare curl and Python with the SAME headers before blaming
  the server.
- cmd reads a running .bat line by line at byte offsets: an update rewriting "Start Switzerland Builder.bat" while it
  runs would make cmd go on in the middle of the new file. The .bat files are one parenthesised block (parsed at once;
  `if errorlevel 1` instead of %errorlevel%, which a block expands at parse time). bash keeps the old inode open when
  a script is replaced with os.replace (never write a running .sh in place).
- The page's "Update and restart" ends the server with exit code 75 (update.RESTART_CODE); start.sh/start.ps1 then
  run the NEW launcher (env hash -> the libraries again if environment.yml changed). Refused while a build runs or
  waits. Tested in the cloud: delta from 629949c (13 files, result = git archive of the new commit, CRLF and exec bits
  right), full archive from an unknown version (349 MB, a stale listed file removed), install.sh 21 s, the server
  path to exit 75. Windows: builder_update_test.yml (beamng/builder/test/update_stamp.txt).

## main is the Malcantone only (2026-11-07)

- PR #113 (switzerland-builder, which carries the whole `ticino` branch) was merged into main by mistake: 324 files,
  the Ticino and builder code, and it DELETED every Malcantone workflow of main (nightly_build, v3_build_test,
  release_*, pages...) and replaced the README. michi: "lasciare il malcantone nel main". Undone by a revert of the
  merge (`git revert -m 1 2f8b257`, PR from claude/project-thread-nc6c38), no force-push: main's tree is again the one
  of 33dc6d2 (v3.1.1). The Ticino work stays on `ticino` and `switzerland-builder` (untouched by the revert).
- Ticino and builder PRs go against `ticino` / `switzerland-builder`, never main: check a PR's base before merging.
- Git now counts those commits as merged into main. If they ever must go into main for real, revert the REVERT commit
  first; a plain merge of switzerland-builder would bring in only its newer commits.
