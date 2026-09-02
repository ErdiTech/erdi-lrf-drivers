"""Family B codec tests.

Every hex string below is a golden vector printed in an ERDI manual.  The
family-B manuals are unusually generous: they print the ``Check_Sum`` C function
*and* a full send/return pair for each command, so almost every assertion here
is a direct manual quotation rather than a hand computation.
"""

import pytest

from erdi_lrf import protocol_b as pb
from erdi_lrf.errors import ChecksumError, FrameError, UndocumentedError
from erdi_lrf.models import B_BAUD_RATES, get_model


def h(s: str) -> bytes:
    return bytes.fromhex(s.replace(" ", ""))


# --------------------------------------------------------------------------
# Checksum: "Begin with the second byte and end with the last second byte,
# find the inverse of the sum."
# --------------------------------------------------------------------------

MANUAL_FRAMES = [
    ("5C 02 11 EC", "LRF100H/LRF22VB/LRF50VB data frame, 4354 cm resp. 4354 mm"),
    ("5A 0D 02 0D 0D D6", "LRF50H: Reading serial no. request"),
    ("5A 0D 04 0D 0D 0D 0D BA", "LRF22VB: Reading serial no. request (4-byte form)"),
    ("5A 8D 04 10 01 00 00 5D", "LRF22VB: Reading serial no. reply, serial 272"),
    ("5A 8D 02 10 01 00 00 5F", "LRF50VB: Reading serial no. reply, serial 272"),
    ("5A 16 02 16 16 BB", "LRF22VB/LRF50VB: Reading software version request"),
    ("5A 96 02 03 02 62", "LRF22VB/LRF50VB: version reply, V2.3"),
    ("5A 06 02 80 04 73", "LRF22VB/LRF50VB: Baud rate setting request, 115200"),
    ("5A 86 02 80 04 F3", "LRF22VB/LRF50VB: Baud rate setting reply"),
    ("5A 0B 02 E7 03 08", "LRF22VB/LRF50VB: Set Frequency request, divisor 999"),
    ("5A 8B 02 E7 03 88", "LRF22VB/LRF50VB: Set Frequency reply"),
    ("5A 1B 02 1B 1B AC", "LRF22VB/LRF50VB: Read Frequency request"),
    ("5A 9B 02 31 00 31", "LRF22VB/LRF50VB: Read Frequency reply, divisor 49"),
    ("5A 1F 02 1F 1F A0", "LRF22VB/LRF50VB: Switch to IIC request"),
    ("5A 9F 02 1F 1F 20", "LRF22VB/LRF50VB: Switch to IIC reply"),
    ("5A 0A 02 02 00 F1", "LRF22VB/LRF50VB/LRF50H: Start Ranging request"),
    ("5A 8A 02 02 00 71", "LRF22VB/LRF50VB/LRF50H: Start Ranging reply"),
    ("5A 0A 02 00 00 F3", "LRF22VB/LRF50VB/LRF50H: Stop Ranging request"),
    ("5A 8A 02 00 00 73", "LRF22VB/LRF50VB/LRF50H: Stop Ranging reply"),
]


@pytest.mark.parametrize("frame,source", MANUAL_FRAMES)
def test_every_manual_frame_satisfies_the_manual_checksum(frame, source):
    assert pb.verify(h(frame)), source


def test_check_sum_is_the_inverted_sum():
    """5C 02 11 EC: ~(0x02 + 0x11) = ~0x13 = 0xEC."""
    assert pb.check_sum(b"\x02\x11") == 0xEC
    assert pb.check_sum(b"\x0d\x02\x0d\x0d") == 0xD6


# --------------------------------------------------------------------------
# Command builders reproduce the manual byte for byte
# --------------------------------------------------------------------------

GOLDEN_COMMANDS = [
    (pb.read_serial_number(), "5A 0D 02 0D 0D D6", "LRF50H command 1"),
    (pb.read_serial_number_4(), "5A 0D 04 0D 0D 0D 0D BA", "LRF22VB command 1"),
    (pb.read_software_version(), "5A 16 02 16 16 BB", "LRF22VB command 2"),
    (pb.set_baud(115200), "5A 06 02 80 04 73", "LRF22VB command 3"),
    (pb.set_frequency_divisor(999), "5A 0B 02 E7 03 08", "LRF22VB command 4"),
    (pb.read_frequency(), "5A 1B 02 1B 1B AC", "LRF22VB command 5"),
    (pb.switch_to_iic(), "5A 1F 02 1F 1F A0", "LRF22VB command 6"),
    (pb.stop_ranging(), "5A 0A 02 00 00 F3", "LRF22VB command 7"),
    (pb.start_ranging(), "5A 0A 02 02 00 F1", "LRF22VB command 8"),
]


@pytest.mark.parametrize("built,manual,source", GOLDEN_COMMANDS)
def test_command_builders_match_the_manual(built, manual, source):
    assert built == h(manual), source


# --------------------------------------------------------------------------
# Units are per-model, never per-family
# --------------------------------------------------------------------------

def test_h_series_reports_centimetres():
    """'the measuring distance is 4354cm' -- LRF100H."""
    spec = get_model("LRF100H")
    m = pb.parse_data_frame(h("5C 02 11 EC"), spec)
    assert m.raw == 4354
    assert m.metres == pytest.approx(43.54)


def test_vb_series_reports_millimetres_same_bytes_different_answer():
    """'the measuring distance is 4354mm' -- LRF22VB.  Same frame, 10x apart."""
    spec = get_model("LRF22VB")
    m = pb.parse_data_frame(h("5C 02 11 EC"), spec)
    assert m.raw == 4354
    assert m.metres == pytest.approx(4.354)


def test_the_two_series_really_do_differ_by_ten():
    frame = h("5C 02 11 EC")
    cm = pb.parse_data_frame(frame, get_model("LRF100H")).metres
    mm = pb.parse_data_frame(frame, get_model("LRF22VB")).metres
    assert cm == pytest.approx(mm * 10)


def test_distance_is_little_endian():
    """'02 11 : Distance value 2 bytes means the measuring distance is 4354'."""
    assert int.from_bytes(b"\x02\x11", "little") == 4354


def test_out_of_range_marker_h_series():
    """'When out of range, it would output 65535cm' -- LRF100H."""
    spec = get_model("LRF100H")
    frame = pb.build_data_frame(65535, spec)
    m = pb.parse_data_frame(frame, spec)
    assert m.raw == 65535
    assert m.out_of_range


def test_out_of_range_marker_lrf22vb_is_20000_not_65535():
    """'Range:0- 20000, When out of range, its output is 20000' -- LRF22VB."""
    spec = get_model("LRF22VB")
    m = pb.parse_data_frame(pb.build_data_frame(20000, spec), spec)
    assert m.out_of_range
    assert pb.parse_data_frame(pb.build_data_frame(19999, spec), spec).out_of_range is False


def test_out_of_range_marker_lrf50vb_is_50000():
    """'When out of range, output would be 50000' -- LRF50VB."""
    spec = get_model("LRF50VB")
    assert spec.out_of_range_raw == 50000
    assert pb.parse_data_frame(pb.build_data_frame(50000, spec), spec).out_of_range


# --------------------------------------------------------------------------
# LRF1500H is the odd one out: 5-byte frame, 3-byte distance
# --------------------------------------------------------------------------

def test_lrf1500h_uses_a_five_byte_frame_with_three_distance_bytes():
    """'02 11 03: Distance value 3 bytes means the measuring distance is 200962cm'."""
    spec = get_model("LRF1500H")
    assert spec.frame_len == 5 and spec.distance_bytes == 3
    assert int.from_bytes(b"\x02\x11\x03", "little") == 200962
    frame = pb.build_data_frame(200962, spec)
    assert frame[:4] == h("5C 02 11 03")
    m = pb.parse_data_frame(frame, spec)
    assert m.raw == 200962
    assert m.metres == pytest.approx(2009.62)


def test_lrf1500h_printed_example_check_byte_contradicts_its_own_formula():
    """MANUAL DISCREPANCY, asserted here so it cannot be quietly "fixed".

    The manual prints the example frame ``5C 02 11 03 EC`` and, on the same
    page, the ``Check_Sum`` function.  Applying that function gives
    ``~(0x02+0x11+0x03) = 0xE9``, not ``0xEC``.  ``0xEC`` is exactly the correct
    check byte for the *four*-byte frame ``5C 02 11 EC`` used by the other
    family-B models, so the printed example looks copied from them.

    This driver implements the printed function; the printed example frame is
    therefore rejected, deliberately.
    """
    assert pb.check_sum(b"\x02\x11\x03") == 0xE9
    assert pb.check_sum(b"\x02\x11") == 0xEC
    assert not pb.verify(h("5C 02 11 03 EC"))
    assert pb.verify(h("5C 02 11 03 E9"))


def test_lrf1500h_frame_length_is_enforced_per_model():
    spec = get_model("LRF1500H")
    with pytest.raises(FrameError):
        pb.parse_data_frame(h("5C 02 11 EC"), spec)   # 4-byte frame, wrong model


# --------------------------------------------------------------------------
# Reply parsing
# --------------------------------------------------------------------------

def test_parse_serial_number_reply():
    """'10 01 00 00 means the serial no. is 272: little-endian' -- LRF22VB."""
    reply = pb.parse_command_reply(h("5A 8D 04 10 01 00 00 5D"), pb.CMD_READ_SERIAL)
    assert int.from_bytes(reply.data, "little") == 272


def test_parse_version_reply():
    """'03 02 means the software version no. is V2.3'."""
    reply = pb.parse_command_reply(h("5A 96 02 03 02 62"), pb.CMD_READ_SOFTWARE)
    assert f"{reply.data[1]}.{reply.data[0]}" == "2.3"


def test_parse_baud_reply():
    """'80 04 as a decimal is 1152 ... the baud rate is set to 115200=1152*100'."""
    reply = pb.parse_command_reply(h("5A 86 02 80 04 F3"), pb.CMD_SET_BAUD)
    assert pb.decode_baud(reply.data) == 115200


def test_parse_reply_rejects_bad_checksum():
    with pytest.raises(ChecksumError):
        pb.parse_command_reply(h("5A 86 02 80 04 F2"))


def test_parse_reply_rejects_wrong_command():
    with pytest.raises(FrameError):
        pb.parse_command_reply(h("5A 86 02 80 04 F3"), pb.CMD_READ_SERIAL)


def test_parse_data_frame_rejects_bad_checksum():
    with pytest.raises(ChecksumError):
        pb.parse_data_frame(h("5C 02 11 ED"), get_model("LRF100H"))


# --------------------------------------------------------------------------
# Frequency: the divisor base is model specific
# --------------------------------------------------------------------------

def test_vb_frequency_base_is_ten_kilohertz():
    """'E7 03 ... represents the frequency divisor: 999.  f=10000/(999+1)=10Hz'."""
    spec = get_model("LRF22VB")
    assert spec.frequency_base_hz == 10_000
    assert pb.divisor_to_hz(999, spec.frequency_base_hz) == pytest.approx(10.0)
    assert pb.divisor_to_hz(49, spec.frequency_base_hz) == pytest.approx(200.0)


def test_h_frequency_base_is_one_megahertz():
    """'serial frequency division factor is 999 (E7 03) ... f=1000000/(999+1)=1000Hz'."""
    spec = get_model("LRF100H")
    assert spec.frequency_base_hz == 1_000_000
    assert pb.divisor_to_hz(999, spec.frequency_base_hz) == pytest.approx(1000.0)


def test_frequency_round_trip():
    for base in (10_000, 1_000_000):
        for hz in (1, 10, 20, 50, 100, 200):
            d = pb.hz_to_divisor(hz, base)
            assert pb.divisor_to_hz(d, base) == pytest.approx(hz)


# --------------------------------------------------------------------------
# Round trip and resynchronisation
# --------------------------------------------------------------------------

@pytest.mark.parametrize("model", ["LRF50H", "LRF100H", "LRF200H", "LRF300H",
                                   "LRF600H", "LRF1500H", "LRF22VB", "LRF50VB"])
def test_data_frame_round_trip(model):
    spec = get_model(model)
    top = 2 ** (8 * spec.distance_bytes) - 1
    for raw in (0, 1, 4354, min(20000, top), top):
        frame = pb.build_data_frame(raw, spec)
        assert len(frame) == spec.frame_len
        assert pb.parse_data_frame(frame, spec).raw == raw


def test_iter_data_frames_resyncs_after_a_mid_frame_start():
    spec = get_model("LRF100H")
    good = pb.build_data_frame(4354, spec)
    stream = good[2:] + good + good
    found = [f for _, f in pb.iter_data_frames(stream, spec)]
    assert found == [good, good]


def test_set_baud_refuses_undocumented_rates():
    """'Any other baud rate is not available'."""
    with pytest.raises(UndocumentedError):
        pb.set_baud(57600)
    for bps in B_BAUD_RATES:
        assert pb.verify(pb.set_baud(bps))


def test_command_builder_rejects_a_reply_marked_command_byte():
    with pytest.raises(FrameError):
        pb.build_command(0x8D, b"\x00\x00")
