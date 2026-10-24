# Mixed-target returns: validating a range when the beam hits two things

A laser rangefinder reports one distance per measurement. When the beam footprint covers more than one surface — a railing in front of a wall, a branch in front of a hillside, a protective window plus the target behind it — the module still reports one number. The question is whether that number is the surface you meant to measure.

This note is a short field procedure for deciding that, and for making the failure visible instead of silent.

## Why a mixed return happens

The spot at range is roughly `R × θ` wide (`θ` in radians). At 100 m a 4.5 mrad beam is about 0.45 m across. Anything inside that footprint can contribute photons to the receiver:

- the intended target,
- a nearer object clipping the edge of the beam,
- a window, mesh or grille in the optical path,
- the background behind a target smaller than the spot.

Most modules pick the strongest return, or the first return above a threshold, depending on their design. Either policy can be right for your application and wrong for the next one. That is why the arithmetic matters more than the marketing number.

## A validation procedure that works with one module

1. **Map the footprint.** Compute the spot diameter at your minimum and maximum operating range. Compare it with the smallest target you must measure. If the spot is larger than the target, assume the background can win.
2. **Test three targets at the same range**: a cooperative flat plate, a small target on a stand, and the same small target with a background 2 m behind it. A module that reports the background only in the third case has a mixed-return behaviour you can plan around.
3. **Move the small target across the beam.** Sweep it laterally in steps of a quarter of the spot diameter and record the reported distance. A sudden jump to the background distance marks the edge of reliable detection.
4. **Check the failure mode.** Does the module hold the last value, return an error flag, or return a plausible wrong number? The first two are workable; the third needs filtering in your host software.
5. **Repeat with the protective window fitted.** A tilted window should send its reflection out of the receiver path; a flat window in line with the beam can add a short, strong return that competes with the target.

## What to log

For each configuration, record: range, spot diameter, target size, background distance, reported distance, signal/quality field if the protocol exposes one, and ambient light. A test that only records "it worked" cannot be debugged later.

If your module exposes a signal strength or a "receive gap" style alarm, log it alongside the distance. A weak-but-valid return and a strong return from the wrong surface look identical in the distance field alone.

## Design consequences

- Mount the module so the beam does not graze the airframe, a skid or a cable. A 2 cm object at 0.5 m is inside almost any footprint.
- Prefer a narrower beam when the target is small and far; prefer a wider beam when pointing jitter dominates and the target fills the spot.
- If your application cannot tolerate a wrong-but-plausible number, filter on signal quality and on the consistency of consecutive samples, not only on range limits.

Further reading from our engineering notes:

- Mixed-target return validation: https://erdilrf.com/knowledge/laser-rangefinder-mixed-target-return-validation/
- Beam divergence and spot size: https://erdilrf.com/knowledge/rangefinder-beam-divergence-spot-size/
- Protective window acceptance: https://erdilrf.com/knowledge/laser-rangefinder-protective-window-acceptance/
- Module list and datasheets: https://erdilrf.com/models/

*Disclosure: this note is maintained by integration support at ERDI TECH LTD (erdilrf.com), a manufacturer of laser rangefinder modules. The procedure above is generic and applies to modules from any vendor.*
