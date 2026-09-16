# erdi-lrf-drivers

Open-source Python, Arduino and ROS 2 drivers for **ERDI 905 nm laser
rangefinder modules** — both published protocol families, all 22 models with a
published protocol.

Manufacturer: [erdilrf.com](https://erdilrf.com/) ·
Model catalogue: [erdilrf.com/models](https://erdilrf.com/models/) ·
Datasheets & samples: [erdilrf.com/contact](https://erdilrf.com/contact/) ·
Email **tommy@erdimail.com** · WhatsApp [**+86 133 0819 5790**](https://wa.me/8613308195790) · Tel **+86-28-81076698**

ERDI ships the full communication protocol with every module. This repository
turns it into code you can `pip install`, drop into the Arduino IDE, or `colcon
build`, so integration takes an afternoon instead of an email thread.

* Two protocol families cover the whole catalogue:
  **[A — 8-byte `55 AA` command/response](docs/protocol-A-55AA.md)** and
  **[B — free-running `5C` data frames](docs/protocol-B-5C.md)**.
* Every constant is transcribed from the model's own manual and cited in the
  docs and in the source. Nothing is extrapolated from a sibling model.
* Where a manual is silent or contradicts itself, the driver **says so and
  refuses to guess** — see [Known gaps](#known-gaps).

## Supported models

Full table with baud rates, frame layouts, units and ranges:
**[docs/models.md](docs/models.md)**.

| Family | Models | Frame | Default baud | Raw unit |
|---|---|---|---|---|
| **A** — `55 AA` command/response | LR1000E2/E4, LR1200E2/E4, LR1500E2/E4, LR2000E2/E4, LRF1200A1, LRF3000A1, SPD1200N0/N2/N4, SPD1200D03 | 8 bytes | 115200 | value × 10 (0.1 m/count) |
| **B** — `5C` free-running stream | LRF50H, LRF100H, LRF200H, LRF300H, LRF600H, LRF1500H | 4 bytes (LRF1500H: 5) | 460800 | **centimetres** |
| **B** — `5C` free-running stream | LRF22VB, LRF50VB | 4 bytes | 460800 | **millimetres** |

> ⚠️ **The units are not uniform.** The frame `5C 02 11 EC` means **43.54 m** on
> an H-series module and **4.354 m** on a VB-series module. Always select your
> model by name; never let a driver infer it from the family.

`LRF10VB` and `SPD1200S2G` are in the catalogue but ERDI has not published a
communication manual for them, so this repository ships no driver for them and
raises a clear error rather than falling back to a similar model.

## Install in one command

```bash
# from the latest GitHub release (recommended — pinned, no git needed at install time)
pip install https://github.com/yu911517778-a11y/erdi-lrf-drivers/releases/download/v0.1.0/erdi_lrf-0.1.0-py3-none-any.whl

# or track main directly
pip install git+https://github.com/yu911517778-a11y/erdi-lrf-drivers
```

Arduino: install via the Arduino IDE **Library Manager** — search `ErdiLRF`
([submission pending arduino/library-registry review](https://github.com/arduino/library-registry));
until it is indexed, install with `arduino-cli lib install --git-url
https://github.com/yu911517778-a11y/erdi-lrf-drivers.git` (points at the repo
root — use `--git-url ...#main:arduino/ErdiLRF` if your `arduino-cli` version
needs the subfolder pinned) or by copying `arduino/ErdiLRF` into your
`libraries/` folder.

PlatformIO: `pio pkg install --library "yu911517778-a11y/erdi-lrf-drivers"` (Git
URL form; see [platformio.ini example](#arduino)) — Registry-name install
(`pio pkg install --library "erdi-lrf"`) is pending publication to the
[PlatformIO Registry](https://registry.platformio.org).

All release artifacts (wheel + sdist): <https://github.com/yu911517778-a11y/erdi-lrf-drivers/releases>
· Hardware and datasheets: <https://erdilrf.com>

## Quick start

### Python

```bash
cd python
pip install -e .

erdi-lrf models                                    # every model and its wire facts
erdi-lrf info --model LRF3000A1                    # what the manual says, with sources
erdi-lrf --port COM3 --model LRF3000A1 measure     # one measurement
erdi-lrf --port /dev/ttyUSB0 --model LRF100H stream --count 20
```

```python
from erdi_lrf import ErdiLRF

with ErdiLRF("/dev/ttyUSB0", model="LRF3000A1") as lrf:
    m = lrf.measure()
    print(f"{m.metres:.1f} m")          # baud, framing and scaling come from the model

with ErdiLRF("/dev/ttyUSB0", model="LRF100H") as lrf:
    for m in lrf.stream():              # family B free-runs at 460800 bps
        print(m.metres, "m", "(out of range)" if m.out_of_range else "")
```

The codecs (`erdi_lrf.protocol_a`, `erdi_lrf.protocol_b`) are pure functions with
no serial dependency, so you can encode and decode frames in tests, simulators
or your own transport.

### Arduino

Copy `arduino/ErdiLRF` into your `libraries/` folder (or
`arduino-cli lib install --git-url` this repository), then:

```cpp
#include <ErdiLRF.h>

ErdiLRF lrf(Serial1, ERDI_LRF3000A1);

void setup() {
  Serial.begin(115200);
  Serial1.begin(erdiDefaultBaud(ERDI_LRF3000A1));   // 115200 here, 460800 for family B
}

void loop() {
  ErdiMeasurement m;
  if (lrf.measure(&m) == ERDI_OK) Serial.println(m.metres, 3);
  delay(500);
}
```

Works with `HardwareSerial` or `SoftwareSerial` (anything that is a `Stream`).
The model table lives in flash, so the library costs ~350 bytes of SRAM on an
Uno. Examples: [`BasicMeasure`](arduino/ErdiLRF/examples/BasicMeasure),
[`ContinuousStream`](arduino/ErdiLRF/examples/ContinuousStream).

A step-by-step wiring and first-reading walkthrough for the Arduino side is
here: [Reading an ERDI laser distance module over UART with
Arduino](https://erdilrf.com/knowledge/read-laser-distance-module-arduino-uart/).

> SoftwareSerial cannot reach the 460800 bps that family-B modules use by
> default. Use a hardware UART, or set the module to a lower documented rate
> first with `setBaudB()`.

### ROS 2

```bash
# the node uses the Python package above
cd python && pip install -e . && cd ..

cp -r ros2/erdi_lrf_ros2 ~/ros2_ws/src/
cd ~/ros2_ws && colcon build --packages-select erdi_lrf_ros2
source install/setup.bash

ros2 run erdi_lrf_ros2 range_node --ros-args \
  -p port:=/dev/ttyUSB0 -p model:=LRF3000A1 -p rate:=10.0 -p frame_id:=lrf_link
# or
ros2 launch erdi_lrf_ros2 erdi_lrf.launch.py port:=/dev/ttyUSB0 model:=LRF100H
```

Publishes `sensor_msgs/Range` on `range`. `min_range` and `max_range` come from
the model's own ranging-range specification; `radiation_type` is `INFRARED`.
`field_of_view` defaults to `0.0` (undeclared) because the protocol manuals do
not carry beam divergence — set it from your model's datasheet if you need it.

Parameters: `port`, `model`, `baud` (0 = model default), `rate`, `frame_id`,
`field_of_view`, `continuous`, `acknowledge_protocol_hold`.

## Protocol documentation

* [docs/protocol-A-55AA.md](docs/protocol-A-55AA.md) — frame layout, the two
  different checksums, the command table, error codes, both baud TYPE tables.
* [docs/protocol-B-5C.md](docs/protocol-B-5C.md) — data frames, the `Check_Sum`
  function, the `5A` command table, baud codes, frequency divisors, the VB I²C
  register map.
* [docs/models.md](docs/models.md) — all 24 catalogue models with their wire
  facts and their hardware pages.

Every table row carries the manual sentence it came from.

## Tests

```bash
cd python && pip install -e ".[test]" && pytest
```

The test suite is built from **golden frames printed in the ERDI manuals** —
`55 AA 88 FF FF FF FF 84`, `5C 02 11 EC`, `5A 0D 02 0D 0D D6` and about thirty
more. Where a manual prints no full example (reply frames carrying real
distances), the expected checksum is computed by hand from the manual's stated
formula and the arithmetic is written into the test docstring. There are also
tests that assert the *manual's own inconsistencies*, so a future contributor
cannot quietly "fix" them.

Transport is tested against a scripted fake serial port, so `pytest` needs no
hardware.

## Get the hardware

| | |
|---|---|
| Model catalogue | <https://erdilrf.com/models/> |
| Long range, 3 km | [LRF3000A1](https://erdilrf.com/models/lrf3000a1/) |
| 1–2 km OEM modules | [LR1000E2](https://erdilrf.com/models/lr1000e2/) · [LR1200E2](https://erdilrf.com/models/lr1200e2/) · [LR1500E2](https://erdilrf.com/models/lr1500e2/) · [LR2000E2](https://erdilrf.com/models/lr2000e2/) |
| 1.2 km SPD series | [SPD1200N0](https://erdilrf.com/models/spd1200n0/) · [SPD1200D03](https://erdilrf.com/models/spd1200d03/) |
| Short-range DToF, cm | [LRF50H](https://erdilrf.com/models/lrf50h/) · [LRF100H](https://erdilrf.com/models/lrf100h/) · [LRF200H](https://erdilrf.com/models/lrf200h/) · [LRF300H](https://erdilrf.com/models/lrf300h/) · [LRF600H](https://erdilrf.com/models/lrf600h/) · [LRF1500H](https://erdilrf.com/models/lrf1500h/) |
| Short-range DToF, mm | [LRF22VB](https://erdilrf.com/models/lrf22vb/) · [LRF50VB](https://erdilrf.com/models/lrf50vb/) |

Questions, samples, datasheets and custom protocol work:
<https://erdilrf.com/contact/>

## Further reading

Background write-ups on the manufacturer's site. They cover the same wire facts
this repository implements, from the integration side rather than the code side:

* [Serial protocol, frames and
  checksums](https://erdilrf.com/knowledge/laser-rangefinder-serial-protocol-frame-checksum-basics/)
  — why the transmit and reply checksum scopes differ, which is the most common
  reason a first integration returns nothing.
* [UART/TTL integration
  guide](https://erdilrf.com/knowledge/uart-ttl-integration-guide-lrf-modules/)
  — levels, wiring and baud selection before any code runs.
* [Which modules support
  I²C](https://erdilrf.com/knowledge/laser-rangefinder-module-i2c-support/) —
  the register map and the models that genuinely publish an address.
* [Reading a module with
  Arduino](https://erdilrf.com/knowledge/read-laser-distance-module-arduino-uart/)
  — the walkthrough for the Arduino library above.
* [How to read the datasheet
  fields](https://erdilrf.com/knowledge/laser-rangefinder-module-datasheet-fields/)
  — minimum range, segmented accuracy and update rate, which decide which model
  you should have bought before the driver matters.
* [Update rate on moving
  platforms](https://erdilrf.com/knowledge/rangefinder-update-rate-moving-platforms/)
  — what the `rate` parameter of the ROS 2 node is actually bounded by.

## Known gaps

These are places where the manufacturer manual is silent or disagrees with
itself. The drivers surface them instead of papering over them. Full detail with
quotations is in the two protocol documents.

1. **`SPD1200D03` default baud rate is unresolved.** Its manual states 115200 bps
   in the protocol section and 15200/9600 bps in the technical table, and adds
   "Do not select a host baud rate until the delivered unit configuration is
   confirmed." Both drivers therefore require an explicit baud rate for this
   model instead of choosing one.
2. **`SPD1200D03` publishes no distance scaling.** The Python driver returns raw
   counts with `metres = None`; the Arduino driver returns `NAN`; the ROS 2 node
   refuses to start rather than publish a `Range` in metres it cannot justify.
3. **`SPD1200D03` publishes no `STA` semantics**, so its status byte is returned
   unchecked.
4. **`LRF1200A1` and `LRF3000A1` continuous ranging is under a protocol hold.**
   Their manuals record request function `0x89` and reply function `0x88` and
   explicitly decline to authorise a response parser. Streaming requires an
   explicit acknowledgement from the caller; single-shot is unaffected.
5. **`LRF1500H`'s printed example frame contradicts its own checksum function.**
   `5C 02 11 03 EC` should be `… E9`; `0xEC` is correct for the other models'
   4-byte frame. The drivers implement the printed function and a test pins the
   discrepancy.
6. **`LRF1500H`'s out-of-range value is stated twice, inconsistently** —
   16777215 in section 5.2 and "0xFFFF (16777215)" in section 6, where `0xFFFF`
   is 65535. The drivers use 16777215, matching the stated 3-byte field width.
7. **`LRF50VB`'s printed serial-read request checksum does not verify** for
   either length byte. The drivers build the request with the published
   `Check_Sum` function.
8. **`SPD1200N0/N2/N4` do not print a transmit checksum formula**, only the note
   that request and reply scopes differ. The drivers use the family-A transmit
   formula, which reproduces every example frame those manuals do print.
9. **The self-test `ErrCode` byte position differs between transcriptions** —
   D3 in the LR-series row, D4 in SPD1200D03's eight-byte form. The Python
   driver exposes both candidates rather than choosing.
10. **`LRF300H`, `LRF600H` and `LRF1500H` publish no output-frequency divisor
    formula**, so set/read frequency is not exposed for them.
11. **`LRF50H`, `LRF100H`, `LRF300H`, `LRF600H` and `LRF1500H` publish no I²C
    address.** Only `LRF200H` (`0x33`) and the VB series (`0x52`) do.
12. **Family-A stop bits and parity are not stated** — only "Data bits: 8". The
    drivers leave the platform default (8N1) in place.
13. **`LRF10VB` and `SPD1200S2G` have no published protocol at all.** They are
    listed but not driven.
14. **Not tested against live hardware in this repository.** The codecs are
    verified against the manuals' golden frames and the transport against a fake
    serial port; the ROS 2 package is statically checked but has not been run in
    a ROS 2 environment here. Bench reports and pull requests are welcome.

## Contact

ERDI TECH LTD · 905 nm laser rangefinder modules · tommy@erdimail.com · WhatsApp +86 133 0819 5790 · erdilrf.com

## Contributing

Two rules, inherited from how the protocol reference was built:

1. **Cite the manual.** Every constant needs the sentence it came from, in a
   comment or in the docs table.
2. **Never extrapolate across models.** If a manual is silent, add a row to
   Known gaps. A blank costs a support email; a guess costs a returned module.

## Contact ERDI

Talk to the people who make the modules — no form gate, no reseller in between.

**ERDI TECH LTD** — 905 nm eye-safe laser rangefinder modules (IEC 60825-1 Class 1)

| | |
|---|---|
| Email | [tommy@erdimail.com](mailto:tommy@erdimail.com?subject=905%20nm%20rangefinder%20module%20enquiry) |
| WhatsApp | [+86 133 0819 5790](https://wa.me/8613308195790) |
| Tel | +86-28-81076698 |
| Web | <https://erdilrf.com> · [Contact form](https://erdilrf.com/contact/) |
| Address | Room 2812, 28/F, Building 3, No. 88 Jiaozi Avenue, Chengdu Hi-Tech Zone, Sichuan, China |

Samples, datasheets, mechanical drawings and custom protocol work: email or WhatsApp is
usually faster than the form. We answer within one working day.

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 ERDI Technology (Chengdu).
