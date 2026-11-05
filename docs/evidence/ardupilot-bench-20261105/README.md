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
