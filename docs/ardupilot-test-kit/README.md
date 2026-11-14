# ArduPilot hardware test kit

This kit is for anyone who has an ERDI module and an ArduPilot flight
controller on the bench and is willing to send back a short log. It takes
about 30 minutes. You do not need to fly; the board can sit on the desk on USB
power plus the module's supply.

What the result is used for: the ERDI rangefinder driver is under review
upstream ([ArduPilot PR #34983](https://github.com/ArduPilot/ardupilot/pull/34983))
and reviewers rightly want logs from real hardware, recorded by someone other
than us.

## 1. Which firmware and which `RNGFNDx_TYPE`

The firmware below is ArduCopter master (4.8.0-dev) with the ERDI drivers
added. It is a **development test build for the bench only. Do not fly it.**

Before you flash:

- Take the propellers off if the board is in an airframe.
- Save your current parameters to a file first (Mission Planner: *Config >
  Full Parameter List > Save to file*). Loading a different firmware can reset
  them.
- When you are done, flash your normal stable firmware again and load your
  saved parameters.

| Your module | Protocol | `RNGFND1_TYPE` | Baud (fixed by the driver) | Firmware |
|---|---|---|---|---|
| LR1000E2, LR1200E2, LR1500E2, LR2000E2 | 8-byte `55 AA` command/reply | **51** (ERDI-E2-Serial) | 115200 | test build only (branch `rangefinder-erdi-e2`) |
| LRF10VB, LRF22VB, LRF50VB | 4-byte `5C`, millimetres | **49** (ERDI-VB-Serial) | 460800 | test build, or PR #34983 |
| LRF50H, LRF100H, LRF200H, LRF300H, LRF600H | 4-byte `5C`, centimetres | **50** (ERDI-H-Serial) | 460800 | test build, or PR #34983 |

Type values 49, 50 and 51 are the values used by these branches. They are not
in an official ArduPilot release yet and may change during review.

Download the `.apj` for your board from the
[ArduPilot test firmware release](https://github.com/ErdiTech/erdi-lrf-drivers/releases/tag/ardupilot-test-fw-20261115):

| File | Board | Vehicle |
|---|---|---|
| `arducopter-CubeOrangePlus-erdi-e2.apj` | Cube Orange+ | Copter |
| `ardurover-CubeOrangePlus-erdi-e2.apj` | Cube Orange+ | Rover |
| `arducopter-MatekH743-erdi-e2.apj` | Matek H743 (Wing/Slim/Mini) | Copter |

All three contain types 49, 50 and 51 and report `V4.8.0-dev (05ca63d6)`.
`SHA256SUMS.txt` in the same release lists the checksums. If your board is
not listed, open an issue with the board name and we will build one.

## 2. Wiring

### E2 series (LR1200E2 and siblings) to a Pixhawk-standard TELEM port

The module comes with a 6-wire harness. Pin numbers are from the module
manual's *Electrical Interface Definition*; the wire colours are the ones on
the E2 harness confirmed by the factory for the LR1000E2. **If the colours on
your harness differ, go by pin number, or ask us before powering up.**

| Module pin | Signal | Wire colour | TELEM port pin (JST-GH 6) |
|---|---|---|---|
| 1 | GND | black | 6 GND |
| 2 | VCC (5 V) | red | 1 +5 V |
| 3 | reserved | grey | not connected (insulate the end) |
| 4 | TXD (module out) | white | 3 RX (into the autopilot) |
| 5 | RXD (module in) | green | 2 TX (out of the autopilot) |
| 6 | SW-SHOT (enable) | yellow | +5 V: join it to the red wire |

Notes:

* **Pin 6 must be held high** or the module does not range under serial
  control. Joining it to VCC is how the factory wires it.
* Supply: the manual gives 3.3-5 V, about 1 W maximum and about 350 mA
  inrush. One module on a TELEM port's 5 V is fine; do not share that port's
  5 V with a power-hungry radio.
* Logic level: the TELEM port is 3.3 V logic. The factory has confirmed the
  LR1200E2 UART works at 3.3 V.
* On a Cube Orange+ use TELEM2 (= `SERIAL2`) if TELEM1 already has a radio.
  On other boards, any free UART works; replace `SERIAL2` below with that
  port's number (see the board's page on ardupilot.org).
* The module does not measure until it is told to. The driver sends the
  "continuous ranging" command at boot and again if the module goes quiet, so
  nothing needs to be configured on the module itself.
* The E2 minimum range is 4 m. Closer than that the module reports a failed
  measurement and the autopilot shows the sensor as out of range. Point it at
  a wall **at least 5 m away** for the test.

### VB and H series

| Module wire | Signal | TELEM port pin |
|---|---|---|
| red | power + (5 V) | 1 +5 V |
| black | power ground | 6 GND |
| yellow | signal ground | 6 GND |
| green | TX (module out) | 3 RX |
| blue | RX (module in) | 2 TX |

These modules stream from power-up at 460800 baud. Minimum range is 0.05 m.

## 3. Flash the firmware

**Mission Planner:** *Setup → Install Firmware → Load custom firmware*, pick
the `.apj`, and let it reboot. Do not let it auto-select a stock firmware.

**QGroundControl:** *Vehicle Setup → Firmware*, plug the board in, tick
*Advanced settings*, choose *ArduPilot* and *Custom firmware file...*, then
pick the `.apj`.

After the reboot the Messages tab should show `ArduCopter V4.8.0-dev` (or `ArduRover`) and
a git hash. Please note that line down; it goes in the report.

If the board already has your own setup on it, save your parameters first
(*Config → Full Parameter List → Save to file*) so you can go back.

## 4. Parameters

Set these (or load the matching `.param` file from this folder with
*Full Parameter List → Load from file*), then **reboot the board**:

| Parameter | E2 (LR1200E2) | VB (e.g. LRF10VB) | H (e.g. LRF50H) | Why |
|---|---|---|---|---|
| `SERIAL2_PROTOCOL` | 9 | 9 | 9 | Rangefinder on that port |
| `SERIAL2_BAUD` | 115 | 460 | 460 | documentation only, the driver sets the baud |
| `RNGFND1_TYPE` | 51 | 49 | 50 | driver |
| `RNGFND1_MIN` | 4 | 0.05 | 0.05 | metres |
| `RNGFND1_MAX` | 600 | 8.9 (LRF10VB) / 19.9 (LRF22VB) | rated range | metres |
| `RNGFND1_ORIENT` | 25 | 25 | 25 | default; fine for the bench |
| `LOG_DISARMED` | 1 | 1 | 1 | log while disarmed on the bench |

`RNGFND1_MAX` for E2 is set to 600 m for the bench test because the MAVLink
`DISTANCE_SENSOR` message cannot carry more than 655 m. The dataflash log
records the full value.

Set `LOG_DISARMED` back to 0 when you are done.

## 5. Check the reading

* **Mission Planner:** *Flight Data → Status* tab, field `rangefinder1`
  (metres).
* **QGroundControl:** *Analyze Tools → MAVLink Inspector →
  DISTANCE_SENSOR*, field `current_distance` (centimetres).

Cover and uncover the lens or move the module: the number should follow. If it
stays at 0 or the pre-arm check says `Rangefinder 1: No Data`, see
Troubleshooting below.

## 6. The test itself

1. Measure the distance from the front of the module to a flat wall with a
   tape or a hand-held laser meter. E2: at least 5 m. VB/H: anything in range.
2. Fix the module so it does not move (tape, clamp, a book).
3. Reboot the board so a fresh log starts.
4. Leave it pointed at the wall for **30 seconds** without touching it.
5. Optional, very useful: then point it at a second wall or object at a
   different known distance for another 30 seconds.
6. Take one photo that shows the wiring between the module and the board.

## 7. Download the log

* **Mission Planner:** *Flight Data → DataFlash Logs* tab →
  *Download DataFlash Log Via Mavlink* → tick the newest log → *Download*.
  The `.bin` file lands in Mission Planner's `logs` folder.
* **QGroundControl:** *Analyze Tools → Log Download → Refresh*, tick the
  newest entry, *Download*.
* Or take the SD card out: the files are in `APM/LOGS/` (newest number).

The rangefinder appears in the log as the `RFND` message.

## 8. What to send back

Open an issue in this repository titled `ArduPilot test: <module> on <board>`
(or reply to whoever sent you this kit) with:

1. the `.bin` log (zip it if GitHub refuses the extension),
2. the wiring photo,
3. the tape-measured distance(s),
4. the firmware line from the Messages tab, the board name and the module
   model printed on its label,
5. anything that looked wrong, even if it seems minor.

We will credit you in the upstream pull request by your GitHub handle unless
you tell us not to.

## Optional: raw byte capture

If you also have a USB-UART adapter (CH340, CP2102, FTDI), a 40-second
capture of the module's raw serial stream lets the driver be replayed in
simulation byte-for-byte. Use [`tools/erdi_capture.py`](../../tools/README.md);
it only listens unless you ask it to send the start command.

## Troubleshooting

| Symptom | Check |
|---|---|
| `Rangefinder 1: No Data` | TX and RX swapped? (module TXD goes to the port's RX.) `SERIAL2_PROTOCOL` = 9 and the board rebooted after setting it? E2: is pin 6 tied high? |
| `Rangefinder 1: Not Detected` | `RNGFND1_TYPE` is not in this firmware: you are running stock firmware, not the test build. |
| E2 reads out of range all the time | Target closer than 4 m, or a dark/angled target beyond reach. Try a light wall 5-20 m away. |
| VB reads out of range at a short distance | Below 0.05 m, or `RNGFND1_MAX` lower than the true distance. |
| Reading jumps by large amounts | Send us the log anyway; that is exactly what we want to see. |
