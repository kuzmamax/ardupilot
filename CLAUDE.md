# ArduPilot working tree — notes for future sessions

This is `kuzmamax/ardupilot`, a working mirror of upstream ArduPilot (`ArduPilot/ardupilot`
@ `master`, commit `ff37fde`), pushed here because it's too large to live inside
`kuzmamax/desktop-tutorial`. Sibling repo `kuzmamax/desktop-tutorial` has the
`ardupilot-embedded-drone-engineer` skill (`.claude/skills/ardupilot-embedded-drone-engineer/SKILL.md`)
with the build/SITL/MAVLink/log-analysis workflow — read that first.

## What's different from upstream

~36 files >2MB (board hwdef wiring-diagram images, `.dae` 3D meshes, prebuilt CMSIS DSP
`.a` libs) were removed before the initial push — the proxy this session pushes through
couldn't reliably transfer the full ~335MB pack. None of them are needed for SITL or for
editing flight/drive-logic source. If a real hardware build ever needs one of those
specific `hwdef` images, fetch it individually from upstream — don't re-mirror the whole
tree.

## Environment gotchas already solved here — don't rediscover them

- **`pip install empy==3.3.4` fails to build** on this image's setuptools with
  `AttributeError: install_layout`. Fix: `SETUPTOOLS_USE_DISTUTILS=stdlib pip install --user empy==3.3.4`.
  ArduPilot's build pins this exact old empy version; newer empy (4.x) is not
  API-compatible with waf's usage here.
- `pip install --user` puts consoles scripts in `~/.local/bin` — add that to `PATH` before
  running `./waf configure` or anything that shells out to `MAVExplorer.py`/MAVProxy.
- Submodules are already initialized (`git submodule update --init --recursive` was run).
  If a fresh clone starts over, that step is required before `./waf configure` — plain
  `git clone` alone leaves `modules/*` empty.

## Verified working (this session)

```bash
export PATH="$HOME/.local/bin:$PATH"
./waf configure --board sitl
./waf copter           # 1429/1429, links build/sitl/bin/arducopter
./waf rover             # 1376/1376, links build/sitl/bin/ardurover
```

Beyond boot — a full scripted flight/drive cycle via pymavlink, asserting real telemetry
transitions (not just "it started"). Scripts live in `Tools/claude-smoke-tests/`
(see that dir's README for usage):

- **Copter**: GUIDED → ARM → TAKEOFF to ~9m → RTL → auto-disarm — all confirmed via
  `HEARTBEAT`/`GLOBAL_POSITION_INT`, `sitl_flight_smoke.py` exits 0.
- **Rover**: GUIDED → ARM → drove >3m toward a GUIDED position target → DISARM —
  `sitl_rover_smoke.py` exits 0.

Not yet exercised: `Tools/autotest/sim_vehicle.py` (the MAVProxy-wrapped normal
interactive entry point — the smoke tests above talk MAVLink directly instead, which is
what the skill recommends for scripted/repeatable scenarios anyway), Plane build, the
full `autotest.py` regression suite (10-30+ min, run it when validating an actual code
change, not as a smoke test), dataflash log analysis on a real flight. Add those when a
task actually needs them.

**Gotcha found while testing**: EKF/GPS needs ~15-20s (wall clock, even at `--speedup 5`)
to settle after connecting before arming succeeds — arming attempted earlier fails
silently against a fresh `-w` (wiped) instance. Both smoke scripts already wait for this;
don't shorten it if you copy the pattern.
