"""Self-test for erdi_capture.py using pyserial's loop:// port (no hardware)."""
import io
import json
import os
import sys

import serial

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import erdi_capture as ec  # noqa: E402


def frame_5c(raw):
    lo, hi = raw & 0xFF, raw >> 8
    return bytes([0x5C, lo, hi, (~(lo + hi)) & 0xFF])


def frame_e2(raw, sta=1, fn=0x89):
    f = bytes([0x55, 0xAA, fn, sta, 0xFF, raw >> 8, raw & 0xFF])
    return f + bytes([sum(f) & 0xFF])


def test_decode_5c_manual_example():
    # manual example: 5C 02 11 EC -> 0x1102 = 4354
    assert ec.decode_5c(bytes.fromhex("5C0211EC")) == [4354]


def test_decode_5c_resyncs_after_garbage():
    data = b"\x00\x5c\x12" + frame_5c(1709) * 3 + b"\xff"
    assert ec.decode_5c(data) == [1709, 1709, 1709]


def test_decode_55aa_and_checksum_scope():
    # the host->module command checksum excludes the header, so the
    # start command itself must not decode as a module reply
    assert ec.decode_55aa(ec.START_COMMANDS["e2"]) == []
    assert ec.decode_55aa(frame_e2(125)) == [(0x89, 1, 125)]


def test_summary_e2():
    data = frame_e2(125) * 5 + frame_e2(0, sta=0)
    s = ec.summarise(data)
    assert s["protocol"] == "55AA" and s["frames_55aa"] == 6 and s["frames_55aa_ok"] == 5
    assert s["median_m"] == 12.5


def test_hex_text_round_trip_with_replay_regex():
    import re
    data = bytes(range(256))
    text = ec.to_hex_lines(data)
    assert bytes(int(h, 16) for h in re.findall(r"\b[0-9A-Fa-f]{2}\b", text)) == data


def test_capture_over_loop_port():
    port = serial.serial_for_url("loop://", timeout=0.05)
    payload = frame_5c(1709) * 200
    port.write(payload)
    out = io.StringIO()
    got = ec.capture(port, seconds=0.5, unit="vb", report_every=0.2, out=out)
    assert got == payload
    assert "median 1.709 m" in out.getvalue()


def test_main_writes_files(tmp_path):
    name = str(tmp_path / "cap")
    # loop:// echoes what the tool sends, so --start e2 also checks that
    # the start frame is sent and does not count as a reply
    rc = ec.main(["--port", "loop://", "--baud", "115200", "--seconds", "0.3",
                  "--start", "e2", "--out", name, "--distance", "12.5"])
    assert rc == 1  # only the echoed command arrived: no valid frames
    assert open(name + ".bin", "rb").read() == ec.START_COMMANDS["e2"]
    meta = json.load(open(name + ".json"))
    assert meta["known_distance_m"] == 12.5 and meta["start_command"] == "e2"
