# Changelog

## 0.1.3 - 2026-11-07
- `LRF10VB` is now driven (family B, 460800 baud, 4-byte `5C` frame, millimetres, out of range 65535), transcribed from the LRF10VB Specification V3.0. Start/stop ranging only; the manual's baud-rate row reprints the LRF50VB serial-number frames, so `set_baud` is not offered.

## 0.1.2 - 2026-11-06
- Tag-triggered release pipeline: GitHub Release, PyPI and PlatformIO Registry published from one `v*` tag.
- Arduino library: added README and LICENSE; version aligned with the Python package.

## 0.1.1
- Python package `erdi-lrf` first PyPI release.
