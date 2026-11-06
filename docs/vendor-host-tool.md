# What the ERDI serial host tool does with units and frames

The factory ships a Windows serial tool (`Suretech-Display.exe`, Qt 5) that plots
the module's distance stream. Its build output includes unstripped object files,
so the behaviour below was read directly from the compiled code rather than
guessed from the user interface. This matters for one question integrators keep
asking: **does the VB series output millimetres or centimetres?**

Everything here is static analysis of the tool. Nothing was observed on a live
serial port.

## The model drop-down decides the display unit, not the module's unit

The tool's model list has two entries per VB model — `VB22A(mm)` and
`VB22A(cm)` — plus one entry per H model (`WT50A` … `WT1500A`). Internally they
are grouped into three lists:

| List | Entries | What the receive path does with a `5C` frame |
|---|---|---|
| `TYPE_MM` | `VB02A(mm)`, `VB10A(mm)`, `VB22A(mm)`, `VB50A(mm)` | shows the raw 16-bit value as `N mm` |
| `TYPE_CM_VIRTUAL` | `VB02A(cm)`, `VB10A(cm)`, `VB22A(cm)`, `VB50A(cm)` | divides the raw value by 10 (truncating) and shows `N cm` |
| `TYPE_CM` | `WT50A`, `WT100A`, `WT200A`, `WT300A`, `WT600A`, `WT1500A` | shows the raw value as `N cm` |

The frame parser is identical for all three groups: `5C`, distance low byte,
distance high byte, checksum `~(sum of the bytes between header and checksum)`,
with a 3-byte distance only for `WT1500A`. Switching the model entry sends
**no command to the module**; it only changes the frequency list, the axis
title and the display scaling.

So the `(cm)` entries are a convenience conversion in the tool (the list is
literally named "virtual cm"). **The VB modules always stream millimetres**, as
their manuals state. A driver that reads the VB wire value as centimetres would
be off by 10x; see the unit table in [protocol-B-5C.md](protocol-B-5C.md#units--per-model-never-per-family).

## Commands the tool sends

Both match the published command table:

| Button | Bytes | Notes |
|---|---|---|
| Set baud rate | `5A 06 02 <baud/100, little-endian> <check>` | 9600 → `60 00`, 19200 → `C0 00`, 38400 → `80 01`, 115200 → `80 04`, 230400 → `00 09`, 256000 → `00 0A`, 460800 → `00 12`, 921600 → `00 24` |
| Set frequency | `5A 0B 02 <divisor, little-endian> <check>` | divisor = base / f − 1; base is 10 000 for `VB22A` and `VB50A` (both `(mm)` and `(cm)` entries) and 1 000 000 for the `WT` models |

The frequency choices offered are 1/10/20/50/100/200 Hz for `VB22A` and
1/10/20/50/100 Hz for `VB50A`; `WT` models take a free numeric value.
The tool recognises the replies `5A 86 …` (baud set) and `5A 8B …`
(frequency set) and prints a success message for each.

## One thing the manuals do not describe

With `VB22A(mm)` or `VB50A(mm)` selected (not the `(cm)` entries, not `WT`),
the tool starts a 1-second timer and writes the fixed five bytes
`55 AA 81 00 FA` to the port each tick. Its receive path also accepts an
8-byte frame that starts `55 AA` and ends `FA`, taking bytes 4–5 as a
big-endian distance and displaying it in millimetres.

This looks like a polled request/response mode for the VB series that is not in
the current VB manuals. The published start-ranging command
(`5A 0A 02 02 00 F1`) is what the drivers in this repository use, and the
streaming `5C` frames do not depend on the `55 AA` poll. Treat the poll as
undocumented until the factory confirms what it does.

## Log file format

The tool's "save" button writes one line per received frame:

```
[yyyy-MM-dd hh:mm:ss]    <value>
```

where `<value>` is the integer in the *displayed* unit (millimetres for a
`(mm)` entry, millimetres ÷ 10 for a `(cm)` entry, centimetres for `WT`). Lines
are buffered and appended to the file in blocks of 1000, so a capture shorter
than 1000 frames writes nothing. The file holds decoded values, not the raw
byte stream, so it cannot be replayed through a driver's frame parser; it is
still a usable record of what the module reported.
