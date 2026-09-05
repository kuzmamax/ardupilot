# Claude smoke tests

Not part of upstream ArduPilot or its `autotest` suite — local additions for a quick
"does this SITL build actually fly/drive" check, scripted via pymavlink instead of
manual MAVProxy console steps (see `ardupilot-embedded-drone-engineer` skill in the
sibling repo `kuzmamax/desktop-tutorial`). Each is a `demo()`-style self-check: it
asserts real telemetry transitions (armed flag, altitude, position), not just that a
command was accepted, and exits nonzero on failure.

## Usage

Start the relevant SITL binary first (`./waf configure --board sitl && ./waf copter`
or `./waf rover`), then in a separate terminal:

```bash
# Copter: eeprom-wiped fresh instance, matches what the script expects
build/sitl/bin/arducopter --model + --speedup 5 \
  --defaults Tools/autotest/default_params/copter.parm \
  --home -35.363261,149.165230,584,353 -w &
python3 Tools/claude-smoke-tests/sitl_flight_smoke.py

# Rover
build/sitl/bin/ardurover --model rover --speedup 5 \
  --defaults Tools/autotest/default_params/rover.parm \
  --home -35.363261,149.165230,584,353 -w &
python3 Tools/claude-smoke-tests/sitl_rover_smoke.py
```

Both need ~15-20s after connecting for the EKF/GPS to settle before they'll arm — that
wait is built into each script, don't shorten it, arming will just fail.

Verified passing on this repo's SITL build 2026-09-05:

- `sitl_flight_smoke.py`: GUIDED → ARM → TAKEOFF to ~9m → RTL → auto-disarm
- `sitl_rover_smoke.py`: GUIDED → ARM → drove >3m toward a GUIDED target → DISARM
