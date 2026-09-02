# Protocol A — 8-byte `55 AA` command/response

Used by 14 models: `LR1000E2/E4`, `LR1200E2/E4`, `LR1500E2/E4`, `LR2000E2/E4`,
`LRF1200A1`, `LRF3000A1`, `SPD1200N0/N2/N4`, `SPD1200D03`.

Every row below ends with the manual sentence it came from. `<MODEL>.txt` refers
to that model's own manual transcription; the wording is identical across the
eight LR-series manuals unless a row says otherwise.

## Link layer

| Field | Value | Source |
|---|---|---|
| Interface | UART-TTL, 3.3 V | "Communication mode: using serial communication mode" — LRF3000A1 |
| Default baud | 115200 | "Source default baud rate: 115200. Data bits: 8. Frame length: 8 bytes." — LR1000E2 |
| Data bits / stop / parity | 8 / (not stated) / (not stated) | "Data bits: 8" — LR1000E2. Stop bits and parity are **not stated** in the family-A protocol sections. |
| Frame length | 8 bytes, both directions | "Frame length: 8 bytes" — LR1000E2 |
| Radix | hexadecimal | "All transmitted and received data is hexadecimal." — LR1000E2 |
| Baud (SPD1200D03) | **conflict, unresolved** | "The PDF protocol section states 115200 bps as default, while the technical table states 15200 bps (factory) / 9600 bps." and "Do not select a host baud rate until the delivered unit configuration is confirmed." — SPD1200D03 |

## Frame layout

```
byte    0    1    2          3    4    5    6      7
       55   AA   Function   D1   D2   D3   D4   Checksum
```

Source: "Frame Header (H) | Frame Header (L) | Function Code | D1 | D2 | D3 | D4 | Checksum" — LR1000E2 source row 1.

## Checksums — the two are different, and the manual says so

| Direction | Formula | Source |
|---|---|---|
| Host → module | `SUM(Function + D1 + D2 + D3 + D4) & 0xFF` | "Source transmit checksum formula: SUM(Function Code + DATA1 + DATA2 + DATA3 + DATA4), lower 8 bits." — LR1000E2 |
| Module → host | `SUM(0x55 + 0xAA + Function + D1 + D2 + D3 + D4) & 0xFF` | "Source reply checksum formula: SUM(Frame Header (H) + Frame Header (L) + Function Code + DATA1 + DATA2 + DATA3 + DATA4), lower 8 bits." — LR1000E2 |

> "The source warns that the transmit and response calculations differ." — LR1000E2
>
> "The verification content for sending and receiving may differ, so please pay
> attention to discrimination." — LRF1200A1, LRF3000A1

The two scopes differ by exactly `0x55 + 0xAA = 0xFF`, so a driver that uses the
transmit formula on replies will be off by one everywhere and appear to work
only when the checksum happens to wrap. This is the most likely family-A
integration bug; `python/tests/test_protocol_a.py` pins both formulas.

## Commands

| Function | Direction | Frame | Source |
|---|---|---|---|
| `0x88` single-shot | send | `55 AA 88 FF FF FF FF 84` | "Single-Shot Ranging \| Send \| 55 AA 88 FF FF FF FF 84" — LR1000E2 row 7 |
| `0x88` single-shot | reply | `55 AA 88 STA FF DIS_H DIS_L SUM` | "Single-Shot Ranging \| Reply \| 55 \| AA \| 88 \| STA \| FF \| DIS_H \| DIS_L \| SUM[1:7]" — row 8 |
| `0x89` continuous | send | `55 AA 89 FF FF FF FF 85` | "Continuous Ranging \| Send \| 55 AA 89 FF FF FF FF 85" — row 11 |
| `0x89` continuous | reply | `55 AA 89 STA FF DIS_H DIS_L SUM` | row 12 — **but see the protocol hold below for LRF1200A1 / LRF3000A1** |
| `0x8E` stop | send | `55 AA 8E FF FF FF FF 8A` | "Stop Ranging \| Send \| 55 AA 8E FF FF FF FF 8A" — row 15 |
| `0x8E` stop | reply | `55 AA 8E STA FF FF FF SUM` | "PDF p8 / stop reply → 55 AA 8E STA FF FF FF SUM[1:7]" — SPD1200D03 (the LR-series row prints six cells; see Known gaps) |
| `0x8A` angle | send | `55 AA 8A FF FF FF FF 86` | "Angle Measurement \| Send \| 55 AA 8A FF FF FF FF 86" — row 19 |
| `0x8A` angle | reply | `55 AA 8A STA FF ANG_H ANG_L SUM` | row 20. "Effective only for modules equipped with an angle sensor" — row 21 |
| `0x80` self-test | reply only | `55 AA 80 STA 00 [00] ErrCode SUM` | "Self-Test Information \| Reply \| 55 \| AA \| 80 \| STA \| 00 \| ErrCode \| SUM[1:7]" — row 24; SPD1200D03 prints the eight-byte form |
| `0x86` LD constant-ON | send | `55 AA 86 FF FF FF 01 84` (on) / `55 AA 86 FF FF FF 00 83` (off) | row 33. Caution: "Do not keep the constant-ON mode enabled for long periods." Documented for the LR series and SPD1200N series only. |
| `0x70` external circuit enable | send | `55 AA 70 AB CD 00 00 E8` | "External circuit enable \| Send \| 55 AA 70 AB CD 00 00 E8" — LRF3000A1 T5/R6. LRF1200A1 / LRF3000A1 only. |
| `0x71` external circuit disable | send | `55 AA 71 AB CD 00 00 E9` | LRF3000A1 T5/R10. Puts the module into the manual's "secondary low-power mode". |
| baud set | send | `55 AA TYPE FF FF FF FF SUM` | "Baud Rate \| Send \| 55 \| AA \| TYPE \| FF \| SUM[3:7]" — row 28 |
| baud set (SPD1200D03 **only**) | send | `55 AA 01 FF FF FF TYPE SUM` | "PDF p8 / baud request → 55 AA 01 FF FF FF TYPE SUM[3:7]" — SPD1200D03 |

## Status and result fields

| Field | Meaning | Source |
|---|---|---|
| `STA` | `1` = success, anything else = failure | "STA = other value: Measurement failed; STA = 1: Measurement successful" — LR1000E2 row 9 |
| `DIS_H`, `DIS_L` | distance, **big-endian** (`DIS_H << 8 \| DIS_L`) | "DIS_H: High byte of the measurement result; DIS_L: Low byte of the measurement result" — row 9 |
| scaling | raw counts are the value × 10 | "all measurement results are output as the actual value × 10" — row 9. **Not stated for SPD1200D03.** |
| `ANG_H`, `ANG_L` | angle, same layout and ×10 scaling | row 21 |
| `ErrCode` | see the table below | LRF1200A1 / LRF3000A1 T5/R15–R18 |

### Error codes (LRF1200A1 / LRF3000A1)

| Code | Description (verbatim) |
|---|---|
| `0x00` | No echo signal was received |
| `0x16` | Out of range: below the minimum range |
| `0x18` | No echo signal was received |
| `0x00`–`0x07` | Hardware error |

The manual lists `0x00` twice — once as "no echo" and once inside the hardware
error range. Reproduced as printed.

## Baud-rate TYPE tables

Two different tables exist. **Do not merge them.**

| TYPE | LR / LRF-A1 / SPD1200N | SPD1200D03 |
|---|---|---|
| `01` | 9600 | 9600 |
| `02` | 14400 | 14400 |
| `03` | 19200 | 19200 |
| `04` | 38400 | 38400 |
| `05` | 56000 | **57600** |
| `06` | 57600 | **115200** |
| `07` | 115200 | **230400** |
| `08` | 128000 | — |
| `09` | 230400 | — |

Sources: "TYPE = 01: Set baud rate to 9600 bps … TYPE = 09: Set baud rate to
230400 bps" — LR1000E2 row 29; "TYPE 01 = 9600; 02 = 14400; 03 = 19200;
04 = 38400; 05 = 57600; 06 = 115200; 07 = 230400 bps. Restart required." —
SPD1200D03.

Both manuals add that the change is not immediate: "The baud rate change does not
take effect immediately; it becomes effective only after a reboot."

## PROTOCOL HOLD — continuous ranging on LRF1200A1 and LRF3000A1

> "The source-stated continuous-ranging request uses function 0x89 while its
> recorded reply uses 0x88. This document preserves both and does not authorize
> continuous operation or a response parser."
>
> "PROTOCOL HOLD  Continuous ranging remains an engineering-confirmation item
> because the source request and reply function bytes differ."

Both drivers in this repository refuse continuous ranging on these two models
unless the caller explicitly acknowledges the hold
(`stream(acknowledge_protocol_hold=True)` in Python,
`startContinuous(true)` in Arduino). Single-shot ranging is unaffected.

## Known gaps

| Gap | What the manual does or does not say |
|---|---|
| Stop bits and parity | The family-A protocol sections state "Data bits: 8" and nothing about stop bits or parity. This repository does not set them and leaves the pyserial/Arduino defaults (8N1) in place; confirm with ERDI if your unit disagrees. |
| `SPD1200D03` default baud | Its own manual states 115200 bps in the protocol section and 15200/9600 bps in the technical table, and instructs the reader not to choose until the delivered unit is confirmed. The drivers therefore require an explicit baud rate for this model. |
| `SPD1200D03` distance scaling | No scaling statement of any kind appears. The Python driver returns raw counts and `metres = None`; the Arduino driver returns `NAN`. Nothing is inferred from the sibling SPD1200N models. |
| `SPD1200D03` `STA` semantics | Not stated, so the status byte is returned unchecked rather than judged against `1`. |
| `SPD1200N0/N2/N4` transmit checksum | The transcription says request and reply scopes differ but does not print the transmit formula. The drivers use the family-A transmit formula, which reproduces every example frame these manuals do print (`55 AA 88 FF FF FF FF 84`, `… 89 … 85`, `… 8E … 8A`, `… 8A … 86`). Flagged rather than assumed silently. |
| Self-test `ErrCode` byte position | The LR-series row prints seven cells (`55 \| AA \| 80 \| STA \| 00 \| ErrCode \| SUM`), putting ErrCode at D3; SPD1200D03 prints the full eight bytes with ErrCode at D4. The Python driver exposes both candidates (`error_code_d3`, `error_code_d4`) instead of picking one. |
| Stop-reply width | The LR-series stop reply row prints six cells; only SPD1200D03 prints the padded eight-byte form. Treated as an eight-byte frame with the row's merged cells expanded. |
| `LRF1200A1` / `LRF3000A1` continuous | See PROTOCOL HOLD above. |
| Distance unit | The protocol sections state only the ×10 scaling, never the unit itself. Metres comes from each model's own ranging-range row in its source technical table. |
