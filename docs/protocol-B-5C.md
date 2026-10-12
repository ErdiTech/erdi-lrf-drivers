# Protocol B — free-running `5C` data frames, `5A` command frames

Used by 8 models: `LRF50H`, `LRF100H`, `LRF200H`, `LRF300H`, `LRF600H`,
`LRF1500H`, `LRF22VB`, `LRF50VB`.

These modules stream distance continuously once powered; there is no
request/response for measurements. Configuration uses a separate `5A` frame.

Every row ends with the manual sentence it came from.

## Link layer

| Field | Value | Source |
|---|---|---|
| Interface | UART (VB series and most H models also expose I²C) | "6. Communication Protocol: UART" — LRF22VB |
| Default baud | 460800, adjustable | "UART Baud Rate 460800 (adjustable) Data Bit 8 Stop Bit 1 Parity Bit None" — LRF100H |
| Data / stop / parity | 8 / 1 / none | same row (LRF22VB prints "Parity Bit N/A") |
| Byte order | little-endian, both directions | "this product adopts Hexadecimal Little-Endian Mode" — LRF100H |
| I²C address (VB series) | `0x52`, 7-bit, ≤400 kHz | "The default address is 0x52 (7bit address mode)." — LRF22VB |

> **460800 bps is out of reach for AVR SoftwareSerial.** Use a hardware UART, or
> set the module to a lower documented rate first with the baud command below.

## Data frame

Four-byte form — every model except `LRF1500H`:

```
byte    0     1        2        3
       5C   dist_lo  dist_hi  check
```

Five-byte form — `LRF1500H` only:

```
byte    0     1        2        3        4
       5C   dist_lo  dist_mid dist_hi  check
```

Sources: "Frame Header | Distance 2 Bytes | Check Byte / 5C 02 11 EC" — LRF100H;
"Frame Header | Distance 3 Bytes | Check Byte / 5C 02 11 03 EC" — LRF1500H.

## Checksum

The manuals print both the sentence and the C function:

> "Begin with the second byte and end with the last second byte, find the
> inverse of the sum."

```c
uint8_t Check_Sum(uint8_t *_pbuff, uint16_t _cmdLen)
{
    uint8_t cmd_sum = 0;
    uint16_t i;
    for (i = 0; i < _cmdLen; i++) { cmd_sum += _pbuff[i]; }
    cmd_sum = (~cmd_sum);
    return cmd_sum;
}
```

Worked check: `5C 02 11 EC` → `~(0x02 + 0x11) = ~0x13 = 0xEC`. ✅

## Units — per model, never per family

| Models | Raw count is | Out-of-range marker | Source |
|---|---|---|---|
| `LRF50H`, `LRF100H`, `LRF200H`, `LRF300H`, `LRF600H`, `LRF1500H` | **centimetres** | 65535 (16777215 on LRF1500H) | "the measuring distance is 4354cm, little-endian, range 0-65535cm. When out of range, it would output 65535cm." — LRF100H |
| `LRF22VB` | **millimetres** | 20000 | "the measuring distance is 4354mm, little-endian, Range:0- 20000, When out of range, its output is 20000." — LRF22VB |
| `LRF50VB` | **millimetres** | 50000 | "the measuring distance is 4354mm, little-endian, range 0-50000. When out of range, output would be 50000." — LRF50VB |

The same four bytes `5C 02 11 EC` mean **43.54 m** on an H module and **4.354 m**
on a VB module. Reading the wrong table is a 10x error, which is why this
repository never derives the unit from the family.

## Command frame

```
byte    0     1     2      3 .. 3+len-1    last
       5A    cmd   len       data...       check
```

The reply echoes the command byte with bit 7 set (`0x0D` → `0x8D`).
The checksum covers `cmd`, `len` and `data` — the same `Check_Sum` function.

| # | Command | Send | Return | Source |
|---|---|---|---|---|
| 1 | Read serial no. | `5A 0D 02 0D 0D D6` | `5A 8D 02 10 01 00 00 5F` | LRF50H / LRF1500H |
| 1b | Read serial no. (VB 4-byte form) | `5A 0D 04 0D 0D 0D 0D BA` | `5A 8D 04 10 01 00 00 5D` | LRF22VB. "10 01 00 00 means the serial no. is 272: little-endian" |
| 2 | Read software version | `5A 16 02 16 16 BB` | `5A 96 02 03 02 62` | "03 02 means the software version no. is V2.3 … Add a point (.) in the middle." |
| 3 | Set baud rate | `5A 06 02 80 04 73` | `5A 86 02 80 04 F3` | "80 04 as a decimal is 1152: little-endian, it means the baud rate is set to 115200=1152*100" |
| 4 | Set frequency | `5A 0B 02 E7 03 08` | `5A 8B 02 E7 03 88` | "E7 03 (little-endian) represents the frequency divisor: 999." |
| 5 | Read frequency | `5A 1B 02 1B 1B AC` | `5A 9B 02 31 00 31` | "31 00 (little-endian) indicates the current divisor: 49." |
| 6 | Switch to I²C | `5A 1F 02 1F 1F A0` | `5A 9F 02 1F 1F 20` | VB series. "Response confirms successful switch." |
| 7 | Stop ranging | `5A 0A 02 00 00 F3` | `5A 8A 02 00 00 73` | `LRF50H`, `LRF22VB`, `LRF50VB` |
| 8 | Start ranging | `5A 0A 02 02 00 F1` | `5A 8A 02 02 00 71` | `LRF50H`, `LRF22VB`, `LRF50VB` |

Every frame in this table verifies against the manual's own `Check_Sum`
function; `python/tests/test_protocol_b.py` asserts all of them.

### Baud-rate codes

The two data bytes are `bps ÷ 100`, little-endian:

| Bytes | Decimal | Baud |
|---|---|---|
| `60 00` | 96 | 9600 |
| `C0 00` | 192 | 19200 |
| `80 01` | 384 | 38400 |
| `80 04` | 1152 | 115200 |
| `00 09` | 2304 | 230400 |
| `00 0A` | 2560 | 256000 |
| `00 12` | 4608 | 460800 |

> "Any other baud rate is not available" — LRF22VB.
> "Other baud rate settings would not get respond." — LRF1500H.

### Output frequency — the divisor base is model specific

`f = base / (divisor + 1)`

| Models | Base | Source |
|---|---|---|
| `LRF22VB`, `LRF50VB` | 10 kHz | "Output frequency: f=10000/(999+1)=10Hz" |
| `LRF50H`, `LRF100H`, `LRF200H` | 1 MHz | "the corresponding serial data output frequency f=1000000/(999+1)=1000Hz" |
| `LRF300H`, `LRF600H`, `LRF1500H` | **not documented** | no divisor formula appears in these manuals |

The drivers refuse to set or read frequency on the three models with no
published formula rather than borrowing a sibling's base.

## I²C register map (VB series)

| Address | Definition | Access | Remarks |
|---|---|---|---|
| `0x00` | Distance, high byte | R | 2 bytes for distance |
| `0x01` | Distance, low byte | R | |
| `0x02` | Laser control | W | 0 = laser off, 1 = laser on |
| `0x03` | LiDAR ID | R | default `0x4A`, for read/write tests |
| `0x04` / `0x05` | I²C → UART switch | W | "Write 0xA5 to register 0x04 and 0x5A to register 0x05 simultaneously" |
| `0x06` / `0x07` | Software version, high / low | R | |
| `0x08`–`0x0B` | Serial number, high → low | R | 4 bytes, range 1–4294967294 |
| `0x0C` | I²C slave address | R/W | 7-bit, range 0–127 |
| `0x0D` | Factory reset | W | write `0x01` |

Note the I²C distance registers are documented **high byte first**, while the
UART data frame is little-endian. Both are reproduced as printed.

This repository's drivers implement the UART path only; the register map is
included so an I²C integrator does not have to open the PDF.

## Known gaps

| Gap | What the manual does or does not say |
|---|---|
| `LRF1500H` example frame vs its own checksum | The manual prints `5C 02 11 03 EC`, but its own `Check_Sum` gives `~(0x02+0x11+0x03) = 0xE9`. `0xEC` is the correct byte for the *four*-byte frame `5C 02 11 EC` used by the other models, so the example looks copied. The drivers implement the printed function; a test asserts the discrepancy so it cannot be silently "corrected". |
| `LRF1500H` out-of-range value | Section 5.2 says the field is 3 bytes and out-of-range outputs 16777215; section 6 says "it would output 0xFFFF (16777215)", and `0xFFFF` is 65535. The drivers use 16777215, matching the stated field width. Reported, not resolved. |
| `LRF50VB` serial-read example checksum | The printed request `5A 0D 02 0D 0D 0D 0D BC` does not satisfy `Check_Sum` for either length byte (`0x02` → `0xBE`, `0x04` → `0xBA`); its printed reply does verify. The drivers build the request with `Check_Sum`. |
| `LRF300H`, `LRF600H`, `LRF1500H` frequency | No divisor formula published; set/read frequency is not exposed for these models. |
| `LRF50H`, `LRF100H`, `LRF300H`, `LRF600H`, `LRF1500H` I²C address | Not stated in their manuals (`LRF200H` states `0x33`, the VB series `0x52`). Nothing is extrapolated. |
| Start/stop ranging | Documented only for `LRF50H`, `LRF22VB` and `LRF50VB`. The other five free-run from power-up and the drivers do not send a start command to them. |
| `LRF22VB` default output frequency | Listed as unresolved in our engineering notes; the supported set is documented (200/100/50/20/10/1 Hz) but the power-on default is not. |
| `LRF50VB` supported frequency list | The set-frequency row lists 100/50/20/10/1 Hz and the read-frequency row lists 200/100/50/20/10/1 Hz. Both are reproduced; the manual does not reconcile them. |
