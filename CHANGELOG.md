# Changelog

## Unreleased

## 0.1.7 - 2026-11-15
- `5A` command replies: a well-formed frame that answers a different command no longer aborts the call. The bytes of a `5C` data frame can form such a frame by coincidence (`5C 5A A5 00` followed by `5A`); the reader now keeps listening for its own reply and raises `FrameError` for the other frame only if nothing else arrives before the timeout.
- `LRF50VB` / `LRF22VB` serial number: if only a reply to some other command arrives for the first printed request form, the other form is now tried as well (it used to be tried only when the module stayed completely silent).
- The longer-form wait is documented and tested: a module that only sends the two-byte serial reply answers after one full timeout.

## 0.1.6 - 2026-11-15
- Fix: `5A` command replies are now cut by their length byte. The reader used to accept the first prefix whose checksum verified, so an `LRF50VB` serial-number reply such as `5A 8D 02 10 01 5F 00 00` (serial 6226192) came back as 272, and a reply whose first data byte happened to match a shorter checksum could fail. For the `LRF50VB` / `LRF22VB` serial number the four-data-byte reply printed in the manuals is preferred; the two-byte form is accepted if that is all the module sends. Stale input is discarded before each command is sent.

## 0.1.5 - 2026-11-15
- Fix: `LRF50VB` read-serial frame. Its manual prints `5A 0D 02 0D 0D 0D 0D BC`, which does satisfy `Check_Sum`; earlier notes calling it a checksum mismatch were wrong. The driver now sends that exact frame to `LRF50VB` (and `5A 0D 04 ... BA` to `LRF22VB`), and the reply parser accepts the printed `5A 8D 02 10 01 00 00 5F` with all four data bytes. If a VB module does not answer its own printed frame, `read_serial_number()` tries the other printed form once.
- `tools/erdi_capture.py`: cross-platform raw UART recorder (pyserial). Receive-only unless `--start e2|vb` is given; writes `.bin`, hex `.txt` and a `.json` summary, with a live frame count and median every 5 s. Self-tests in `tools/test_erdi_capture.py` run in CI.
- `docs/ardupilot-test-kit/`: bench test instructions, wiring tables and Mission Planner parameter files for ArduPilot test builds with the ERDI drivers (`RNGFNDx_TYPE` 49 VB, 50 H, 51 E2). Type 51 exists only on a test branch, not upstream.

## 0.1.4 - 2026-11-12
- Package, Arduino library and citation metadata now name the publisher as ERDI TECH LTD (matches LICENSE), including the Arduino library LICENSE and source headers.
- Per-model range data re-checked against the erdilrf.com catalog (2026-11-12): all 22 catalogue models match the standard catalog range (SPD1200N0/N2/N4 = 0.2-1,200 m; the 1,500 m night-time figure is not used as a limit). No code or protocol changes.

## 0.1.3 - 2026-11-07
- `LRF10VB` is now driven (family B, 460800 baud, 4-byte `5C` frame, millimetres, out of range 65535), transcribed from the LRF10VB Specification V3.0. Start/stop ranging only; the manual's baud-rate row reprints the LRF50VB serial-number frames, so `set_baud` is not offered.

## 0.1.2 - 2026-11-06
- Tag-triggered release pipeline: GitHub Release, PyPI and PlatformIO Registry published from one `v*` tag.
- Arduino library: added README and LICENSE; version aligned with the Python package.

## 0.1.1
- Python package `erdi-lrf` first PyPI release.
