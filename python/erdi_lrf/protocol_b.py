"""Family B codec: ``5C`` free-running data frames and ``5A`` command frames.

Data frame (4-byte models)::

    5C <dist_lo> <dist_hi> <check>

Data frame (LRF1500H only, 5 bytes)::

    5C <dist_lo> <dist_mid> <dist_hi> <check>

Distance is little-endian and its **unit differs by series**: the H series
reports centimetres, the VB series reports millimetres.  The unit comes from the
model spec, never from the family.

Command frame::

    5A <cmd> <len> <data...> <check>

The reply echoes the command byte with bit 7 set (``0x0D`` -> ``0x8D``).

Checksum, quoted from the manual, which also prints the C function::

    Begin with the second byte and end with the last second byte, find the
    inverse of the sum.

    uint8_t Check_Sum(uint8_t *_pbuff, uint16_t _cmdLen)
    {
        uint8_t cmd_sum=0;
        uint16_t i;
        for(i=0;i<_cmdLen;i++) { cmd_sum += _pbuff[i]; }
        cmd_sum = (~cmd_sum);
        return cmd_sum;
    }

This module is pure: no serial port, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from .errors import ChecksumError, FrameError, UndocumentedError

DATA_HEADER = 0x5C
CMD_HEADER = 0x5A
REPLY_BIT = 0x80

# Command bytes, from the "UART Commands" tables.
CMD_READ_SERIAL = 0x0D      # "Reading serial no.   5A 0D 02 0D 0D D6"
CMD_SET_BAUD = 0x06         # "Baud rate setting    5A 06 02 80 04 73"
CMD_SET_FREQUENCY = 0x0B    # "Set Frequency        5A 0B 02 E7 03 08"
CMD_READ_SOFTWARE = 0x16    # "Reading software version no.  5A 16 02 16 16 BB"
CMD_READ_FREQUENCY = 0x1B   # "Read Frequency       5A 1B 02 1B 1B AC"
CMD_SWITCH_TO_IIC = 0x1F    # "Switch to IIC        5A 1F 02 1F 1F A0"
CMD_RANGING = 0x0A          # "Stop 5A 0A 02 00 00 F3 / Start 5A 0A 02 02 00 F1"


def check_sum(payload: bytes) -> int:
    """The manual's ``Check_Sum``: bitwise inverse of the byte sum, 8-bit."""
    return (~sum(payload)) & 0xFF


def verify(frame: bytes) -> bool:
    """True if ``frame``'s last byte matches ``check_sum(frame[1:-1])``."""
    frame = bytes(frame)
    if len(frame) < 3:
        return False
    return frame[-1] == check_sum(frame[1:-1])


def build_command(cmd: int, data: bytes) -> bytes:
    """Build ``5A <cmd> <len> <data...> <check>``.

    The length byte counts the data bytes, matching every printed example:
    ``5A 0D 02 0D 0D D6`` (2 data bytes) and ``5A 0D 04 0D 0D 0D 0D BA``
    (4 data bytes).
    """
    if not 0 <= cmd <= 0x7F:
        raise FrameError(f"command byte out of range: 0x{cmd:02X} (bit 7 marks replies)")
    body = bytes([cmd, len(data)]) + bytes(data)
    return bytes([CMD_HEADER]) + body + bytes([check_sum(body)])


@dataclass(frozen=True)
class ReplyB:
    """A parsed ``5A`` command reply."""

    command: int          # with bit 7 already stripped
    data: bytes
    frame: bytes


def parse_command_reply(frame: bytes, expected_command: Optional[int] = None) -> ReplyB:
    frame = bytes(frame)
    if len(frame) < 4:
        raise FrameError(f"command reply too short: {frame.hex(' ')}")
    if frame[0] != CMD_HEADER:
        raise FrameError(f"bad reply header 0x{frame[0]:02X}, expected 0x5A")
    if not verify(frame):
        raise ChecksumError(
            f"reply checksum 0x{frame[-1]:02X} != computed "
            f"0x{check_sum(frame[1:-1]):02X} for {frame.hex(' ')}"
        )
    cmd = frame[1] & ~REPLY_BIT
    length = frame[2]
    data = frame[3:3 + length]
    if len(data) != length:
        raise FrameError(
            f"reply declares {length} data bytes but carries {len(data)}: {frame.hex(' ')}"
        )
    if expected_command is not None and cmd != expected_command:
        raise FrameError(
            f"reply command 0x{cmd:02X} != expected 0x{expected_command:02X}"
        )
    return ReplyB(command=cmd, data=bytes(data), frame=frame)


# --- data frames ----------------------------------------------------------

@dataclass(frozen=True)
class MeasurementB:
    """One free-running distance frame."""

    raw: int
    metres: Optional[float]
    out_of_range: bool
    frame: bytes


def parse_data_frame(frame: bytes, spec) -> MeasurementB:
    """Parse one ``5C`` data frame using ``spec`` for length, unit and range."""
    frame = bytes(frame)
    if len(frame) != spec.frame_len:
        raise FrameError(
            f"{spec.model} data frame must be {spec.frame_len} bytes, got {len(frame)}"
        )
    if frame[0] != DATA_HEADER:
        raise FrameError(f"bad data header 0x{frame[0]:02X}, expected 0x5C")
    if not verify(frame):
        raise ChecksumError(
            f"data checksum 0x{frame[-1]:02X} != computed "
            f"0x{check_sum(frame[1:-1]):02X} for {frame.hex(' ')}"
        )
    raw = int.from_bytes(frame[1:1 + spec.distance_bytes], "little")
    oor = spec.out_of_range_raw is not None and raw >= spec.out_of_range_raw
    return MeasurementB(
        raw=raw,
        metres=spec.to_metres(raw),
        out_of_range=oor,
        frame=frame,
    )


def build_data_frame(raw: int, spec) -> bytes:
    """Encode a data frame -- used for round-trip tests and for simulators."""
    body = int(raw).to_bytes(spec.distance_bytes, "little")
    return bytes([DATA_HEADER]) + body + bytes([check_sum(body)])


def iter_data_frames(buffer: bytes, spec) -> Iterator[Tuple[int, bytes]]:
    """Yield ``(offset, frame)`` for every checksum-valid data frame in ``buffer``.

    A frame whose checksum fails is skipped and the scan resyncs one byte later,
    so a mid-frame start does not desynchronise the reader permanently.
    """
    n = spec.frame_len
    i = 0
    while i <= len(buffer) - n:
        if buffer[i] == DATA_HEADER and verify(buffer[i:i + n]):
            yield i, bytes(buffer[i:i + n])
            i += n
        else:
            i += 1


# --- parameter commands ---------------------------------------------------

def read_serial_number() -> bytes:
    """``5A 0D 02 0D 0D D6``.

    Note the VB manuals print a 4-data-byte variant (``5A 0D 04 0D 0D 0D 0D BA``)
    returning a 4-byte serial number; use :func:`read_serial_number_4` there.
    """
    return build_command(CMD_READ_SERIAL, b"\x0d\x0d")


def read_serial_number_4() -> bytes:
    """``5A 0D 04 0D 0D 0D 0D BA`` -- the LRF22VB four-byte form."""
    return build_command(CMD_READ_SERIAL, b"\x0d\x0d\x0d\x0d")


def read_software_version() -> bytes:
    """``5A 16 02 16 16 BB``."""
    return build_command(CMD_READ_SOFTWARE, b"\x16\x16")


def set_baud(bps: int) -> bytes:
    """``5A 06 02 80 04 73`` sets 115200.

    The two data bytes are ``bps // 100`` little-endian: "80 04 as a decimal is
    1152: little-endian, it means the baud rate is set to 115200=1152*100".
    """
    from .models import B_BAUD_RATES

    if bps not in B_BAUD_RATES:
        raise UndocumentedError(
            f"{bps} bps is not in the manual's list {B_BAUD_RATES}: "
            "'Any other baud rate is not available'"
        )
    return build_command(CMD_SET_BAUD, (bps // 100).to_bytes(2, "little"))


def decode_baud(data: bytes) -> int:
    """Decode a two-byte baud field back to bits per second."""
    return int.from_bytes(data[:2], "little") * 100


def set_frequency_divisor(divisor: int) -> bytes:
    """``5A 0B 02 E7 03 08`` sets divisor 999.

    The output frequency is ``base / (divisor + 1)``; the base is **model
    specific** (see :attr:`ModelSpec.frequency_base_hz`) and is 10 kHz on the VB
    series but 1 MHz on LRF50H/LRF100H/LRF200H.
    """
    if not 0 <= divisor <= 0xFFFF:
        raise FrameError(f"divisor out of 16-bit range: {divisor}")
    return build_command(CMD_SET_FREQUENCY, divisor.to_bytes(2, "little"))


def read_frequency() -> bytes:
    """``5A 1B 02 1B 1B AC``."""
    return build_command(CMD_READ_FREQUENCY, b"\x1b\x1b")


def switch_to_iic() -> bytes:
    """``5A 1F 02 1F 1F A0`` -- VB series only.

    The manual documents no UART command to switch back; the return path is the
    I2C register pair 0x04/0x05 ("Write 0xA5 to register 0x04 and 0x5A to
    register 0x05 simultaneously").
    """
    return build_command(CMD_SWITCH_TO_IIC, b"\x1f\x1f")


def start_ranging() -> bytes:
    """``5A 0A 02 02 00 F1``."""
    return build_command(CMD_RANGING, b"\x02\x00")


def stop_ranging() -> bytes:
    """``5A 0A 02 00 00 F3``."""
    return build_command(CMD_RANGING, b"\x00\x00")


def divisor_to_hz(divisor: int, base_hz: int) -> float:
    """``f = base / (divisor + 1)`` -- see :func:`set_frequency_divisor`."""
    return base_hz / (divisor + 1)


def hz_to_divisor(hz: float, base_hz: int) -> int:
    """Inverse of :func:`divisor_to_hz`, rounded to the nearest integer."""
    if hz <= 0:
        raise FrameError("frequency must be positive")
    return max(0, round(base_hz / hz) - 1)
