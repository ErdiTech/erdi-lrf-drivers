# Changelog

## Unreleased
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
