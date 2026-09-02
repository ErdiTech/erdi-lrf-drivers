"""``erdi-lrf`` command-line interface.

::

    erdi-lrf models
    erdi-lrf info --model LRF3000A1
    erdi-lrf --port COM3 --model LRF3000A1 measure
    erdi-lrf --port /dev/ttyUSB0 --model LRF100H stream --count 20
    erdi-lrf --port COM3 --model LRF22VB info-device
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import __version__
from .errors import ErdiLrfError
from .models import MODELS, UNPUBLISHED_PROTOCOL, get_model


def _fmt_measurement(m) -> str:
    if getattr(m, "metres", None) is None:
        return f"raw={m.raw} (no distance-scaling statement in this model's manual)"
    extra = ""
    if getattr(m, "out_of_range", False):
        extra = "  [OUT OF RANGE marker]"
    return f"{m.metres:.3f} m  (raw={m.raw}){extra}"


def cmd_models(args) -> int:
    rows = []
    for name in sorted(MODELS):
        s = MODELS[name]
        rows.append({
            "model": name,
            "family": s.family,
            "default_baud": s.default_baud,
            "frame_len": s.frame_len,
            "unit": s.unit,
            "min_range_m": s.min_range_m,
            "max_range_m": s.max_range_m,
        })
    if args.json:
        print(json.dumps({"published": rows, "unpublished": UNPUBLISHED_PROTOCOL},
                         indent=2))
        return 0
    print(f"{'MODEL':<12} {'FAM':<4} {'BAUD':>7} {'FRAME':>6} {'UNIT':<5} RANGE")
    for r in rows:
        baud = r["default_baud"] if r["default_baud"] is not None else "-"
        unit = r["unit"] or "-"
        rng = (f"{r['min_range_m']}-{r['max_range_m']} m"
               if r["max_range_m"] is not None else "-")
        print(f"{r['model']:<12} {r['family']:<4} {str(baud):>7} "
              f"{r['frame_len']:>6} {unit:<5} {rng}")
    print()
    for name, why in sorted(UNPUBLISHED_PROTOCOL.items()):
        print(f"{name:<12} (no published protocol) {why}")
    return 0


def cmd_info(args) -> int:
    s = get_model(args.model)
    print(f"model            {s.model}")
    print(f"protocol family  {s.family}")
    print(f"default baud     {s.default_baud if s.default_baud is not None else 'NONE - must be given explicitly'}")
    print(f"frame length     {s.frame_len} bytes")
    print(f"distance bytes   {s.distance_bytes}")
    print(f"unit             {s.unit or 'undocumented'}")
    print(f"out of range     {s.out_of_range_raw if s.out_of_range_raw is not None else 'undocumented'}")
    print(f"range            {s.min_range_m}-{s.max_range_m} m")
    print(f"capabilities     {', '.join(sorted(s.capabilities))}")
    if s.notes:
        print("\nnotes:")
        for n in s.notes:
            print(f"  - {n}")
    if s.sources:
        print("\nmanual sources:")
        for k, v in s.sources.items():
            print(f"  {k}: {v}")
    return 0


def _open(args):
    from .device import ErdiLRF

    if not args.port:
        raise SystemExit("--port is required for this command")
    return ErdiLRF(args.port, model=args.model, baud=args.baud, timeout=args.timeout)


def cmd_measure(args) -> int:
    with _open(args) as lrf:
        print(_fmt_measurement(lrf.measure()))
    return 0


def cmd_stream(args) -> int:
    with _open(args) as lrf:
        it = lrf.stream(acknowledge_protocol_hold=args.acknowledge_protocol_hold)
        n = 0
        for m in it:
            print(_fmt_measurement(m))
            n += 1
            if args.count and n >= args.count:
                break
        it.close()
    return 0


def cmd_info_device(args) -> int:
    with _open(args) as lrf:
        try:
            print(f"serial number    {lrf.read_serial_number()}")
        except ErdiLrfError as exc:
            print(f"serial number    unavailable: {exc}")
        try:
            print(f"software version {lrf.read_software_version()}")
        except ErdiLrfError as exc:
            print(f"software version unavailable: {exc}")
        try:
            print(f"output frequency {lrf.read_frequency():.1f} Hz")
        except ErdiLrfError as exc:
            print(f"output frequency unavailable: {exc}")
    return 0


def cmd_set_baud(args) -> int:
    with _open(args) as lrf:
        lrf.set_baud(args.bps)
    print(f"requested {args.bps} bps "
          "(family A applies the change only after the module reboots)")
    return 0


def _add_connection_args(parser: argparse.ArgumentParser, subcommand: bool) -> None:
    """Connection options, accepted both before and after the subcommand.

    On the subparsers the defaults are suppressed so that a value given before
    the subcommand is not silently overwritten by ``None``.
    """
    kw = {"default": argparse.SUPPRESS} if subcommand else {}
    parser.add_argument("--port", help="serial port, e.g. COM3 or /dev/ttyUSB0", **kw)
    parser.add_argument("--model", help="model name, e.g. LRF3000A1", **kw)
    parser.add_argument("--baud", type=int,
                        help="override the model's documented default baud rate",
                        **({"default": argparse.SUPPRESS} if subcommand else {"default": None}))
    parser.add_argument("--timeout", type=float, help="serial timeout, seconds",
                        **({"default": argparse.SUPPRESS} if subcommand else {"default": 1.0}))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="erdi-lrf",
        description="Driver CLI for ERDI 905 nm laser rangefinder modules. "
                    "Hardware: https://erdilrf.com/models/",
    )
    p.add_argument("--version", action="version", version=f"erdi-lrf {__version__}")
    _add_connection_args(p, subcommand=False)

    conn = argparse.ArgumentParser(add_help=False)
    _add_connection_args(conn, subcommand=True)

    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("models", help="list every model and its wire facts")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_models)

    sp = sub.add_parser("info", parents=[conn], help="show one model's documented protocol facts")
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("measure", parents=[conn], help="take a single measurement")
    sp.set_defaults(func=cmd_measure)

    sp = sub.add_parser("stream", parents=[conn], help="print measurements continuously")
    sp.add_argument("--count", type=int, default=0, help="stop after N readings")
    sp.add_argument("--acknowledge-protocol-hold", action="store_true",
                    help="proceed with continuous ranging on models whose manual "
                         "leaves the reply function byte unresolved")
    sp.set_defaults(func=cmd_stream)

    sp = sub.add_parser("info-device", parents=[conn], help="read serial number / version / rate")
    sp.set_defaults(func=cmd_info_device)

    sp = sub.add_parser("set-baud", parents=[conn], help="set the module's UART baud rate")
    sp.add_argument("bps", type=int)
    sp.set_defaults(func=cmd_set_baud)

    return p


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("info", "measure", "stream", "info-device", "set-baud") \
            and not args.model:
        print("--model is required for this command", file=sys.stderr)
        return 2
    try:
        return args.func(args)
    except ErdiLrfError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
