#!/usr/bin/env python3
"""Scripted arm/guided-drive smoke test against a running ArduRover SITL instance.

demo(): connects to tcp:127.0.0.1:5760, switches to GUIDED, arms, sends a GUIDED
position target a short distance ahead, and asserts the rover actually moved
(not just that the command was accepted) before disarming.
"""
import math
import sys
import time

from pymavlink import mavutil


def wait_mode(m, mode, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
        cur = mavutil.mode_string_v10(m.messages["HEARTBEAT"])
        if cur == mode:
            return True
    return False


def wait_armed(m, armed, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=2)
        if hb is None:
            continue
        is_armed = bool(hb.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
        if is_armed == armed:
            return True
    return False


def get_latlon(m, timeout=5):
    msg = m.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=timeout)
    if msg is None:
        return None
    return msg.lat / 1e7, msg.lon / 1e7


def meters_between(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = (lat2 - lat1) * 111320
    dlon = (lon2 - lon1) * 111320 * math.cos(math.radians(lat1))
    return math.hypot(dlat, dlon)


def demo():
    print("connecting to tcp:127.0.0.1:5760 ...")
    m = mavutil.mavlink_connection("tcp:127.0.0.1:5760", autoreconnect=False, retries=0)
    hb = m.wait_heartbeat(timeout=20)
    if hb is None:
        print("FAIL: no heartbeat within 20s — is SITL actually running?")
        sys.exit(1)
    print(f"heartbeat ok: sysid={m.target_system} compid={m.target_component}")

    m.mav.request_data_stream_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 4, 1,
    )
    print("waiting for EKF/GPS lock ...")
    time.sleep(20)

    start = None
    deadline = time.time() + 15
    while time.time() < deadline:
        pos = get_latlon(m, timeout=3)
        if pos is not None and pos != (0.0, 0.0):
            start = pos
            break
    assert start is not None, "FAIL: no non-zero GLOBAL_POSITION_INT (GPS never locked)"
    print(f"start position: {start}")

    print("mode -> GUIDED")
    m.set_mode_apm("GUIDED")
    assert wait_mode(m, "GUIDED"), "FAIL: never reached GUIDED"
    print("  ok: GUIDED confirmed via HEARTBEAT")

    print("arming")
    m.mav.command_long_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0,
    )
    assert wait_armed(m, True), "FAIL: never armed"
    print("  ok: ARMED confirmed via HEARTBEAT base_mode")

    # target ~20m north of start
    target_lat = start[0] + (20.0 / 111320)
    target_lon = start[1]
    print(f"sending GUIDED target ~20m north: {target_lat:.6f},{target_lon:.6f}")
    m.mav.set_position_target_global_int_send(
        0, m.target_system, m.target_component,
        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
        0b0000111111111000,  # only lat/lon/alt valid
        int(target_lat * 1e7), int(target_lon * 1e7), 0,
        0, 0, 0, 0, 0, 0, 0, 0,
    )

    moved = 0.0
    deadline = time.time() + 40
    while time.time() < deadline:
        pos = get_latlon(m, timeout=3)
        if pos is None:
            continue
        moved = meters_between(start, pos)
        if moved > 3.0:
            break

    assert moved > 3.0, f"FAIL: rover only moved {moved:.1f}m in 40s, expected >3m"
    print(f"  ok: rover moved {moved:.1f}m from start (GLOBAL_POSITION_INT)")

    print("disarming")
    m.mav.command_long_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 0, 0, 0, 0, 0, 0,
    )
    assert wait_armed(m, False, timeout=15), "FAIL: never disarmed"
    print("  ok: DISARMED confirmed via HEARTBEAT base_mode")

    print("PASS: arm/guided-drive/disarm cycle completed")


if __name__ == "__main__":
    try:
        demo()
    except AssertionError as e:
        print(e)
        sys.exit(1)
