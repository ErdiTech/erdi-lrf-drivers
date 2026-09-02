"""Transport tests against a scripted fake serial port -- no hardware needed."""

import pytest

from erdi_lrf import protocol_a as pa
from erdi_lrf import protocol_b as pb
from erdi_lrf.device import ErdiLRF
from erdi_lrf.errors import ProtocolHoldError, UndocumentedError
from erdi_lrf.models import get_model


class FakeSerial:
    """A serial port that answers requests from a scripted response map."""

    def __init__(self, responses=None, stream=b""):
        self.responses = responses or {}
        self.rx = bytearray(stream)
        self.written = bytearray()
        self.closed = False

    def write(self, data):
        self.written += data
        reply = self.responses.get(bytes(data))
        if reply:
            self.rx += reply
        return len(data)

    def read(self, n=1):
        chunk = bytes(self.rx[:n])
        del self.rx[:n]
        return chunk

    def reset_input_buffer(self):
        self.rx.clear()

    def close(self):
        self.closed = True


def factory(responses=None, stream=b""):
    fake = FakeSerial(responses, stream)

    def make(port, baud, timeout):
        fake.port, fake.baud, fake.timeout = port, baud, timeout
        return fake

    make.fake = fake
    return make


def a_reply(function, sta, raw):
    body = bytes([0x55, 0xAA, function, sta, 0xFF, raw >> 8, raw & 0xFF])
    return body + bytes([pa.rx_checksum(body)])


def test_family_a_single_measurement_round_trip():
    f = factory({pa.single_shot(): a_reply(pa.FN_SINGLE, 1, 42)})
    with ErdiLRF("COM_TEST", model="LR1000E2", serial_factory=f) as lrf:
        m = lrf.measure()
    assert m.raw == 42
    assert m.metres == pytest.approx(4.2)
    assert f.fake.written.startswith(pa.single_shot())
    assert f.fake.baud == 115200


def test_family_a_measurement_survives_leading_garbage():
    reply = a_reply(pa.FN_SINGLE, 1, 1500)
    f = factory({pa.single_shot(): b"\x00\x55\x99" + reply})
    with ErdiLRF("COM_TEST", model="LR2000E2", serial_factory=f) as lrf:
        assert lrf.measure().metres == pytest.approx(150.0)


def test_family_b_measurement_reads_a_stream_frame():
    spec = get_model("LRF100H")
    f = factory(stream=pb.build_data_frame(4354, spec) * 3)
    with ErdiLRF("COM_TEST", model="LRF100H", serial_factory=f) as lrf:
        assert lrf.measure().metres == pytest.approx(43.54)
    assert f.fake.baud == 460800


def test_family_b_stream_yields_successive_frames():
    spec = get_model("LRF22VB")
    raws = [1000, 2000, 3000]
    payload = b"".join(pb.build_data_frame(r, spec) for r in raws)
    f = factory(stream=payload)
    with ErdiLRF("COM_TEST", model="LRF22VB", serial_factory=f) as lrf:
        got = []
        it = lrf.stream()
        for m in it:
            got.append(m.raw)
            if len(got) == len(raws):
                break
        it.close()
    assert got == raws


def test_read_serial_number_over_the_wire():
    f = factory({pb.read_serial_number_4(): bytes.fromhex("5A8D0410010000 5D".replace(" ", ""))})
    with ErdiLRF("COM_TEST", model="LRF22VB", serial_factory=f) as lrf:
        assert lrf.read_serial_number() == 272


def test_read_software_version_over_the_wire():
    f = factory({pb.read_software_version(): bytes.fromhex("5A960203026 2".replace(" ", ""))})
    with ErdiLRF("COM_TEST", model="LRF22VB", serial_factory=f) as lrf:
        assert lrf.read_software_version() == "2.3"


def test_spd1200d03_refuses_to_guess_a_baud_rate():
    f = factory()
    with pytest.raises(UndocumentedError) as exc:
        ErdiLRF("COM_TEST", model="SPD1200D03", serial_factory=f)
    assert "BAUD CONFLICT" in str(exc.value)


def test_spd1200d03_works_when_the_baud_rate_is_given_explicitly():
    f = factory({pa.single_shot(): a_reply(pa.FN_SINGLE, 1, 42)})
    with ErdiLRF("COM_TEST", model="SPD1200D03", baud=115200, serial_factory=f) as lrf:
        m = lrf.measure(raise_on_failure=False)
    assert m.raw == 42
    assert m.metres is None


def test_continuous_is_refused_on_models_with_a_protocol_hold():
    f = factory()
    with ErdiLRF("COM_TEST", model="LRF3000A1", serial_factory=f) as lrf:
        with pytest.raises(ProtocolHoldError):
            next(lrf.stream())


def test_continuous_proceeds_when_the_hold_is_acknowledged():
    reply = a_reply(pa.FN_SINGLE, 1, 5000)   # the manual's recorded reply uses 0x88
    f = factory({pa.continuous(): reply * 2})
    with ErdiLRF("COM_TEST", model="LRF3000A1", serial_factory=f) as lrf:
        it = lrf.stream(acknowledge_protocol_hold=True)
        assert next(it).metres == pytest.approx(500.0)
        it.close()


def test_undocumented_capabilities_raise_rather_than_improvise():
    f = factory()
    with ErdiLRF("COM_TEST", model="LRF1500H", serial_factory=f) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.read_frequency()
    with ErdiLRF("COM_TEST", model="LR1000E2", serial_factory=f) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.read_serial_number()
    with ErdiLRF("COM_TEST", model="LRF3000A1", serial_factory=f) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.set_ld_always_on(True)


def test_set_baud_uses_the_models_own_type_table():
    f = factory()
    with ErdiLRF("COM_TEST", model="LR1000E2", serial_factory=f) as lrf:
        lrf.set_baud(56000)                       # TYPE 05 in the LR table
    assert f.fake.written[:3] == b"\x55\xaa\x05"

    f2 = factory()
    with ErdiLRF("COM_TEST", model="SPD1200D03", baud=9600, serial_factory=f2) as lrf:
        lrf.set_baud(57600)                       # TYPE 05 in the D03 table, in D4
    assert f2.fake.written[:3] == b"\x55\xaa\x01"
    assert f2.fake.written[6] == 0x05


def test_set_baud_refuses_a_rate_missing_from_the_models_table():
    f = factory()
    with ErdiLRF("COM_TEST", model="SPD1200D03", baud=9600, serial_factory=f) as lrf:
        with pytest.raises(UndocumentedError):
            lrf.set_baud(128000)                  # in the LR table, not in D03's


def test_close_stops_a_running_stream():
    spec = get_model("LRF22VB")
    f = factory(stream=pb.build_data_frame(1234, spec) * 4)
    lrf = ErdiLRF("COM_TEST", model="LRF22VB", serial_factory=f)
    it = lrf.stream()
    next(it)
    lrf.close()
    assert f.fake.closed
