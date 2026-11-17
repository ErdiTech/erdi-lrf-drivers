"""SPD1200S2G: 8-byte distance protocol transcribed from the factory-pack manual (kb protocols/_source/SPD1200S2G.txt).

The 12-byte angle packets are deliberately not driven (the manual says to confirm their scale first).
"""

import pytest

from erdi_lrf import protocol_a as pa
from erdi_lrf.device import ErdiLRF
from erdi_lrf.errors import UndocumentedError
from erdi_lrf.models import A_BAUD_TYPES_SPD1200S2G, get_model
from test_device import factory


def test_model_row_follows_the_manual():
    spec = get_model("spd1200s2g")
    assert (spec.family, spec.default_baud, spec.frame_len, spec.distance_bytes) == ("A", 115200, 8, 2)
    assert (spec.unit, spec.raw_scale, spec.min_range_m, spec.max_range_m) == ("m", 10.0, 0.1, 1200.0)
    assert spec.baud_types == A_BAUD_TYPES_SPD1200S2G
    assert A_BAUD_TYPES_SPD1200S2G[0x05] == 56000 and A_BAUD_TYPES_SPD1200S2G[0x07] == 128000
    assert 57600 not in A_BAUD_TYPES_SPD1200S2G.values()   # differs from the LR table and from SPD1200D03's


def test_request_frames():
    assert pa.single_shot().hex() == "55aa88ffffffff84"
    assert pa.continuous().hex() == "55aa89ffffffff85"
    assert pa.stop().hex() == "55aa8effffffff8a"


def test_reply_scaled_by_ten_into_metres():
    # 55 AA 88 STA FF DATA_H DATA_L SUM[1:7]; 0x1102 = 4354 -> 435.4 m.  Sum 0x29A, lower eight bits 0x9A.
    frame = bytes.fromhex("55aa8801ff11029a")
    m = pa.parse_measurement(frame, get_model("SPD1200S2G"), expected_function=pa.FN_SINGLE)
    assert m.ok and m.raw == 4354 and m.metres == pytest.approx(435.4)


def test_measure_over_a_fake_port():
    reply = bytes.fromhex("55aa8801ff11029a")
    f = factory({pa.single_shot(): reply})
    with ErdiLRF("COM_TEST", model="SPD1200S2G", serial_factory=f) as lrf:
        assert lrf.measure().metres == pytest.approx(435.4)
    assert f.fake.baud == 115200


def test_baud_request_puts_type_in_d4_with_its_own_table():
    # "55 AA 01 FF FF FF Type SUM[3:7]": Type 06 = 115200 bps; SUM = 01+FF+FF+FF+06 = 0x304 -> 04
    f = factory()
    with ErdiLRF("COM_TEST", model="SPD1200S2G", serial_factory=f) as lrf:
        lrf.set_baud(115200)
        lrf.set_baud(56000)           # Type 05 = 56000 here; SUM = 01+3xFF+05 = 0x303 -> 03
    assert bytes(f.fake.written) == bytes.fromhex("55aa01ffffff0604" "55aa01ffffff0503")
    f2 = factory()
    with ErdiLRF("COM_TEST", model="SPD1200S2G", serial_factory=f2) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.set_baud(57600)


def test_angle_packets_and_unlisted_rows_are_not_driven():
    f = factory()
    with ErdiLRF("COM_TEST", model="SPD1200S2G", serial_factory=f) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.measure_angle()
        with pytest.raises(UndocumentedError):
            lrf.set_ld_always_on(True)
