#!/usr/bin/env python3
"""Record the raw UART byte stream of an ERDI rangefinder module.

Receive-only by default: nothing is written to the module. The capture is
saved three ways:

  <name>.bin   the bytes exactly as received
  <name>.txt   the same bytes as hex text, 32 per line ("5C 02 11 EC ...").
               This file contains hex only, so replay tools that pick every
               two-digit hex token out of the text read it unchanged.
  <name>.json  port, baud, duration, known distance, byte/frame counts

While recording it prints a status line every 5 seconds with the number of
checksum-valid frames and the median decoded distance, so you can see the
wiring is right before the recording ends.

Examples:

  python erdi_capture.py --list
  python erdi_capture.py --port COM6 --baud 460800 --seconds 40 --distance 1.90
  python erdi_capture.py --port /dev/ttyUSB0 --baud 115200 --start e2 --distance 12.0

Modules that only measure after a command (the E2 series: LR1000E2,
LR1200E2, LR1500E2, LR2000E2) need --start e2, which sends the documented
"continuous ranging" frame once (55 AA 89 FF FF FF FF 85). --start vb sends
the VB-series "start ranging" frame (5A 0A 02 02 00 F1). Without --start
the tool never transmits.

Requires pyserial (pip install pyserial). MIT licence.
"""
import argparse
import datetime as _dt
import json
import statistics
import sys
import time

try:
    import serial
except ImportError:  # pragma: no cover
    sys.exit("pyserial is required: pip install pyserial")

START_COMMANDS = {
    "e2": bytes.fromhex("55AA89FFFFFFFF85"),
    "vb": bytes.fromhex("5A0A020200F1"),
}

# unit of one raw count, per protocol: B frames (5C) are mm for VB and cm
# for H; A frames (55 AA) are 0.1 m.
UNIT_M = {"vb": 0.001, "h": 0.01, "e2": 0.1}


def decode_5c(data):
    """Return raw distance values of checksum-valid 4-byte 5C frames."""
    out = []
    i = 0
    n = len(data)
    while i + 3 < n:
        if data[i] == 0x5C and ((~(data[i + 1] + data[i + 2])) & 0xFF) == data[i + 3]:
            out.append(data[i + 1] | data[i + 2] << 8)
            i += 4
        else:
            i += 1
    return out


def decode_55aa(data):
    """Return (function, sta, raw) of checksum-valid 8-byte 55 AA frames."""
    out = []
    i = 0
    n = len(data)
    while i + 7 < n:
        if data[i] == 0x55 and data[i + 1] == 0xAA and (sum(data[i:i + 7]) & 0xFF) == data[i + 7]:
            out.append((data[i + 2], data[i + 3], data[i + 5] << 8 | data[i + 6]))
            i += 8
        else:
            i += 1
    return out


def summarise(data, unit=None):
    """Frame counts and median distance for whichever protocol is present."""
    b = decode_5c(data)
    a = decode_55aa(data)
    a_ok = [raw for (fn, sta, raw) in a if fn in (0x88, 0x89) and sta == 1]
    s = {
        "bytes": len(data),
        "frames_5c": len(b),
        "frames_55aa": len(a),
        "frames_55aa_ok": len(a_ok),
    }
    if len(a) > len(b):
        s["protocol"] = "55AA"
        if a_ok:
            s["median_m"] = round(statistics.median(a_ok) * UNIT_M["e2"], 3)
    elif b:
        s["protocol"] = "5C"
        valid = [r for r in b if r != 0xFFFF]
        s["frames_5c_out_of_range"] = len(b) - len(valid)
        if valid:
            med = statistics.median(valid)
            s["median_raw"] = med
            if unit in UNIT_M:
                s["median_m"] = round(med * UNIT_M[unit], 3)
    else:
        s["protocol"] = None
    return s


def to_hex_lines(data, per_line=32):
    return "\n".join(
        " ".join("%02X" % x for x in data[i:i + per_line])
        for i in range(0, len(data), per_line)
    ) + ("\n" if data else "")


def status_line(elapsed, data, unit):
    s = summarise(data, unit)
    msg = "%5.1f s  %8d bytes  5C frames %6d  55AA frames %5d" % (
        elapsed, s["bytes"], s["frames_5c"], s["frames_55aa"])
    if "median_m" in s:
        msg += "  median %.3f m" % s["median_m"]
    elif "median_raw" in s:
        msg += "  median raw %s (pass --unit to convert)" % s["median_raw"]
    return msg


def capture(port, seconds, start=None, unit=None, report_every=5.0, out=sys.stdout):
    """Read from an open pyserial port for `seconds`; return the bytes."""
    if start:
        port.write(START_COMMANDS[start])
        port.flush()
    buf = bytearray()
    t0 = time.monotonic()
    next_report = t0 + report_every
    while True:
        now = time.monotonic()
        if now - t0 >= seconds:
            break
        chunk = port.read(port.in_waiting or 1)
        if chunk:
            buf.extend(chunk)
        if now >= next_report:
            print(status_line(now - t0, buf, unit), file=out, flush=True)
            next_report += report_every
    return bytes(buf)


def list_ports():
    from serial.tools import list_ports as lp
    ports = list(lp.comports())
    if not ports:
        print("no serial ports found")
    for p in ports:
        print("%-16s %s" % (p.device, p.description))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Record the raw UART stream of an ERDI rangefinder (receive-only by default).")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--port", help="serial port, e.g. COM6 or /dev/ttyUSB0 (pyserial URLs such as socket:// also work)")
    ap.add_argument("--baud", type=int, default=460800,
                    help="baud rate (default 460800 for VB/H series; E2 series is 115200)")
    ap.add_argument("--seconds", type=float, default=40, help="recording length (default 40)")
    ap.add_argument("--out", help="output name without extension (default erdi-capture-<time>)")
    ap.add_argument("--distance", type=float, help="known distance to the target in metres, stored in the .json")
    ap.add_argument("--model", default="", help="module model, stored in the .json (e.g. LRF10VB)")
    ap.add_argument("--unit", choices=sorted(UNIT_M), help="decode 5C frames as vb (mm) or h (cm) for the live median")
    ap.add_argument("--start", choices=sorted(START_COMMANDS),
                    help="send one documented start-ranging frame before recording (the only time the tool transmits)")
    a = ap.parse_args(argv)

    if a.list:
        list_ports()
        return 0
    if not a.port:
        ap.error("--port is required (use --list to see ports)")

    name = a.out or "erdi-capture-" + _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        port = serial.serial_for_url(a.port, baudrate=a.baud, bytesize=8, parity="N",
                                     stopbits=1, timeout=0.05)
    except serial.SerialException as e:
        print("could not open %s: %s" % (a.port, e), file=sys.stderr)
        print("Is another program (serial monitor, ground station) using the port?", file=sys.stderr)
        return 2

    print("recording %s at %d baud for %.0f s%s -> %s.{bin,txt,json}" % (
        a.port, a.baud, a.seconds, " (sending %s start frame)" % a.start if a.start else " (receive only)", name))
    try:
        data = capture(port, a.seconds, start=a.start, unit=a.unit)
    except KeyboardInterrupt:
        print("stopped early")
        data = b""
    finally:
        port.close()

    with open(name + ".bin", "wb") as f:
        f.write(data)
    with open(name + ".txt", "w", encoding="ascii", newline="\n") as f:
        f.write(to_hex_lines(data))
    s = summarise(data, a.unit)
    meta = {
        "tool": "erdi_capture.py",
        "port": a.port,
        "baud": a.baud,
        "seconds": a.seconds,
        "start_command": a.start,
        "model": a.model,
        "known_distance_m": a.distance,
        "recorded_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "summary": s,
    }
    with open(name + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(status_line(a.seconds, data, a.unit))
    if not data:
        print("No bytes received. Check: TX of the module goes to RX of the adapter, common GND, "
              "baud rate, and for E2 modules use --start e2 and hold pin 6 high.")
        return 1
    if not (s["frames_5c"] or s["frames_55aa"]):
        print("Bytes arrived but no valid frames were found: the baud rate is probably wrong.")
        return 1
    print("saved %s.bin, %s.txt, %s.json" % (name, name, name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
