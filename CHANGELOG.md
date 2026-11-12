# Changelog

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
