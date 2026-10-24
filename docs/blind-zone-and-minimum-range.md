# Blind zone and minimum range: the first metre is the hard part

Datasheets lead with maximum range. The number that causes most installation problems is the minimum one.

A laser rangefinder needs the outgoing pulse to have left the optics before the receiver can accept the return. That timing, plus the receiver's recovery behaviour, sets a **blind zone**: a distance below which the module either reports nothing, reports a fixed value, or reports a reflection from its own window.

## Where the blind zone comes from

- **Pulse width and gating.** The receiver is effectively deaf while the transmitter fires. A return that arrives inside that window cannot be separated from the transmit pulse.
- **Optical crosstalk.** A protective window, a filter or a dirty lens can reflect a small part of the pulse straight back into the receiver. At short distances that reflection can be stronger than the target return.
- **Recovery time.** After a strong return (a wall at 30 cm), the receiver may need time to return to normal sensitivity.

The practical consequence: a module specified for 0.3 m may still be unreliable at 0.35 m against a dark, angled target, and perfectly fine at 0.3 m against a white plate. The blind zone is not a single number — it is a curve that depends on target reflectivity, angle and ambient light.

## Mounting around it

1. **Offset the module** so the closest surface you must measure is outside the blind zone, or accept that the closest reading will be invalid and handle it in software.
2. **Never let the beam hit the vehicle.** On a small drone, the skid or the camera housing can sit inside the blind zone. Tilt the module a few degrees or move it forward.
3. **Treat the first samples after power-up as suspect.** Many modules need a few frames to settle; discard them explicitly rather than smoothing them into the output.
4. **Define the invalid value.** Decide in advance whether "no return" is `-1`, `0`, a NaN, or a held previous value, and make the parser express that rather than folding it into a plausible distance.

## A quick bench check

Put a target at the shortest distance you care about. Move it 5 cm closer in steps until the reported distance stops tracking. Record where it breaks and what the module reports there (no return, zero, or the last good value).

Repeat with a dark target and with a tilted target. The break point will move. That range — not the datasheet's minimum — is what your control loop must tolerate.

Further reading:

- Minimum measuring distance and blind zone: https://erdilrf.com/knowledge/minimum-measuring-distance-blind-zone/
- Mixed-target return validation: https://erdilrf.com/knowledge/laser-rangefinder-mixed-target-return-validation/
- Module list and datasheets: https://erdilrf.com/models/

*Disclosure: maintained by integration support at ERDI TECH LTD (erdilrf.com), a manufacturer of laser rangefinder modules.*
