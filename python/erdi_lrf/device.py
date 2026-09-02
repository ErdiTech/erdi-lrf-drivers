"""Serial transport for ERDI 905 nm rangefinder modules.

The codec modules (:mod:`erdi_lrf.protocol_a`, :mod:`erdi_lrf.protocol_b`) are
pure and hardware-free; this module is the only place that touches a serial
port.  ``pyserial`` is imported lazily so the codecs and the model table can be
used, and tested, without it.
"""

from __future__ import annotations

import time
from typing import Iterator, Optional

from . import protocol_a as pa
from . import protocol_b as pb
from .errors import (
    ErdiLrfError,
    MeasurementFailed,
    NoReplyError,
    ProtocolHoldError,
    UndocumentedError,
)
from .models import (
    CAP_ANGLE,
    CAP_CONTINUOUS,
    CAP_EXTERNAL_CIRCUIT,
    CAP_LD_ALWAYS_ON,
    CAP_READ_FREQUENCY,
    CAP_READ_SERIAL,
    CAP_READ_VERSION,
    CAP_SET_BAUD,
    CAP_SET_FREQUENCY,
    CAP_START_STOP,
    CAP_SWITCH_TO_IIC,
    ModelSpec,
    get_model,
)


def _require_serial():
    try:
        import serial  # noqa: F401
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ErdiLrfError(
            "pyserial is required to talk to a module: pip install pyserial"
        ) from exc
    return serial


class ErdiLRF:
    """A connected ERDI rangefinder module.

    ::

        from erdi_lrf import ErdiLRF

        with ErdiLRF("COM3", model="LRF3000A1") as lrf:
            print(lrf.measure().metres)

    ``baud`` defaults to the model's documented default.  ``SPD1200D03`` has no
    usable default -- its own manual contradicts itself -- so passing ``baud``
    explicitly is mandatory for that model.
    """

    def __init__(self, port: str, model: str, baud: Optional[int] = None,
                 timeout: float = 1.0, serial_factory=None) -> None:
        self.spec: ModelSpec = get_model(model)
        if baud is None:
            if self.spec.default_baud is None:
                raise UndocumentedError(
                    f"{self.spec.model}: no default baud rate can be chosen for you.\n"
                    + "\n".join(self.spec.notes)
                    + "\nPass baud=... explicitly once the delivered unit's "
                    "configuration is confirmed."
                )
            baud = self.spec.default_baud
        self.baud = baud
        self.timeout = timeout
        if serial_factory is None:
            serial = _require_serial()
            self.ser = serial.Serial(port, baud, timeout=timeout)
        else:
            self.ser = serial_factory(port, baud, timeout)
        self._streaming = False

    # -- context manager ---------------------------------------------------
    def __enter__(self) -> "ErdiLRF":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            if self._streaming:
                self.stop()
        except Exception:  # noqa: BLE001 - closing must not mask the original error
            pass
        finally:
            self.ser.close()

    # -- helpers -----------------------------------------------------------
    def _require(self, capability: str, what: str) -> None:
        if not self.spec.supports(capability):
            raise UndocumentedError(
                f"{self.spec.model}: {what} is not documented in this model's "
                f"manual.  Documented operations: "
                f"{', '.join(sorted(self.spec.capabilities))}."
            )

    def _read_exact(self, n: int) -> bytes:
        data = self.ser.read(n)
        if len(data) != n:
            raise NoReplyError(
                f"{self.spec.model}: expected {n} bytes, got {len(data)} "
                f"within {self.timeout}s at {self.baud} bps"
            )
        return data

    def _read_frame_a(self, expected_function: Optional[int] = None,
                      deadline: Optional[float] = None) -> bytes:
        """Resynchronise on 55 AA and return one complete 8-byte frame."""
        buf = bytearray()
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise NoReplyError(f"{self.spec.model}: no valid 55 AA frame before deadline")
            byte = self.ser.read(1)
            if not byte:
                raise NoReplyError(
                    f"{self.spec.model}: serial read timed out at {self.baud} bps"
                )
            buf += byte
            if len(buf) > 2 * pa.FRAME_LEN:
                del buf[:-2 * pa.FRAME_LEN]
            frames = pa.find_frames(bytes(buf))
            for frame in frames:
                if expected_function is None or frame[2] == expected_function:
                    return frame

    def _read_frame_b(self, deadline: Optional[float] = None) -> bytes:
        n = self.spec.frame_len
        buf = bytearray()
        while True:
            if deadline is not None and time.monotonic() > deadline:
                raise NoReplyError(f"{self.spec.model}: no valid 5C frame before deadline")
            byte = self.ser.read(1)
            if not byte:
                raise NoReplyError(
                    f"{self.spec.model}: serial read timed out at {self.baud} bps"
                )
            buf += byte
            if len(buf) > 2 * n:
                del buf[:-2 * n]
            for _, frame in pb.iter_data_frames(bytes(buf), self.spec):
                return frame

    def _command_b(self, request: bytes, expected_command: int) -> pb.ReplyB:
        self.ser.write(request)
        buf = bytearray()
        deadline = time.monotonic() + max(self.timeout, 0.2)
        while time.monotonic() < deadline:
            byte = self.ser.read(1)
            if not byte:
                continue
            buf += byte
            # Command replies are short; scan for a 5A frame that verifies.
            for start in range(len(buf)):
                if buf[start] != pb.CMD_HEADER:
                    continue
                for end in range(start + 4, len(buf) + 1):
                    chunk = bytes(buf[start:end])
                    if pb.verify(chunk):
                        return pb.parse_command_reply(chunk, expected_command)
        raise NoReplyError(
            f"{self.spec.model}: no reply to command 0x{expected_command:02X}"
        )

    # -- ranging -----------------------------------------------------------
    def measure(self, raise_on_failure: bool = True):
        """Take a single measurement.

        Family A sends ``55 AA 88 ...`` and waits for the reply.  Family B
        modules free-run, so this starts ranging where the model documents a
        start command and returns the first valid data frame.
        """
        if self.spec.family == "A":
            self.ser.reset_input_buffer()
            self.ser.write(pa.single_shot())
            frame = self._read_frame_a(
                pa.FN_SINGLE, deadline=time.monotonic() + max(self.timeout, 0.2)
            )
            m = pa.parse_measurement(frame, self.spec, expected_function=pa.FN_SINGLE)
            if raise_on_failure and self.spec.sources.get("status") and not m.ok:
                raise MeasurementFailed(m.status)
            return m
        # family B
        started = False
        if self.spec.supports(CAP_START_STOP) and not self._streaming:
            self.ser.write(pb.start_ranging())
            started = True
        try:
            return pb.parse_data_frame(
                self._read_frame_b(deadline=time.monotonic() + max(self.timeout, 0.5)),
                self.spec,
            )
        finally:
            if started:
                self.ser.write(pb.stop_ranging())

    def stream(self, acknowledge_protocol_hold: bool = False) -> Iterator:
        """Yield measurements continuously until the generator is closed."""
        if self.spec.family == "A":
            self._require(CAP_CONTINUOUS, "continuous ranging")
            if self.spec.continuous_hold and not acknowledge_protocol_hold:
                raise ProtocolHoldError(
                    f"{self.spec.model}: {self.spec.continuous_hold}\n"
                    "Pass acknowledge_protocol_hold=True to proceed on your own "
                    "engineering judgement, or confirm the reply function byte "
                    "with ERDI first (https://erdilrf.com/contact/)."
                )
            self.ser.reset_input_buffer()
            self.ser.write(pa.continuous())
            self._streaming = True
            try:
                while True:
                    frame = self._read_frame_a()
                    if frame[2] not in (pa.FN_SINGLE, pa.FN_CONTINUOUS):
                        continue
                    yield pa.parse_measurement(frame, self.spec)
            finally:
                self.stop()
        else:
            if self.spec.supports(CAP_START_STOP):
                self.ser.write(pb.start_ranging())
            self._streaming = True
            try:
                while True:
                    yield pb.parse_data_frame(self._read_frame_b(), self.spec)
            finally:
                self.stop()

    def stop(self) -> None:
        """Stop continuous ranging, where the model documents a stop command."""
        try:
            if self.spec.family == "A":
                self.ser.write(pa.stop())
            elif self.spec.supports(CAP_START_STOP):
                self.ser.write(pb.stop_ranging())
        finally:
            self._streaming = False

    def measure_angle(self):
        """Angle measurement (family A ``0x8A``), for units with an angle sensor."""
        self._require(CAP_ANGLE, "angle measurement")
        self.ser.reset_input_buffer()
        self.ser.write(pa.angle())
        frame = self._read_frame_a(
            pa.FN_ANGLE, deadline=time.monotonic() + max(self.timeout, 0.2)
        )
        return pa.parse_measurement(frame, self.spec, expected_function=pa.FN_ANGLE)

    # -- parameters --------------------------------------------------------
    def set_baud(self, bps: int) -> None:
        """Set the module's UART baud rate.

        Family A: takes effect only after a reboot ("The baud rate change does
        not take effect immediately").  Family B: the module answers at the old
        rate, then switches.
        """
        self._require(CAP_SET_BAUD, "baud-rate setting")
        if self.spec.family == "A":
            table = self.spec.baud_types or {}
            codes = [c for c, v in table.items() if v == bps]
            if not codes:
                raise UndocumentedError(
                    f"{self.spec.model}: {bps} bps is not in this model's TYPE "
                    f"table {dict(sorted(table.items()))}"
                )
            frame = (pa.set_baud_spd1200d03(codes[0])
                     if self.spec.model == "SPD1200D03"
                     else pa.set_baud(codes[0]))
            self.ser.write(frame)
            return
        self._command_b(pb.set_baud(bps), pb.CMD_SET_BAUD)

    def read_serial_number(self) -> int:
        """Family B: read the module serial number (little-endian)."""
        self._require(CAP_READ_SERIAL, "serial-number read")
        four_byte = self.spec.model in ("LRF22VB", "LRF50VB")
        request = pb.read_serial_number_4() if four_byte else pb.read_serial_number()
        reply = self._command_b(request, pb.CMD_READ_SERIAL)
        return int.from_bytes(reply.data, "little")

    def read_software_version(self) -> str:
        """Family B: read the software version, e.g. ``"2.3"``.

        Source: "03 02 means the software version no. is V2.3: little-endian, 02
        represents 2, 03 represents 3, Add a point (.) in the middle."
        """
        self._require(CAP_READ_VERSION, "software-version read")
        reply = self._command_b(pb.read_software_version(), pb.CMD_READ_SOFTWARE)
        if len(reply.data) < 2:
            raise NoReplyError(f"{self.spec.model}: short version reply {reply.frame.hex(' ')}")
        return f"{reply.data[1]}.{reply.data[0]}"

    def set_frequency(self, hz: float) -> float:
        """Family B: set the output frequency; returns the achievable frequency.

        ``f = base / (divisor + 1)`` where the base is model specific.
        """
        self._require(CAP_SET_FREQUENCY, "output-frequency setting")
        base = self.spec.frequency_base_hz
        if base is None:
            raise UndocumentedError(
                f"{self.spec.model}: the manual prints no frequency divisor formula."
            )
        divisor = pb.hz_to_divisor(hz, base)
        self._command_b(pb.set_frequency_divisor(divisor), pb.CMD_SET_FREQUENCY)
        return pb.divisor_to_hz(divisor, base)

    def read_frequency(self) -> float:
        """Family B: read the current output frequency in Hz."""
        self._require(CAP_READ_FREQUENCY, "output-frequency read")
        base = self.spec.frequency_base_hz
        if base is None:
            raise UndocumentedError(
                f"{self.spec.model}: the manual prints no frequency divisor formula."
            )
        reply = self._command_b(pb.read_frequency(), pb.CMD_READ_FREQUENCY)
        divisor = int.from_bytes(reply.data[:2], "little")
        return pb.divisor_to_hz(divisor, base)

    def switch_to_iic(self) -> None:
        """Family B (VB series): switch the module from UART to I2C.

        There is no documented UART command to switch back -- see the codec
        docstring.
        """
        self._require(CAP_SWITCH_TO_IIC, "switching to I2C")
        self._command_b(pb.switch_to_iic(), pb.CMD_SWITCH_TO_IIC)

    def set_ld_always_on(self, enable: bool) -> None:
        """Family A ``0x86``.  Manual caution: do not leave this on for long."""
        self._require(CAP_LD_ALWAYS_ON, "LD constant-ON mode")
        self.ser.write(pa.ld_always_on(enable))

    def set_external_circuit(self, enable: bool) -> None:
        """Family A ``0x70`` / ``0x71`` (LRF1200A1, LRF3000A1).

        Disabling puts the module into the manual's secondary low-power mode.
        """
        self._require(CAP_EXTERNAL_CIRCUIT, "external-circuit enable/disable")
        self.ser.write(pa.external_circuit(enable))
