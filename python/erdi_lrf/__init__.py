"""Open-source drivers for ERDI 905 nm laser rangefinder modules.

Two published protocol families cover the whole catalogue:

* **Family A** -- 8-byte ``55 AA`` command/response frames, 115200 bps default.
* **Family B** -- free-running ``5C`` data frames plus ``5A`` command frames,
  460800 bps default.

Every constant is transcribed from the model's own manual.  Nothing is
extrapolated from a sibling model: the VB series reports millimetres while the H
series reports centimetres, and LRF1500H uses a 5-byte frame where everything
else uses 4.

Hardware: https://erdilrf.com/models/
"""

from .device import ErdiLRF
from .errors import (
    ChecksumError,
    ErdiLrfError,
    FrameError,
    MeasurementFailed,
    NoReplyError,
    ProtocolHoldError,
    UndocumentedError,
    UnknownModelError,
)
from .models import MODELS, UNPUBLISHED_PROTOCOL, ModelSpec, get_model

__version__ = "0.1.0"

__all__ = [
    "ErdiLRF",
    "MODELS",
    "UNPUBLISHED_PROTOCOL",
    "ModelSpec",
    "get_model",
    "ErdiLrfError",
    "ChecksumError",
    "FrameError",
    "MeasurementFailed",
    "NoReplyError",
    "ProtocolHoldError",
    "UndocumentedError",
    "UnknownModelError",
    "__version__",
]
