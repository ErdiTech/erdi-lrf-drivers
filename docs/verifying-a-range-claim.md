# Verifying a range claim before you design around it

A published maximum range is a number plus a test condition. If you only take the number, you are
designing against a target you may never see. This note is the check we run on any rangefinder datasheet,
including our own.

## The four things a range figure needs

1. **Target size and reflectance.** "3000 m" against a 70%-reflectivity building is not 3000 m against a
   person or a wire.
2. **Atmospheric visibility.** Several of our long-range figures are quoted at visibility ≥15 km or ≥26 km.
   On a hazy day the same module ranges far less.
3. **The beam footprint at that distance.** Divergence × range. A target smaller than the footprint is not
   fully illuminated, so the return energy drops and the published maximum does not apply.
4. **The update rate and supply** the figure was taken at — the same module can draw twice the power at 10 Hz
   as at 1 Hz, and some modules quote different ranges at different rates.

## A worked check

Take two modules from the open dataset and price them against a 0.5 m target at 2 km:

| Model | Band | Published max | Divergence | Footprint at max | Mass | Mass per km |
|---|---|---|---|---|---|---|
| LRF3000A1 | 905 nm | 3 km (70% building, visibility ≥4 km) | 10 mrad | **30 m** | 12 g | 4.0 g/km |
| LRF1829C | 1535 nm | 23 km (6×6 m diffuse, ≥30% reflectance, visibility ≥30 km) | 0.3 mrad | **6.9 m** | 400 g | 17.4 g/km |

At 2 km, LRF3000A1's beam is `10 mrad × 2 km = 20 m` wide. A 0.5 m target fills 2.5% of it — the published
3 km figure was earned on something 60 times larger. LRF1829C's beam at 2 km is `0.3 × 2 = 0.6 m`, which still
does not fit inside 0.5 m, but is close enough that the return is plausible.

**Neither module is "wrong". Both numbers are true. Only one of them is true for a 0.5 m target.**

## The check, in one command

```bash
python tools/erdi_select.py --url https://specs.erdilrf.com/data/erdi-lrf-specs.json \
    --need-range 2000 --target 0.5
```

It prints, per module, the footprint at your distance and one of two verdicts: `fits` or
`target smaller than beam`. That is the whole test — it will not tell you what the return will be, only
whether the published maximum was ever about your target.

## What we will not do

We will not extrapolate a range to a target the manufacturer did not test, and we will not quote a range
without its condition. If a figure in our dataset is missing a condition, the dataset says so rather than
silently inventing one.

Source: <https://specs.erdilrf.com/data/range-conditions> (verbatim conditions) ·
<https://specs.erdilrf.com/data/footprint> (footprint and mass per km) ·
<https://specs.erdilrf.com/data/power> (power, with the statement each figure came from).
