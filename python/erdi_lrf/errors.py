"""Exception types for the ERDI laser rangefinder drivers."""

from __future__ import annotations


class ErdiLrfError(Exception):
    """Base class for every error raised by this package."""


class UnknownModelError(ErdiLrfError, KeyError):
    """The requested model is not in the published protocol set."""


class ChecksumError(ErdiLrfError, ValueError):
    """A frame failed its manual-documented checksum."""


class FrameError(ErdiLrfError, ValueError):
    """A frame is malformed: wrong length, wrong header, wrong function byte."""


class NoReplyError(ErdiLrfError, TimeoutError):
    """The module did not answer inside the serial timeout."""


class MeasurementFailed(ErdiLrfError):
    """The module answered, but its status byte reports a failed measurement."""

    def __init__(self, status: int, message: str = "") -> None:
        self.status = status
        super().__init__(message or f"module reported STA=0x{status:02X} (not 1 = success)")


class UndocumentedError(ErdiLrfError, NotImplementedError):
    """The requested operation is not documented in this model's manual.

    Raised instead of guessing.  The message names the model and the field.
    """


class ProtocolHoldError(ErdiLrfError):
    """The manual itself flags this operation as unresolved.

    The manual transcription for some models records a request function byte and
    a reply function byte that disagree, and explicitly withholds authorisation
    for a response parser.  Rather than silently pick one, this driver refuses
    and quotes the manual.  Pass ``acknowledge_protocol_hold=True`` to proceed on
    your own engineering judgement.
    """
