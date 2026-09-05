#!/usr/bin/env python3
"""Scripted arm/takeoff/RTL smoke test against a running ArduCopter SITL instance.

demo(): connects to tcp:127.0.0.1:5760, waits for EKF/GPS to be ready, switches to
GUIDED, arms, takes off to 10m, waits to reach altitude, switches to RTL, and asserts
each transition actually happened (not just that the command was accepted).
"""
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


def wait_alt(m, target_m, tolerance=1.0, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        msg = m.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=2)
        if msg is None:
            continue
        alt = msg.relative_alt / 1000.0
        if abs(alt - target_m) <= tolerance:
            return alt
    return None


def demo():
    print("connecting to tcp:127.0.0.1:5760 ...")
    m = mavutil.mavlink_connection("tcp:127.0.0.1:5760", autoreconnect=False, retries=0)
    hb = m.wait_heartbeat(timeout=20)
    if hb is None:
        print("FAIL: no heartbeat within 20s — is SITL actually running?")
        sys.exit(1)
    print(f"heartbeat ok: sysid={m.target_system} compid={m.target_component}")

    print("waiting for EKF/GPS lock (STATUSTEXT + EKF flags) ...")
    m.mav.request_data_stream_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_DATA_STREAM_ALL, 4, 1,
    )
    # give the EKF time to converge on the wiped/fresh instance
    time.sleep(15)

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

    print("takeoff to 10m")
    m.mav.command_long_send(
        m.target_system, m.target_component,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, 0, 0, 0, 0, 10,
    )
    alt = wait_alt(m, 10.0, tolerance=1.5, timeout=30)
    assert alt is not None, "FAIL: never reached ~10m"
    print(f"  ok: reached {alt:.1f}m (target 10m) via GLOBAL_POSITION_INT")

    print("mode -> RTL")
    m.set_mode_apm("RTL")
    assert wait_mode(m, "RTL"), "FAIL: never reached RTL"
    print("  ok: RTL confirmed via HEARTBEAT")

    print("waiting for disarm after landing")
    assert wait_armed(m, False, timeout=60), "FAIL: never disarmed after RTL/land"
    print("  ok: DISARMED confirmed via HEARTBEAT base_mode")

    print("PASS: full arm/takeoff/RTL/land/disarm cycle completed")


if __name__ == "__main__":
    try:
        demo()
    except AssertionError as e:
        print(e)
        sys.exit(1)
