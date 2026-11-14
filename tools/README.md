# tools

## `erdi_capture.py` — record the raw serial stream of a module

Cross-platform (Windows, Linux, macOS), Python 3.9+, needs only `pyserial`.
It **only listens** unless you pass `--start`. Use it with any USB-UART
adapter (CH340, CP2102, FTDI) wired to the module.

```bash
pip install pyserial
python erdi_capture.py --list                     # find the port
python erdi_capture.py --port COM6 --baud 460800 --seconds 40 \
    --model LRF10VB --unit vb --distance 1.90     # VB/H series stream on power-up
python erdi_capture.py --port /dev/ttyUSB0 --baud 115200 --start e2 \
    --model LR1200E2 --distance 12.0              # E2 series must be told to start
```

Wiring: module TX to adapter RX, module RX to adapter TX, grounds together,
module powered as its manual says (E2: hold pin 6 high).

| Option | Meaning |
|---|---|
| `--port` | `COM6`, `/dev/ttyUSB0`, or a pyserial URL such as `socket://host:port` |
| `--baud` | default 460800 (VB/H). E2 series: 115200 |
| `--seconds` | recording length, default 40 |
| `--distance` | tape-measured distance to the target in metres, saved with the capture |
| `--model` | module model, saved with the capture |
| `--unit vb\|h` | decode 5C frames as mm (`vb`) or cm (`h`) in the live status line |
| `--start e2\|vb` | send one documented start frame first: E2 `55 AA 89 FF FF FF FF 85`, VB `5A 0A 02 02 00 F1`. The only time the tool transmits |
| `--out` | output name without extension, default `erdi-capture-<time>` |

Every 5 seconds it prints the bytes received, the number of checksum-valid
frames and the median distance, so a wiring or baud mistake shows up early.

Output, next to where you run it:

* `<name>.bin` — the bytes exactly as received.
* `<name>.txt` — the same bytes as hex, 32 per line (`5C 02 11 EC ...`).
  Hex only, no header, so replay tools that read every two-digit hex token
  get the stream unchanged.
* `<name>.json` — port, baud, duration, model, distance, frame counts.

Exit code 0 means valid frames were recorded; 1 means no bytes or no valid
frames (the message says which); 2 means the port could not be opened.

Self-test without hardware (uses pyserial's `loop://` port):

```bash
python -m pytest -q tools
```

A Windows double-click version of the same idea (PowerShell, receive-only,
460800) is distributed separately to factory staff.
