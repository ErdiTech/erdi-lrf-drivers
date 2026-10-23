# Laser rangefinder module evaluation checklist (design-in)

Maintained by ERDI TECH LTD (ERDILRF). This checklist is vendor-neutral in form but
ERDI-specific in the links; it exists because most integration failures we see are
caused by comparing headline range numbers instead of comparing measurement
conditions.

Use it before you request samples, and again before you freeze a mechanical design.

## 1. Define the measurement, not the number

Write down, in one line each:

- target material and approximate reflectivity at the laser wavelength;
- target size at the closest and farthest working distance;
- expected ambient light (indoor, overcast, direct sun);
- required update rate and whether the platform moves during a measurement;
- required accuracy and the acceptable outlier rate;
- mounting envelope, window material, and cable route.

A module that reaches 200 m on a cooperative target may reach a small fraction of
that on a low-reflectivity target in bright light. ERDI publishes the conditions
next to the numbers on each model page, for example
[LRF200H](https://erdilrf.com/models/lrf200h/) distinguishes 90% and 10%
reflectivity cases. Read those conditions as part of the specification.

## 2. Interface and electrical

| Check | Why it matters |
|---|---|
| UART logic level (3.3 V or 5 V TTL) | The supply voltage does not tell you the signal voltage. Confirm both. |
| Supply voltage range and peak current | A module that browns out during a measurement returns plausible-looking bad data. |
| Connector pinout and mating part | Pin order is not standard across vendors. |
| Cable length and shielding | Long unshielded UART runs pick up motor and ESC noise. |
| Start-up time and first valid frame | Some hosts log the boot frame as a measurement. |

Background: [UART/TTL integration guide](https://erdilrf.com/knowledge/uart-ttl-integration-guide-lrf-modules/).

## 3. Protocol and data quality

- Ask for the frame description, not only a driver binary.
- Confirm checksum coverage and what the device does on a bad frame.
- Confirm the unit of the distance field (metres, centimetres, millimetres) and
  whether it is signed.
- Confirm the status/confidence field and its meaning.
- Log raw frames for the first bench session; parsing bugs look like sensor noise.

Protocol notes for the two ERDI families are in
[Protocol A](protocol-A-55AA.md) and [Protocol B](protocol-B-5C.md); the general
checksum pattern is described in
[frame and checksum basics](https://erdilrf.com/knowledge/laser-rangefinder-serial-protocol-frame-checksum-basics/).

## 4. Optical and mechanical

- Spot size grows with distance: diameter is roughly `2 * range * tan(divergence/2)`.
  At long range the spot can be larger than the target.
- Window tilt and coating cause internal reflections that appear as a short false
  range.
- Confirm the reference plane: front face, mounting face, or connector face.
- Check whether the module expects a bandpass window; a plain acrylic window may
  pass ambient light but block or distort the return.

See [beam divergence and spot size](https://erdilrf.com/knowledge/rangefinder-beam-divergence-spot-size/)
and [update rate on moving platforms](https://erdilrf.com/knowledge/rangefinder-update-rate-moving-platforms/).

## 5. Environmental and safety

- Operating and storage temperature, and whether accuracy is specified across it.
- Ingress protection claim and what it actually covers (the optical window is the
  usual weak point).
- Laser class of the module, and the class of the finished system after your
  housing and optics. A module-level class is not a finished-product certification.
- For 1535 nm modules, read [905 nm vs 1535 nm](905nm-vs-1535nm.md) before you
  assume the "eye-safe" label removes the need for an assessment.

## 6. Bench acceptance before design freeze

1. Static test at 10%, 50% and 90% reflectivity targets at three distances.
2. Dynamic test at the intended update rate on a moving target.
3. 30-minute soak at maximum specified ambient temperature.
4. Brown-out test at the minimum supply voltage.
5. EMC check with the real motor/ESC running.
6. 1,000-frame log analysed for outliers and dropouts.

Record the firmware or protocol revision with every log. If a result cannot be
reproduced from the log, it is not a result.

## 7. What to ask the supplier

- Which model revision was shipped, and which document revision applies to it.
- Whether the delivered unit matches the published protocol and electrical table.
- Which fields are calibrated at the factory and which are host-side.
- What the return policy is for evaluation samples.

Model index: <https://erdilrf.com/models/>. Contact:
<https://erdilrf.com/contact/>.
