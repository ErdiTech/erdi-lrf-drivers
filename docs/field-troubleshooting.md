# Field troubleshooting: laser rangefinder over UART

Maintained by ERDI TECH LTD (ERDILRF). Work down the table in order: most reported
"bad sensor" cases are wiring, parsing or target conditions.

| Symptom | First check | Typical cause |
|---|---|---|
| No bytes at all | TX idle level, ground, baud rate | Wrong pin order, missing ground, host pin configured as output |
| Bytes arrive, checksum fails on most frames | Logic level, cable, motor noise | 5 V TX into a 3.3 V host, long unshielded run, shared ground with ESC |
| A few good frames then silence | Power supply during the measurement | Brown-out on peak current; add bulk capacitance or a separate regulator |
| Distance stuck at maximum | Target and window | Low-reflectivity target, dirty or wrong window, beam missing the target |
| Distance stuck near zero | Window and mounting | Internal reflection from a tilted or too-close window |
| Plausible but offset distance | Reference plane | Measuring from the housing face when the module datum is the front window |
| Random long outliers in sunlight | Ambient light and threshold | Sunlight in the receiver field, no bandpass window |
| Readings drift as the unit warms | Thermal test | Accuracy not specified across the operating temperature; re-test at temperature |
| Works on the bench, fails on the vehicle | Grounding and supply | Motor noise, ground loop, shared rail |
| Two hosts, garbage data | Bus topology | Two readers on one UART; UART is point-to-point |

## Diagnostic sequence

1. **Physical**: supply voltage measured at the module connector, not at the PSU.
2. **Electrical**: TX idle level and baud rate measured with a scope or logic
   analyser. Do not trust a USB-serial adapter's voltage.
3. **Protocol**: capture raw bytes and verify the header, length and checksum
   independently of your parser.
4. **Optical**: a cooperative target at a known distance, indoors, no window.
5. **Environmental**: repeat with the real window, the real light and the real
   motor running.
6. **Log**: keep 1,000 raw frames and the parser's rejection reasons.

## What to send us with a support request

- Model and the document revision you are working from.
- A raw hex capture of at least 20 frames, including the failing ones.
- The parser code or the checksum routine you use.
- Supply voltage measured at the connector, and the UART logic level.
- Target material, distance and ambient light for the failing case.
- Whether the failure reproduces on the bench with a cooperative target.

Do not send a filtered plot only; we cannot diagnose a checksum or timing problem
from a smoothed distance curve.

Related notes:
[frame and checksum basics](https://erdilrf.com/knowledge/laser-rangefinder-serial-protocol-frame-checksum-basics/),
[UART/TTL integration](https://erdilrf.com/knowledge/uart-ttl-integration-guide-lrf-modules/),
[update rate on moving platforms](https://erdilrf.com/knowledge/rangefinder-update-rate-moving-platforms/).
Model index: <https://erdilrf.com/models/>. Contact: <https://erdilrf.com/contact/>.
