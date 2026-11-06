# Factory bench capture — LRF22VB and LRF50H (2026-11-05)

Bench evidence recorded at the ERDI factory for the ArduPilot driver pull request
(ArduPilot/ardupilot#34983). Both modules were run from a laptop over a USB-to-TTL
adapter with the vendor serial tool at **460800 8N1**, aimed at a wall while the
distance was changed by hand.

| File | What it shows |
|---|---|
| `lrf22vb-wiring-usb-ttl-1.jpg`, `lrf22vb-wiring-usb-ttl-2.jpg` | LRF22VB module wired to a CH340-type USB-to-TTL adapter (5V / VCC / 3V3 / TXD / RXD / GND header) |
| `lrf22vb-bench-tool-settings.jpg` | Vendor tool: model `VB22A`, port `COM6`, baud `460800`, connect/disconnect log |
| `lrf22vb-bench-tool-trace.jpg` | Live distance trace while a hand is moved in and out of the beam |
| `lrf50h-bench-tool-settings.jpg` | Vendor tool: model `WT50A` (LRF50H), `COM6`, `460800`, output rate 1000 Hz |
| `lrf50h-bench-wiring.jpg` | LRF50H flying leads being connected during the recording |

Source: three phone videos (49 s + 42 s + 17 s, 720x1280) and two photos. The vendor
tool plots the decoded distance; it was not used to save the raw byte stream, so the
raw `0x5C` frames are not part of this set.

Follow-up from the factory (2026-11-06): the wall was **1.9 m** from the modules, and
the LRF22VB run used the tool's `VB22A(cm)` display entry, which is why its distance
reads in the 190s. That `(cm)` entry is a display-side division by 10 of the module's
millimetre frames — the tool sends no unit command to the module. Details, read from
the tool's own compiled code, are in [vendor-host-tool.md](../../vendor-host-tool.md).

## Tool log captures (2026-11-06)

A second run at the factory, same wiring and the same 1.9 m wall, this time
with the vendor tool's "save" button on. Each file is the tool's own log:
one line per received `0x5C` frame that passed its checksum,
`[yyyy-MM-dd hh:mm:ss]    <value>` in the displayed unit (see
[vendor-host-tool.md](../../vendor-host-tool.md)). The timestamps come from
the factory laptop's clock.

| File | Module | Tool entry | Frames | Span | Value |
|---|---|---|---|---|---|
| `lrf22vb-tool-capture-mm.txt` | LRF22VB | `VB22A(mm)` | 3000 | 32 s | 1708–1710, median 1709 (mm), every frame within ±2 of the median |
| `lrf50h-tool-capture-cm.txt` | LRF50H | `WT50A` | 2000 | 22 s | 189–204 cm for 1997 frames, median 196 (cm); 3 frames read 31496, 36977 and 39688 |

What they show:

- **Units.** The LRF22VB logs ~1709 in `(mm)` mode and the LRF50H logs ~196 as
  `WT50A`, both at the same wall the factory measured as 1.9 m. So the VB wire
  value is millimetres and the H wire value is centimetres, as the manuals and
  [protocol-B-5C.md](../../protocol-B-5C.md) state. The ArduPilot driver scales
  by 0.001 for VB and 0.01 for H, which matches.
- **Stability.** Both modules sit within a few units of their median for the
  whole run against a static target.
- **Spikes on the H series.** 3 of the 2000 LRF50H frames carry a distance of
  315–397 m, far past the 50 m rating, with a checksum the tool accepted. They
  are not the `0xFFFF` out-of-range code. A driver that averages every valid
  frame in an update window would pull a 1.96 m reading to several metres
  when one of these lands in the window, so the ArduPilot driver treats any
  frame beyond `RNGFNDx_MAX` as out-of-range instead of averaging it.
- **Rate.** The tool logged ~94 frames/s (VB) and ~91 frames/s (H). The H
  series streams faster than that; the tool's own receive loop sets this
  rate, not the module.

These are decoded values, not the raw byte stream, so they cannot be replayed
through the driver's frame parser. A raw capture and a flight-controller log
are still the missing pieces for "tested on hardware".
