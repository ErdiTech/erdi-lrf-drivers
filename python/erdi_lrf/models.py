"""Per-model wire facts for the ERDI 905 nm rangefinder catalogue.

Every value in this file is transcribed from the model's own manual.  Nothing is
extrapolated from a sibling model, because the catalogue is not internally
uniform:

* the VB series reports **millimetres** while the H series reports
  **centimetres** -- reading the wrong one is a 10x error;
* ``LRF1500H`` uses a 5-byte data frame with a 3-byte distance while every other
  family-B model uses a 4-byte frame with a 2-byte distance;
* ``SPD1200D03`` uses a different baud-setting frame *and* a different TYPE
  table from the rest of family A;
* ``LRF50H``/``LRF100H``/``LRF200H`` derive output frequency from a 1 MHz base
  while ``LRF22VB``/``LRF50VB`` derive it from a 10 kHz base.

Where the manual does not state something, the field is ``None`` and the gap is
recorded in ``notes`` -- it is never filled in by inference.

Source archive: ERDI engineering notes, one file per model
(verbatim transcription of the manual's communication-protocol section).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from .errors import UnknownModelError

# --------------------------------------------------------------------------
# Capability tokens
# --------------------------------------------------------------------------
CAP_SINGLE = "single"                      # family A 0x88
CAP_CONTINUOUS = "continuous"              # family A 0x89
CAP_STOP = "stop"                          # family A 0x8E
CAP_ANGLE = "angle"                        # family A 0x8A
CAP_SELF_TEST = "self_test"                # family A 0x80 (unsolicited reply)
CAP_SET_BAUD = "set_baud"
CAP_LD_ALWAYS_ON = "ld_always_on"          # family A 0x86
CAP_EXTERNAL_CIRCUIT = "external_circuit"  # family A 0x70 / 0x71
CAP_READ_SERIAL = "read_serial"            # family B 0x0D
CAP_READ_VERSION = "read_version"          # family B 0x16
CAP_SET_FREQUENCY = "set_frequency"        # family B 0x0B
CAP_READ_FREQUENCY = "read_frequency"      # family B 0x1B
CAP_SWITCH_TO_IIC = "switch_to_iic"        # family B 0x1F
CAP_START_STOP = "start_stop"              # family B 0x0A

# --------------------------------------------------------------------------
# Baud-rate tables
# --------------------------------------------------------------------------

#: Family A ``TYPE`` byte -> bits per second.
#: Source (LR1000E2.txt source row 29, identical rows in the sibling manuals):
#: "TYPE = 01: Set baud rate to 9600 bps ... TYPE = 09: Set baud rate to 230400 bps"
A_BAUD_TYPES: Mapping[int, int] = {
    0x01: 9600,
    0x02: 14400,
    0x03: 19200,
    0x04: 38400,
    0x05: 56000,
    0x06: 57600,
    0x07: 115200,
    0x08: 128000,
    0x09: 230400,
}

#: SPD1200D03 publishes a *different* seven-entry table.  Do not merge it with
#: :data:`A_BAUD_TYPES`.
#: Source (SPD1200D03.txt, "PDF p8 / baud types"):
#: "TYPE 01 = 9600; 02 = 14400; 03 = 19200; 04 = 38400; 05 = 57600; 06 = 115200;
#: 07 = 230400 bps. Restart required."
A_BAUD_TYPES_SPD1200D03: Mapping[int, int] = {
    0x01: 9600,
    0x02: 14400,
    0x03: 19200,
    0x04: 38400,
    0x05: 57600,
    0x06: 115200,
    0x07: 230400,
}

#: Family B baud rates, encoded as ``bps // 100`` little-endian uint16.
#: Source (LRF22VB.txt UART command 3): "60 00 (9600) / C0 00 (19200) /
#: 80 01 (38400) / 80 04 (115200) / 00 09 (230400) / 00 0A (256000) /
#: 00 12 (460800).  Any other baud rate is not available"
B_BAUD_RATES = (9600, 19200, 38400, 115200, 230400, 256000, 460800)


@dataclass(frozen=True)
class ModelSpec:
    """One model's wire-level facts, each traceable to its manual."""

    model: str
    family: str                       # "A" (55 AA command/response) or "B" (5C stream)
    default_baud: Optional[int]
    frame_len: int                    # bytes in one data/reply frame
    distance_bytes: int               # family B: bytes of distance in a data frame
    unit: Optional[str]               # unit of ``raw / raw_scale``: "m", "cm", "mm"
    raw_scale: Optional[float]        # raw counts per one ``unit``
    out_of_range_raw: Optional[int]
    min_range_m: Optional[float]
    max_range_m: Optional[float]
    capabilities: frozenset
    baud_types: Optional[Mapping[int, int]] = None   # family A TYPE table
    frequency_base_hz: Optional[int] = None          # family B: f = base / (divisor + 1)
    continuous_hold: Optional[str] = None            # manual sentence withholding authorisation
    sources: Mapping[str, str] = field(default_factory=dict)
    notes: tuple = ()

    @property
    def metres_per_count(self) -> Optional[float]:
        """Metres represented by one raw count, or ``None`` if undocumented."""
        if self.raw_scale is None or self.unit is None:
            return None
        per_unit = {"m": 1.0, "cm": 0.01, "mm": 0.001}[self.unit]
        return per_unit / self.raw_scale

    def to_metres(self, raw: int) -> Optional[float]:
        """Convert a raw distance count to metres, or ``None`` if undocumented."""
        mpc = self.metres_per_count
        return None if mpc is None else raw * mpc

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


# --------------------------------------------------------------------------
# Shared manual quotations (identical wording across the eight LR-series manuals)
# --------------------------------------------------------------------------
_LR_SRC = {
    "baud": "Source default baud rate: 115200. Data bits: 8. Frame length: 8 bytes.",
    "tx_checksum": (
        "Source transmit checksum formula: SUM(Function Code + DATA1 + DATA2 + "
        "DATA3 + DATA4), lower 8 bits."
    ),
    "rx_checksum": (
        "Source reply checksum formula: SUM(Frame Header (H) + Frame Header (L) + "
        "Function Code + DATA1 + DATA2 + DATA3 + DATA4), lower 8 bits."
    ),
    "scale": (
        "Data is returned in hexadecimal format, and all measurement results are "
        "output as the actual value x 10"
    ),
    "status": "STA = other value: Measurement failed; STA = 1: Measurement successful",
    "unit": (
        "The unit is metres, taken from the model's own ranging-range row in the "
        "source technical table; the protocol section states only the x10 scaling."
    ),
}

_LR_CAPS = frozenset({
    CAP_SINGLE, CAP_CONTINUOUS, CAP_STOP, CAP_ANGLE,
    CAP_SELF_TEST, CAP_SET_BAUD, CAP_LD_ALWAYS_ON,
})

_ANGLE_NOTE = (
    "Angle measurement (0x8A) is 'Effective only for modules equipped with an "
    "angle sensor' -- source row 21."
)


def _lr(model: str, min_m: float, max_m: float) -> ModelSpec:
    return ModelSpec(
        model=model, family="A", default_baud=115200, frame_len=8,
        distance_bytes=2, unit="m", raw_scale=10.0, out_of_range_raw=None,
        min_range_m=min_m, max_range_m=max_m,
        capabilities=_LR_CAPS, baud_types=A_BAUD_TYPES,
        sources=dict(_LR_SRC), notes=(_ANGLE_NOTE,),
    )


_A1_SRC = {
    "baud": "Baud rate: 115200 (default).  Data Bits: 8 Bits.  Length of a frame: 8 bytes",
    "tx_checksum": "Send | 55 | AA | SUM(function word +DATA1+...+DATA4)",
    "rx_checksum": "Reply | 55 | AA | SUM(frame header H + frame header L + ...+DATA4)",
    "checksum_warning": (
        "The verification content for sending and receiving may differ, so please "
        "pay attention to discrimination."
    ),
    "scale": "all data results are output by multiplying the real data by 10",
    "status": "STA = 0 measurement failure; STA = 1: The measurement was successful",
    "unit": (
        "The unit is metres, taken from the model's own ranging-range row in the "
        "source technical table; the protocol section states only the x10 scaling."
    ),
}

_A1_HOLD = (
    "PROTOCOL HOLD  Continuous ranging remains an engineering-confirmation item "
    "because the source request and reply function bytes differ.  (Request "
    "55 AA 89 FF FF FF FF 85; recorded reply 55 AA 88 STA FF DIS_H DIS_L SUM.)"
)

_A1_CAPS = frozenset({
    CAP_SINGLE, CAP_CONTINUOUS, CAP_STOP, CAP_ANGLE,
    CAP_SELF_TEST, CAP_SET_BAUD, CAP_EXTERNAL_CIRCUIT,
})

_N_SRC = {
    "baud": (
        "Source communication method: serial.  Default baud rate: 115200 bps.  "
        "Data bits: 8.  Frame length: 8 bytes."
    ),
    "rx_checksum": (
        "The source uses different checksum scopes for request and reply frames.  "
        "Preserve the exact source row order and verify checksum handling in the "
        "integration implementation."
    ),
    "scale": (
        "Data is returned in hexadecimal, The returned hexadecimal value is the "
        "actual result multiplied by 10"
    ),
    "status": "STA = other, measurement failed; STA = 1:measurement succeeded",
    "unit": (
        "The unit is metres, taken from the model's own ranging-range row in the "
        "source technical table; the protocol section states only the x10 scaling."
    ),
}

_N_NOTES = (
    "The SPD1200N transcription states that request and reply checksum scopes "
    "differ but does not print the transmit formula.  This driver uses the "
    "family-A transmit formula, which reproduces every example frame the manual "
    "does print (55 AA 88 FF FF FF FF 84 / 89 ... 85 / 8E ... 8A / 8A ... 86).  "
    "See docs/protocol-A-55AA.md, 'Known gaps'.",
    _ANGLE_NOTE,
)

_N_CAPS = frozenset({
    CAP_SINGLE, CAP_CONTINUOUS, CAP_STOP, CAP_ANGLE,
    CAP_SELF_TEST, CAP_SET_BAUD, CAP_LD_ALWAYS_ON,
})


def _n(model: str, min_m: Optional[float], max_m: Optional[float]) -> ModelSpec:
    return ModelSpec(
        model=model, family="A", default_baud=115200, frame_len=8,
        distance_bytes=2, unit="m", raw_scale=10.0, out_of_range_raw=None,
        min_range_m=min_m, max_range_m=max_m,
        capabilities=_N_CAPS, baud_types=A_BAUD_TYPES,
        sources=dict(_N_SRC), notes=_N_NOTES,
    )


# --------------------------------------------------------------------------
# Family B shared quotations
# --------------------------------------------------------------------------
_B_CHECKSUM_SRC = (
    "Begin with the second byte and end with the last second byte, find the "
    "inverse of the sum.  uint8_t Check_Sum(uint8_t *_pbuff, uint16_t _cmdLen) "
    "{ uint8_t cmd_sum=0; ... cmd_sum = (~cmd_sum); return cmd_sum; }"
)
_B_BAUD_SRC = "UART Baud Rate 460800 (adjustable) Data Bit 8 Stop Bit 1 Parity Bit None"
_B_H_UNIT_SRC = (
    "02 11: Distance value 2 bytes means the measuring distance is 4354cm, "
    "little-endian, range 0-65535cm.  When out of range, it would output 65535cm."
)

_B_H_CAPS = frozenset({
    CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD,
    CAP_SET_FREQUENCY, CAP_READ_FREQUENCY,
})

_NO_FREQ_NOTE = (
    "The manual gives no output-frequency divisor formula for this model, so "
    "set/read frequency is not exposed."
)


def _h(model: str, max_m: float, freq_base: Optional[int],
       caps: frozenset = _B_H_CAPS, notes: tuple = ()) -> ModelSpec:
    return ModelSpec(
        model=model, family="B", default_baud=460800, frame_len=4,
        distance_bytes=2, unit="cm", raw_scale=1.0, out_of_range_raw=65535,
        min_range_m=0.05, max_range_m=max_m,
        capabilities=caps, frequency_base_hz=freq_base,
        sources={
            "baud": _B_BAUD_SRC,
            "checksum": _B_CHECKSUM_SRC,
            "frame": "Frame Header | Distance 2 Bytes | Check Byte -> 5C 02 11 EC",
            "unit": _B_H_UNIT_SRC,
        },
        notes=notes,
    )


MODELS: dict = {
    # ---- Family A, LR series --------------------------------------------
    "LR1000E2": _lr("LR1000E2", 4.0, 1000.0),
    "LR1000E4": _lr("LR1000E4", 4.0, 1000.0),
    "LR1200E2": _lr("LR1200E2", 4.0, 1200.0),
    "LR1200E4": _lr("LR1200E4", 4.0, 1200.0),
    "LR1500E2": _lr("LR1500E2", 4.0, 1500.0),
    "LR1500E4": _lr("LR1500E4", 4.0, 1500.0),
    "LR2000E2": _lr("LR2000E2", 4.0, 2000.0),
    "LR2000E4": _lr("LR2000E4", 4.0, 2000.0),

    # ---- Family A, A1 series (protocol hold on continuous) ---------------
    "LRF1200A1": ModelSpec(
        model="LRF1200A1", family="A", default_baud=115200, frame_len=8,
        distance_bytes=2, unit="m", raw_scale=10.0, out_of_range_raw=None,
        min_range_m=5.0, max_range_m=1200.0,
        capabilities=_A1_CAPS, baud_types=A_BAUD_TYPES,
        continuous_hold=_A1_HOLD, sources=dict(_A1_SRC),
        notes=(_ANGLE_NOTE, _A1_HOLD),
    ),
    "LRF3000A1": ModelSpec(
        model="LRF3000A1", family="A", default_baud=115200, frame_len=8,
        distance_bytes=2, unit="m", raw_scale=10.0, out_of_range_raw=None,
        min_range_m=1.0, max_range_m=3000.0,
        capabilities=_A1_CAPS, baud_types=A_BAUD_TYPES,
        continuous_hold=_A1_HOLD, sources=dict(_A1_SRC),
        notes=(_ANGLE_NOTE, _A1_HOLD),
    ),

    # ---- Family A, SPD1200N series ---------------------------------------
    "SPD1200N0": _n("SPD1200N0", 0.2, 1200.0),
    "SPD1200N2": _n("SPD1200N2", 0.2, 1200.0),
    "SPD1200N4": _n("SPD1200N4", 0.2, 1200.0),

    # ---- Family A, SPD1200D03 (baud conflict, no documented scale) --------
    "SPD1200D03": ModelSpec(
        model="SPD1200D03", family="A",
        default_baud=None,          # the manual contradicts itself -- see notes
        frame_len=8, distance_bytes=2,
        unit=None, raw_scale=None,  # no scaling statement of any kind in the manual
        out_of_range_raw=None,
        min_range_m=0.2, max_range_m=1200.0,
        capabilities=frozenset({CAP_SINGLE, CAP_CONTINUOUS, CAP_STOP,
                                CAP_SELF_TEST, CAP_SET_BAUD}),
        baud_types=A_BAUD_TYPES_SPD1200D03,
        sources={
            "tx_checksum": (
                "55 AA Function D1 D2 D3 D4 SUM; transmit checksum uses the lower "
                "eight bits of Function + DATA1 + DATA2 + DATA3 + DATA4."
            ),
            "rx_checksum": (
                "55 AA Function D1 D2 D3 D4 SUM; reply checksum uses the lower "
                "eight bits of Header H + Header L + Function + DATA1 + DATA2 + "
                "DATA3 + DATA4."
            ),
        },
        notes=(
            "BAUD CONFLICT (the manual contradicts itself; reported verbatim, not "
            "resolved): 'The PDF protocol section states 115200 bps as default, "
            "while the technical table states 15200 bps (factory) / 9600 bps.' and "
            "'Do not select a host baud rate until the delivered unit "
            "configuration is confirmed.'  This driver therefore refuses to pick "
            "one: you must pass baud= explicitly.",
            "The manual prints no distance-scaling statement for this model, so "
            "raw counts are returned and .metres is None.  Confirm the scaling "
            "with ERDI before converting.",
            "The manual prints no STA semantics for this model, so the status "
            "byte is returned unchecked.",
            "No angle-measurement row appears in this model's transcription.",
        ),
    ),

    # ---- Family B, H series (centimetres) ---------------------------------
    "LRF50H": _h("LRF50H", 50.0, 1_000_000, caps=_B_H_CAPS | {CAP_START_STOP}),
    "LRF100H": _h("LRF100H", 100.0, 1_000_000),
    "LRF200H": _h("LRF200H", 200.0, 1_000_000),
    "LRF300H": _h("LRF300H", 300.0, None,
                  caps=frozenset({CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD}),
                  notes=(_NO_FREQ_NOTE,)),
    "LRF600H": _h("LRF600H", 600.0, None,
                  caps=frozenset({CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD}),
                  notes=(_NO_FREQ_NOTE,)),

    # LRF1500H: 5-byte frame, 3-byte distance -- the only one in the catalogue.
    "LRF1500H": ModelSpec(
        model="LRF1500H", family="B", default_baud=460800, frame_len=5,
        distance_bytes=3, unit="cm", raw_scale=1.0, out_of_range_raw=16777215,
        min_range_m=0.05, max_range_m=1500.0,
        capabilities=frozenset({CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD}),
        frequency_base_hz=None,
        sources={
            "baud": (
                "the default frequency is 1000/50Hz, and the default baud rate is "
                "460800 (adjustable).  Data bit 8, stop bit 1, no parity bit."
            ),
            "checksum": _B_CHECKSUM_SRC,
            "frame": "Frame Header | Distance 3 Bytes | Check Byte -> 5C 02 11 03 EC",
            "unit": (
                "02 11 03: Distance value 3 bytes means the measuring distance is "
                "200962cm, little-endian, range 0-16777215cm.  When out of range, "
                "it would output 16777215cm."
            ),
        },
        notes=(
            "Our engineering notes record baud='60' for this model.  That "
            "is an extraction artefact from the baud-rate code table "
            "('60 00 | 96 | 9600'); the manual prose states 460800 (adjustable), "
            "which is what this driver uses.",
            "MANUAL DISCREPANCY (reported, not resolved): the printed example frame "
            "'5C 02 11 03 EC' does not satisfy the manual's own Check_Sum "
            "function -- ~(0x02+0x11+0x03) = 0xE9, not 0xEC.  0xEC is the correct "
            "check byte for the 4-byte frame '5C 02 11 EC' used by the other "
            "family-B models, so the example looks copied.  This driver implements "
            "the printed Check_Sum function.",
            "MANUAL DISCREPANCY (reported, not resolved): section 6 says 'When out "
            "of its measuring range, it would output 0xFFFF (16777215)'.  0xFFFF is "
            "65535, not 16777215.  This driver uses 16777215, which matches the "
            "3-byte field width stated in section 5.2.",
            _NO_FREQ_NOTE,
        ),
    ),

    # ---- Family B, VB series (millimetres) --------------------------------
    "LRF22VB": ModelSpec(
        model="LRF22VB", family="B", default_baud=460800, frame_len=4,
        distance_bytes=2, unit="mm", raw_scale=1.0, out_of_range_raw=20000,
        min_range_m=0.05, max_range_m=20.0,
        capabilities=frozenset({
            CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD,
            CAP_SET_FREQUENCY, CAP_READ_FREQUENCY, CAP_SWITCH_TO_IIC,
            CAP_START_STOP}),
        frequency_base_hz=10_000,
        sources={
            "baud": "UART Baud Rate 460800 (adjustable) Data Bit 8 Stop Bit 1 Parity Bit N/A",
            "checksum": (
                "EC: The checksum byte is calculated by summing all bytes from the "
                "second byte (02) to the second-last byte (11), then inverting the "
                "result."
            ),
            "unit": (
                "02 11 : Distance value 2 bytes means the measuring distance is "
                "4354mm, little-endian, Range:0- 20000, When out of range, its "
                "output is 20000."
            ),
            "iic_address": "The default address is 0x52 (7bit address mode).",
        },
        notes=("Supported output frequencies per the manual: 200/100/50/20/10/1 Hz.",),
    ),
    "LRF50VB": ModelSpec(
        model="LRF50VB", family="B", default_baud=460800, frame_len=4,
        distance_bytes=2, unit="mm", raw_scale=1.0, out_of_range_raw=50000,
        min_range_m=0.05, max_range_m=50.0,
        capabilities=frozenset({
            CAP_READ_SERIAL, CAP_READ_VERSION, CAP_SET_BAUD,
            CAP_SET_FREQUENCY, CAP_READ_FREQUENCY, CAP_SWITCH_TO_IIC,
            CAP_START_STOP}),
        frequency_base_hz=10_000,
        sources={
            "baud": (
                "UART Protocol Free Baud Rate 460800 (adjustable) Data Bit 8 "
                "Stop Bit 1 Parity Bit None"
            ),
            "checksum": (
                "EC: The checksum byte is calculated by summing all bytes from the "
                "second byte (02) to the second-last byte (11), then inverting the "
                "result."
            ),
            "unit": (
                "02 11: Distance value 2 bytes means the measuring distance is "
                "4354mm, little-endian, range 0-50000.  When out of range, output "
                "would be 50000."
            ),
            "iic_address": "The default address is 0x52 (7bit address mode).",
        },
        notes=(
            "Our engineering notes list out_of_range as unresolved for "
            "this model; the manual prose does state 'When out of range, output "
            "would be 50000', which is what this driver uses.",
            "MANUAL DISCREPANCY (reported, not resolved): the printed 'Reading "
            "serial no.' request '5A 0D 02 0D 0D 0D 0D BC' does not satisfy the "
            "manual's own Check_Sum function for either length byte "
            "(0x02 -> 0xBE, 0x04 -> 0xBA).  The printed reply "
            "'5A 8D 02 10 01 00 00 5F' does check out.  This driver builds the "
            "request with the Check_Sum function.",
            "Supported output frequencies per the manual: 100/50/20/10/1 Hz (the "
            "set-frequency row) and 200/100/50/20/10/1 Hz (the read-frequency "
            "row) -- the manual lists both.",
        ),
    ),
}

#: Models in the published catalogue whose communication protocol ERDI has not
#: released.  Listed so that ``erdi-lrf models`` is honest about the whole
#: catalogue rather than silently omitting them.
UNPUBLISHED_PROTOCOL = {
    "LRF10VB": "Upstream has not published a manual for this model (940 nm, 0.05-9 m).",
    "SPD1200S2G": "Upstream has not published a manual for this model (0.1-1200 m, with gyro).",
}


def get_model(name: str) -> ModelSpec:
    """Look up a model spec, case-insensitively."""
    key = name.strip().upper()
    if key in MODELS:
        return MODELS[key]
    if key in UNPUBLISHED_PROTOCOL:
        raise UnknownModelError(
            f"{key}: {UNPUBLISHED_PROTOCOL[key]} "
            "Ask ERDI (https://erdilrf.com/contact/) rather than assuming it "
            "matches a sibling model -- units are not uniform across this "
            "catalogue."
        )
    raise UnknownModelError(
        f"unknown model {name!r}. Published protocols: {', '.join(sorted(MODELS))}."
    )
