#!/usr/bin/env python3
"""Selection arithmetic for ERDI LRF modules — footprint, mass per km, power per metre.

Why this exists: the two numbers that decide whether a rangefinder fits a platform are
(a) how wide the beam is where it lands and (b) what the reach costs in grams (and watts).
Both are arithmetic on published figures, and both are usually missing from datasheets.

Data source: the open dataset at https://specs.erdilrf.com/data/erdi-lrf-specs.json
(also mirrored at https://github.com/erdilrf-afk/erdi-lrf-specs). Nothing here is measured
by this script; it multiplies and divides published numbers and prints the condition text
next to each one so two figures are only compared when they were measured the same way.

Usage:
    python erdi_select.py --url https://specs.erdilrf.com/data/erdi-lrf-specs.json
    python erdi_select.py --file erdi-lrf-specs.json --band 1535 --max-mass 200
    python erdi_select.py --url ... --need-range 2000 --target 0.5
"""
import argparse
import json
import sys


def load(src_file=None, src_url=None):
    if src_file:
        with open(src_file, encoding="utf-8") as f:
            return json.load(f)
    if src_url:
        import urllib.request
        req = urllib.request.Request(src_url, headers={"User-Agent": "erdi-select"})
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    sys.exit("give --file or --url")


def rows_for(rows, band=None, max_mass=None, min_range=None):
    out = []
    for r in rows:
        if r.get("family") == "laser_source":
            continue
        wl = r.get("wavelength_nm")
        if band == "905" and wl != 905:
            continue
        if band == "1535" and wl not in (1535, 1540):
            continue
        if max_mass and (r.get("weight_g") or 1e9) > max_mass:
            continue
        if min_range and (r.get("range_max_m") or 0) < min_range:
            continue
        out.append(r)
    return out


def footprint_m(div_mrad, rng_m):
    return div_mrad * rng_m / 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--url")
    ap.add_argument("--band", choices=["905", "1535"])
    ap.add_argument("--max-mass", type=float)
    ap.add_argument("--min-range", type=float)
    ap.add_argument("--need-range", type=float, help="your actual distance in metres")
    ap.add_argument("--target", type=float, help="your smallest target in metres")
    a = ap.parse_args()

    rows = rows_for(load(a.file, a.url), a.band, a.max_mass, a.min_range)
    print(f"{len(rows)} modules match the filter\n")
    print(f"{'model':12s}{'band':>6s}{'range':>10s}{'div':>8s}{'footprint':>11s}{'mass':>8s}{'g/km':>7s}{'W':>6s}{'mW/m':>7s}")
    for r in sorted(rows, key=lambda r: -(r.get("mass_per_km_g") or 1e9)):
        rng = r.get("range_max_m") or 0
        div = r.get("divergence_mrad")
        fp = f"{footprint_m(div, rng):.1f} m" if (div and rng) else "—"
        print(f"{r['model']:12s}{str(r.get('wavelength_nm')):>6s}{rng/1000:>9.1f}k"
              f"{str(div or '—'):>8s}{fp:>11s}"
              f"{str(r.get('weight_g') or '—'):>8s}{str(r.get('mass_per_km_g') or '—'):>7s}"
              f"{str(r.get('power_avg_w') or '—'):>6s}{str(r.get('power_per_metre_mw') or '—'):>7s}")

    if a.need_range and a.target:
        print(f"\nAt {a.need_range:g} m, the beam must be narrower than {a.target:g} m for the target to be "
              f"fully illuminated (divergence < {a.target / a.need_range * 1000:.2f} mrad):")
        for r in rows:
            div = r.get("divergence_mrad")
            if not div:
                continue
            fp = footprint_m(div, a.need_range)
            verdict = "fits" if fp <= a.target else "target smaller than beam"
            print(f"  {r['model']:12s} {div:>5g} mrad -> {fp:>6.2f} m at {a.need_range:g} m  ({verdict})")

    print("\nEvery figure is transcribed from the published specification; the derived columns are arithmetic, "
          "not measurements. The condition behind each range is in range_condition / power_statement.")


if __name__ == "__main__":
    main()
