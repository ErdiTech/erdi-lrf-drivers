# Model table

Every row is transcribed from that model's own ERDI manual. **Nothing is
extrapolated from a sibling model** — the units are not uniform across this
catalogue, and assuming they are is a 10x error.

Columns:

* **Family** — `A` = 8-byte `55 AA` command/response
  ([protocol-A-55AA.md](protocol-A-55AA.md)); `B` = free-running `5C` data
  frames ([protocol-B-5C.md](protocol-B-5C.md)).
* **Baud** — the manual's documented default.
* **Frame / dist** — bytes per data frame, and bytes of distance inside it.
* **Unit** — the unit of one raw count. Family A raw counts are
  `value × 10`, i.e. one count is 0.1 m; the H series counts centimetres; the
  VB series counts millimetres.
* **Range** — the model's ranging-range row from its source technical table,
  used for `sensor_msgs/Range` `min_range` / `max_range`.

| Model | Family | Baud | Frame / dist | Unit | Range | Wavelength | Notes |
|---|---|---|---|---|---|---|---|
| [LR1000E2](https://erdilrf.com/models/lr1000e2/) | A | 115200 | 8 B / 2 B | m | 4.0-1000.0 m | 905 nm ± 5 nm |  |
| [LR1000E4](https://erdilrf.com/models/lr1000e4/) | A | 115200 | 8 B / 2 B | m | 4.0-1000.0 m | 905 ± 5 nm |  |
| [LR1200E2](https://erdilrf.com/models/lr1200e2/) | A | 115200 | 8 B / 2 B | m | 4.0-1200.0 m | 905 nm ± 5 nm |  |
| [LR1200E4](https://erdilrf.com/models/lr1200e4/) | A | 115200 | 8 B / 2 B | m | 4.0-1200.0 m | 905 ± 5 nm |  |
| [LR1500E2](https://erdilrf.com/models/lr1500e2/) | A | 115200 | 8 B / 2 B | m | 4.0-1500.0 m | 905 nm ± 5 nm |  |
| [LR1500E4](https://erdilrf.com/models/lr1500e4/) | A | 115200 | 8 B / 2 B | m | 4.0-1500.0 m | 905 ± 5 nm |  |
| [LR2000E2](https://erdilrf.com/models/lr2000e2/) | A | 115200 | 8 B / 2 B | m | 4.0-2000.0 m | 905 nm ± 5 nm |  |
| [LR2000E4](https://erdilrf.com/models/lr2000e4/) | A | 115200 | 8 B / 2 B | m | 4.0-2000.0 m | 905 ± 5 nm |  |
| [LRF1200A1](https://erdilrf.com/models/lrf1200a1/) | A | 115200 | 8 B / 2 B | m | 5.0-1200.0 m | - | continuous ranging under PROTOCOL HOLD |
| [LRF3000A1](https://erdilrf.com/models/lrf3000a1/) | A | 115200 | 8 B / 2 B | m | 1.0-3000.0 m | 905 ± 10 nm, Class 1 (IEC 60825-1) | continuous ranging under PROTOCOL HOLD |
| [SPD1200N0](https://erdilrf.com/models/spd1200n0/) | A | 115200 | 8 B / 2 B | m | 0.2-1200.0 m | 905 nm ± 5 nm |  |
| [SPD1200N2](https://erdilrf.com/models/spd1200n2/) | A | 115200 | 8 B / 2 B | m | 0.2-1200.0 m | 905 nm ± 5 nm |  |
| [SPD1200N4](https://erdilrf.com/models/spd1200n4/) | A | 115200 | 8 B / 2 B | m | 0.2-1200.0 m | 905 ± 5 nm |  |
| [SPD1200D03](https://erdilrf.com/models/spd1200d03/) | A | **see notes** | 8 B / 2 B | **undocumented** | 0.2-1200.0 m | 905 nm | manual contradicts itself on baud; no scaling statement |
| [LRF22VB](https://erdilrf.com/models/lrf22vb/) | B | 460800 | 4 B / 2 B | mm | 0.05-20.0 m | 905 nm |  |
| [LRF50VB](https://erdilrf.com/models/lrf50vb/) | B | 460800 | 4 B / 2 B | mm | 0.05-50.0 m | 905 nm |  |
| [LRF50H](https://erdilrf.com/models/lrf50h/) | B | 460800 | 4 B / 2 B | cm | 0.05-50.0 m | 905 nm |  |
| [LRF100H](https://erdilrf.com/models/lrf100h/) | B | 460800 | 4 B / 2 B | cm | 0.05-100.0 m | 905 nm |  |
| [LRF200H](https://erdilrf.com/models/lrf200h/) | B | 460800 | 4 B / 2 B | cm | 0.05-200.0 m | 905 nm |  |
| [LRF300H](https://erdilrf.com/models/lrf300h/) | B | 460800 | 4 B / 2 B | cm | 0.05-300.0 m | 905 nm |  |
| [LRF600H](https://erdilrf.com/models/lrf600h/) | B | 460800 | 4 B / 2 B | cm | 0.05-600.0 m | 905 nm |  |
| [LRF1500H](https://erdilrf.com/models/lrf1500h/) | B | 460800 | 5 B / 3 B | cm | 0.05-1500.0 m | 905 nm | only 5-byte frame in the catalogue; see protocol-B doc |
| [LRF10VB](https://erdilrf.com/models/lrf10vb/) | (not published) | - | - | - | - | 940 nm | Upstream has not published a manual for this model (940 nm, 0.05-9 m). |
| [SPD1200S2G](https://erdilrf.com/models/spd1200s2g/) | (not published) | - | - | - | - | 905 nm ± 5 nm | Upstream has not published a manual for this model (0.1-1200 m, with gyro). |

## Where the numbers come from

| Field | Source |
|---|---|
| Family, frame length, distance bytes, checksum | the model manual's communication-protocol section (`SECTION 11 Source Protocol Transcription` in the family-A manuals, `Communication Protocol: UART` in the family-B manuals) |
| Default baud | the same section's interface table |
| Unit | family A: "all measurement results are output as the actual value × 10", with the metre unit taken from the model's own ranging-range row; family B: the manual's own worked example, "the measuring distance is 4354cm" (H) or "4354mm" (VB) |
| Range | the model's ranging-range row in its source technical table |
| Wavelength | the model's source technical table |

## Two models with no published protocol

`LRF10VB` and `SPD1200S2G` are in the catalogue but ERDI has not published a
communication manual for them. This repository therefore does **not** ship a
driver for them, and `get_model()` raises rather than falling back to a
sibling model. Ask via <https://erdilrf.com/contact/>.

## Wavelength note

`LRF10VB` is the only 940 nm model in an otherwise 905 nm catalogue. It is
listed here as published, not normalised to 905 nm.
