"""Family A codec tests.

Every hex string below is a **golden vector printed in an ERDI manual**, quoted
in the test's docstring with its source model.  Where the manual prints only a
compressed row and no full frame (reply frames carrying real distances), the
expected checksum is computed by hand from the manual's stated formula and the
arithmetic is spelled out in the docstring.
"""

import pytest

from erdi_lrf import protocol_a as pa
from erdi_lrf.errors import ChecksumError, FrameError
from erdi_lrf.models import A_BAUD_TYPES, A_BAUD_TYPES_SPD1200D03, get_model


def h(s: str) -> bytes:
    return bytes.fromhex(s.replace(" ", ""))


# --------------------------------------------------------------------------
# Golden request frames printed verbatim in the manuals
# --------------------------------------------------------------------------

GOLDEN_REQUESTS = [
    # (builder, manual hex, source row)
    (pa.single_shot(), "55 AA 88 FF FF FF FF 84",
     "LR1000E2 row 7: 'Single-Shot Ranging | Send | 55 AA 88 FF FF FF FF 84'"),
    (pa.continuous(), "55 AA 89 FF FF FF FF 85",
     "LR1000E2 row 11: 'Continuous Ranging | Send | 55 AA 89 FF FF FF FF 85'"),
    (pa.stop(), "55 AA 8E FF FF FF FF 8A",
     "LR1000E2 row 15: 'Stop Ranging | Send | 55 AA 8E FF FF FF FF 8A'"),
    (pa.angle(), "55 AA 8A FF FF FF FF 86",
     "LR1000E2 row 19: 'Angle Measurement | Send | 55 AA 8A FF FF FF FF 86'"),
    (pa.ld_always_on(True), "55 AA 86 FF FF FF 01 84",
     "LR1000E2 row 33: '55 AA 86 FF FF FF 01 84 Enable'"),
    (pa.ld_always_on(False), "55 AA 86 FF FF FF 00 83",
     "LR1000E2 row 33: '55 AA 86 FF FF FF 00 83 Disable'"),
    (pa.external_circuit(True), "55 AA 70 AB CD 00 00 E8",
     "LRF3000A1 T5/R6: 'External circuit enable | Send | 55 AA 70 AB CD 00 00 E8'"),
    (pa.external_circuit(False), "55 AA 71 AB CD 00 00 E9",
     "LRF3000A1 T5/R10: '55 AA 71 AB CD 00 00 E9'"),
]


@pytest.mark.parametrize("built,manual,source", GOLDEN_REQUESTS)
def test_request_frames_match_the_manual(built, manual, source):
    assert built == h(manual), source


def test_transmit_checksum_formula():
    """'SUM(Function Code + DATA1 + DATA2 + DATA3 + DATA4), lower 8 bits'.

    0x88 + 0xFF*4 = 0x484 -> lower 8 bits 0x84, which is the byte the manual
    prints for the single-shot request.
    """
    assert pa.tx_checksum(0x88, b"\xff\xff\xff\xff") == 0x84
    assert pa.tx_checksum(0x86, b"\xff\xff\xff\x01") == 0x84
    assert pa.tx_checksum(0x70, b"\xab\xcd\x00\x00") == 0xE8


def test_reply_checksum_covers_the_header_but_transmit_does_not():
    """The manual warns the two formulas differ; this pins the difference.

    Transmit scope is Function+D1..D4; reply scope adds the two header bytes,
    so the same trailing seven bytes give checksums exactly 0x55+0xAA = 0xFF
    apart (mod 256).
    """
    frame7 = h("55 AA 88 01 FF 00 2A")
    tx = pa.tx_checksum(frame7[2], frame7[3:7])
    rx = pa.rx_checksum(frame7)
    assert (rx - tx) & 0xFF == (0x55 + 0xAA) & 0xFF
    assert tx != rx


def test_reply_checksum_hand_computed():
    """Hand-computed from 'SUM(Frame Header (H) + Frame Header (L) + Function
    Code + DATA1 + DATA2 + DATA3 + DATA4), lower 8 bits'.

    Frame 55 AA 88 01 FF 00 2A -> 0x55+0xAA+0x88+0x01+0xFF+0x00+0x2A = 0x2B1,
    lower 8 bits 0xB1.
    """
    assert pa.rx_checksum(h("55 AA 88 01 FF 00 2A")) == 0xB1


# --------------------------------------------------------------------------
# Reply parsing
# --------------------------------------------------------------------------

def test_parse_single_shot_reply_scales_by_ten():
    """Reply layout '55 | AA | 88 | STA | FF | DIS_H | DIS_L | SUM[1:7]'.

    DIS_H=0x00, DIS_L=0x2A -> raw 42; 'all measurement results are output as the
    actual value x 10' -> 4.2 m.  Checksum computed by hand as in the test above.
    """
    spec = get_model("LR1000E2")
    frame = h("55 AA 88 01 FF 00 2A B1")
    m = pa.parse_measurement(frame, spec, expected_function=pa.FN_SINGLE)
    assert m.status == 1 and m.ok
    assert m.raw == 42
    assert m.metres == pytest.approx(4.2)


def test_parse_reply_rejects_a_bad_checksum():
    spec = get_model("LR1000E2")
    with pytest.raises(ChecksumError):
        pa.parse_measurement(h("55 AA 88 01 FF 00 2A B0"), spec)


def test_parse_reply_rejects_a_bad_header():
    spec = get_model("LR1000E2")
    with pytest.raises(FrameError):
        pa.parse_measurement(h("AA 55 88 01 FF 00 2A B1"), spec)


def test_parse_reply_rejects_the_wrong_function():
    spec = get_model("LR1000E2")
    with pytest.raises(FrameError):
        pa.parse_measurement(h("55 AA 88 01 FF 00 2A B1"), spec,
                             expected_function=pa.FN_ANGLE)


def test_failed_status_is_reported_not_silently_dropped():
    """'STA = other value: Measurement failed; STA = 1: Measurement successful'."""
    spec = get_model("LR1000E2")
    frame = bytearray(h("55 AA 88 00 FF 00 00 00"))
    frame[-1] = pa.rx_checksum(bytes(frame[:-1]))
    m = pa.parse_measurement(bytes(frame), spec)
    assert m.status == 0
    assert not m.ok


def test_spd1200d03_returns_raw_counts_because_no_scaling_is_documented():
    """SPD1200D03's manual prints no distance-scaling statement at all."""
    spec = get_model("SPD1200D03")
    assert spec.raw_scale is None
    frame = bytearray(h("55 AA 88 01 FF 00 2A 00"))
    frame[-1] = pa.rx_checksum(bytes(frame[:-1]))
    m = pa.parse_measurement(bytes(frame), spec)
    assert m.raw == 42
    assert m.metres is None


def test_self_test_exposes_both_documented_errcode_positions():
    """The LR row prints seven cells, SPD1200D03 prints eight; both are exposed.

    Frame 55 AA 80 00 00 00 18 -> 0x55+0xAA+0x80+0x00+0x00+0x00+0x18 = 0x197,
    lower 8 bits 0x97.
    """
    st = pa.parse_self_test(h("55 AA 80 00 00 00 18 97"))
    assert st.status == 0 and not st.ok
    assert st.error_code_d4 == 0x18            # SPD1200D03 eight-byte form
    assert st.error_code_d3 == 0x00            # LR-series seven-cell form
    assert pa.ERROR_CODES[0x18] == "No echo signal was received"


# --------------------------------------------------------------------------
# Round-trip and resynchronisation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("function", [0x88, 0x89, 0x8A, 0x8E, 0x80, 0x86, 0x70, 0x71])
@pytest.mark.parametrize("data", [b"\xff\xff\xff\xff", b"\x00\x00\x00\x00",
                                  b"\xab\xcd\x00\x00", b"\x12\x34\x56\x78"])
def test_build_command_round_trip(function, data):
    frame = pa.build_command(function, data)
    assert len(frame) == pa.FRAME_LEN
    assert frame[:2] == pa.HEADER
    assert frame[2] == function
    assert frame[3:7] == data
    assert frame[7] == pa.tx_checksum(function, data)


def test_find_frames_resyncs_after_garbage():
    good = h("55 AA 88 01 FF 00 2A B1")
    stream = b"\x00\x55\x11" + good + b"\x55\xaa\x00" + good
    found = pa.find_frames(stream)
    assert found == [good, good]


def test_find_frames_skips_frames_that_fail_the_checksum():
    bad = h("55 AA 88 01 FF 00 2A B0")
    assert pa.find_frames(bad) == []


def test_build_command_rejects_wrong_data_length():
    with pytest.raises(FrameError):
        pa.build_command(0x88, b"\xff\xff")


# --------------------------------------------------------------------------
# Baud tables -- the two are genuinely different, do not merge them
# --------------------------------------------------------------------------

def test_baud_type_tables_differ_between_spd1200d03_and_the_rest():
    assert A_BAUD_TYPES[0x05] == 56000        # LR series
    assert A_BAUD_TYPES_SPD1200D03[0x05] == 57600
    assert A_BAUD_TYPES[0x09] == 230400
    assert A_BAUD_TYPES_SPD1200D03[0x07] == 230400
    assert 0x08 not in A_BAUD_TYPES_SPD1200D03


def test_spd1200d03_baud_frame_puts_type_in_d4():
    """'PDF p8 / baud request -> 55 AA 01 FF FF FF TYPE SUM[3:7]'."""
    frame = pa.set_baud_spd1200d03(0x06)
    assert frame[2] == 0x01
    assert frame[6] == 0x06
    assert frame[7] == pa.tx_checksum(0x01, b"\xff\xff\xff\x06")


def test_standard_baud_frame_puts_type_in_the_function_position():
    """'Baud Rate | Send | 55 | AA | TYPE | FF | SUM[3:7]'."""
    frame = pa.set_baud(0x07)
    assert frame == h("55 AA 07 FF FF FF FF 03")
