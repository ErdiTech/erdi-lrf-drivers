"""Family A codec: 8-byte ``55 AA`` command/response frames.

Frame layout (source: "Frame Header (H) | Frame Header (L) | Function Code | D1 |
D2 | D3 | D4 | Checksum")::

    55 AA <function> <D1> <D2> <D3> <D4> <checksum>

The two checksums are **not** the same, and the manual says so explicitly:

* transmit: ``SUM(Function Code + DATA1 + DATA2 + DATA3 + DATA4)``, lower 8 bits
* reply:    ``SUM(Frame Header (H) + Frame Header (L) + Function Code + DATA1 +
  DATA2 + DATA3 + DATA4)``, lower 8 bits

"The source warns that the transmit and response calculations differ."
Getting this wrong is the single most likely integration bug in family A, which
is why the two functions below are deliberately separate and separately tested.

This module is pure: no serial port, no I/O.  Everything here can be unit-tested
without hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from .errors import ChecksumError, FrameError

HEADER = b"\x55\xaa"
FRAME_LEN = 8

# Function codes, from the source command tables.
FN_SINGLE = 0x88          # "Single-Shot Ranging | Send | 55 AA 88 FF FF FF FF 84"
FN_CONTINUOUS = 0x89      # "Continuous Ranging | Send | 55 AA 89 FF FF FF FF 85"
FN_ANGLE = 0x8A           # "Angle Measurement | Send | 55 AA 8A FF FF FF FF 86"
FN_STOP = 0x8E            # "Stop Ranging | Send | 55 AA 8E FF FF FF FF 8A"
FN_SELF_TEST = 0x80       # "Self-Test Information | Reply | 55 AA 80 STA 00 ErrCode SUM"
FN_LD_ALWAYS_ON = 0x86    # "55 AA 86 FF FF FF 01 84 Enable / 55 AA 86 FF FF FF 00 83 Disable"
FN_EXT_CIRCUIT_ON = 0x70  # "External circuit enable | Send | 55 AA 70 AB CD 00 00 E8"
FN_EXT_CIRCUIT_OFF = 0x71  # "55 AA 71 AB CD 00 00 E9"

#: Every request in the manual pads the four data bytes with FF unless the row
#: prints a specific value.
IDLE_DATA = b"\xff\xff\xff\xff"

#: ErrCode table, source rows T5/R15..T5/R18 of LRF1200A1 / LRF3000A1.
#: Reported exactly as printed, including the fact that 0x00 appears twice.
ERROR_CODES = {
    0x00: "No echo signal was received (also listed inside the 0x00-0x07 hardware-error range)",
    0x16: "Out of range: below the minimum range",
    0x18: "No echo signal was received",
}
HARDWARE_ERROR_RANGE = range(0x00, 0x08)  # "0x00~0x07 | Hardware error"

STATUS_SUCCESS = 0x01  # "STA = 1: Measurement successful"


def tx_checksum(function: int, data: bytes) -> int:
    """Transmit checksum: ``SUM(Function Code + DATA1..DATA4)``, lower 8 bits."""
    if len(data) != 4:
        raise FrameError(f"data must be 4 bytes, got {len(data)}")
    return (function + sum(data)) & 0xFF


def rx_checksum(frame_without_checksum: bytes) -> int:
    """Reply checksum: ``SUM(header H + header L + function + DATA1..DATA4)``."""
    if len(frame_without_checksum) != FRAME_LEN - 1:
        raise FrameError(
            f"expected {FRAME_LEN - 1} bytes before the checksum, "
            f"got {len(frame_without_checksum)}"
        )
    return sum(frame_without_checksum) & 0xFF


def build_command(function: int, data: bytes = IDLE_DATA) -> bytes:
    """Build one 8-byte request frame."""
    if not 0 <= function <= 0xFF:
        raise FrameError(f"function code out of range: {function}")
    if len(data) != 4:
        raise FrameError(f"data must be 4 bytes, got {len(data)}")
    return HEADER + bytes([function]) + bytes(data) + bytes([tx_checksum(function, data)])


def _check_reply_envelope(frame: bytes, expected_function: Optional[int],
                          verify_checksum: bool) -> bytes:
    """Validate length, header, checksum and function byte of a reply frame."""
    frame = bytes(frame)
    if len(frame) != FRAME_LEN:
        raise FrameError(f"family A reply must be {FRAME_LEN} bytes, got {len(frame)}")
    if frame[:2] != HEADER:
        raise FrameError(f"bad frame header {frame[:2].hex(' ')}, expected 55 aa")
    if verify_checksum:
        want = rx_checksum(frame[:-1])
        if frame[-1] != want:
            raise ChecksumError(
                f"reply checksum 0x{frame[-1]:02X} != computed 0x{want:02X} for "
                f"frame {frame.hex(' ')}.  Note the reply formula covers the two "
                "header bytes as well; the transmit formula does not."
            )
    if expected_function is not None and frame[2] != expected_function:
        raise FrameError(
            f"reply function 0x{frame[2]:02X} != expected 0x{expected_function:02X} "
            f"in frame {frame.hex(' ')}"
        )
    return frame


# --- request builders -----------------------------------------------------

def single_shot() -> bytes:
    """``55 AA 88 FF FF FF FF 84`` -- single-shot ranging."""
    return build_command(FN_SINGLE)


def continuous() -> bytes:
    """``55 AA 89 FF FF FF FF 85`` -- start continuous ranging."""
    return build_command(FN_CONTINUOUS)


def stop() -> bytes:
    """``55 AA 8E FF FF FF FF 8A`` -- stop continuous ranging."""
    return build_command(FN_STOP)


def angle() -> bytes:
    """``55 AA 8A FF FF FF FF 86`` -- angle measurement.

    "Effective only for modules equipped with an angle sensor."
    """
    return build_command(FN_ANGLE)


def ld_always_on(enable: bool) -> bytes:
    """``55 AA 86 FF FF FF 01 84`` enable / ``... 00 83`` disable.

    Source caution: "Do not keep the constant-ON mode enabled for long periods."
    """
    return build_command(FN_LD_ALWAYS_ON, b"\xff\xff\xff" + bytes([0x01 if enable else 0x00]))


def external_circuit(enable: bool) -> bytes:
    """``55 AA 70 AB CD 00 00 E8`` enable / ``55 AA 71 AB CD 00 00 E9`` disable.

    LRF1200A1 / LRF3000A1 only.  Disabling puts the module into the manual's
    "secondary low-power mode".
    """
    fn = FN_EXT_CIRCUIT_ON if enable else FN_EXT_CIRCUIT_OFF
    return build_command(fn, b"\xab\xcd\x00\x00")


def set_baud(type_code: int) -> bytes:
    """Baud-rate request for every family-A model *except* SPD1200D03.

    Source row: "Baud Rate | Send | 55 | AA | TYPE | FF | SUM[3:7]".  That row is
    written in the manual's compressed form; the same compression is used for
    "Single-Shot Ranging | Send | 55 | AA | 88 | FF | SUM[3:7]", whose expanded
    form the manual prints on the very next row as ``55 AA 88 FF FF FF FF 84``.
    The expansion below follows that printed convention.

    "The baud rate change does not take effect immediately; it becomes effective
    only after a reboot."
    """
    return build_command(type_code, IDLE_DATA)


def set_baud_spd1200d03(type_code: int) -> bytes:
    """Baud-rate request for SPD1200D03 only.

    This model puts TYPE in D4 rather than in the function-code position:
    "PDF p8 / baud request -> ``55 AA 01 FF FF FF TYPE SUM[3:7]``".
    """
    return build_command(0x01, b"\xff\xff\xff" + bytes([type_code]))


# --- reply parsing --------------------------------------------------------

@dataclass(frozen=True)
class MeasurementA:
    """A family-A ranging reply."""

    status: int
    raw: int
    metres: Optional[float]
    function: int
    frame: bytes

    @property
    def ok(self) -> bool:
        return self.status == STATUS_SUCCESS


def parse_measurement(frame: bytes, spec, expected_function: Optional[int] = None,
                      verify_checksum: bool = True) -> MeasurementA:
    """Parse a ranging reply ``55 AA <fn> STA FF DIS_H DIS_L SUM``.

    ``spec`` is a :class:`erdi_lrf.models.ModelSpec`; it supplies the scaling.
    When the model's manual documents no scaling (SPD1200D03), ``metres`` is
    ``None`` and only ``raw`` is meaningful.
    """
    frame = _check_reply_envelope(frame, expected_function, verify_checksum)
    raw = (frame[5] << 8) | frame[6]
    return MeasurementA(
        status=frame[3], raw=raw, metres=spec.to_metres(raw),
        function=frame[2], frame=frame,
    )


@dataclass(frozen=True)
class SelfTestA:
    """A power-on self-test reply ``55 AA 80 STA 00 [00] ErrCode SUM``.

    The two source transcriptions disagree on where ErrCode sits:

    * LR-series row 24 prints seven cells: ``55 | AA | 80 | STA | 00 | ErrCode | SUM``
    * SPD1200D03 prints the full eight: ``55 AA 80 STA 00 00 ErrCode SUM``

    Rather than pick one, both candidate bytes are exposed.  ``data`` holds
    D1..D4 verbatim so you can decide with your delivered unit in hand.
    """

    status: int
    data: bytes
    frame: bytes

    @property
    def error_code_d3(self) -> int:
        """ErrCode if the LR-series seven-cell row is read literally (D3)."""
        return self.data[2]

    @property
    def error_code_d4(self) -> int:
        """ErrCode per the SPD1200D03 eight-byte form (D4)."""
        return self.data[3]

    @property
    def ok(self) -> bool:
        return self.status == STATUS_SUCCESS


def parse_self_test(frame: bytes, verify_checksum: bool = True) -> SelfTestA:
    frame = _check_reply_envelope(frame, FN_SELF_TEST, verify_checksum)
    return SelfTestA(status=frame[3], data=frame[3:7], frame=frame)


def find_frames(buffer: bytes) -> Sequence[bytes]:
    """Split a byte buffer into checksum-valid 8-byte ``55 AA`` frames.

    Frames that do not verify are skipped, and the scan resyncs one byte later,
    so a partially-read stream does not desynchronise the reader permanently.
    """
    frames = []
    i = 0
    end = len(buffer) - FRAME_LEN + 1
    while i < end:
        if buffer[i] == 0x55 and buffer[i + 1] == 0xAA:
            candidate = buffer[i:i + FRAME_LEN]
            if candidate[-1] == rx_checksum(candidate[:-1]):
                frames.append(bytes(candidate))
                i += FRAME_LEN
                continue
        i += 1
    return frames
