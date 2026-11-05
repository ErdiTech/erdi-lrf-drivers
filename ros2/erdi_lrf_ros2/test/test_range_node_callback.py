"""Real driver/parser/callback regression; fake serial and minimal ROS types only.

Set L4_DRIVER_ROOT to a pinned source tree. No ROS distro or hardware validation
is performed by these tests.
"""
import importlib.util
import math
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

SOURCE=Path(os.environ.get('L4_DRIVER_ROOT',Path(__file__).resolve().parents[3])).resolve()
sys.path.insert(0,str(SOURCE/'python'))
from erdi_lrf.device import ErdiLRF
from erdi_lrf import protocol_a as pa, protocol_b as pb
from erdi_lrf.models import get_model


class FakeSerial:
    def __init__(self,responses=None,stream=b''):
        self.responses=responses or {}
        self.rx=bytearray(stream)
        self.written=bytearray()
        self.closed=False

    def write(self,data):
        self.written.extend(data)
        self.rx.extend(self.responses.get(bytes(data),b''))
        return len(data)

    def read(self,n=1):
        chunk=bytes(self.rx[:n]);del self.rx[:n];return chunk

    def reset_input_buffer(self):self.rx.clear()
    def close(self):self.closed=True


class Logger:
    def __init__(self):self.warnings=[];self.debugs=[]
    def warn(self,message):self.warnings.append(message)
    def debug(self,message):self.debugs.append(message)


class Timer:
    def __init__(self):self.cancelled=False
    def cancel(self):self.cancelled=True


class FakeNode:
    def get_logger(self):return self.logger
    def get_clock(self):return SimpleNamespace(now=lambda:SimpleNamespace(to_msg=lambda:'host-receive-time'))


class FakeRange:
    INFRARED=1
    def __init__(self):self.header=SimpleNamespace()


@pytest.fixture
def node_type(monkeypatch):
    rclpy=ModuleType('rclpy')
    rclpy_node=ModuleType('rclpy.node');rclpy_node.Node=FakeNode
    sensor=ModuleType('sensor_msgs')
    sensor_msg=ModuleType('sensor_msgs.msg');sensor_msg.Range=FakeRange
    for name,value in [('rclpy',rclpy),('rclpy.node',rclpy_node),('sensor_msgs',sensor),('sensor_msgs.msg',sensor_msg)]:
        monkeypatch.setitem(sys.modules,name,value)
    spec=importlib.util.spec_from_file_location('_l4_real_range_node',SOURCE/'ros2/erdi_lrf_ros2/erdi_lrf_ros2/range_node.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.ErdiRangeNode


def make_node(node_type,model='LR1000E2',continuous=True,responses=None,stream=b''):
    fake=FakeSerial(responses,stream)
    lrf=ErdiLRF('COM_FAKE',model,timeout=.002,serial_factory=lambda *args:fake)
    node=node_type.__new__(node_type)
    node.spec=get_model(model);node.continuous=continuous;node.lrf=lrf
    node._stream=lrf.stream() if continuous else None
    node.timer=Timer();node.logger=Logger();node.published=[]
    node.publisher=SimpleNamespace(publish=node.published.append)
    node.frame_id='test_range';node.field_of_view=0.125
    return node,fake


def a_frame(status,raw,function=pa.FN_SINGLE):
    body=bytes([0x55,0xAA,function,status,0xFF,raw>>8,raw&255])
    return body+bytes([pa.rx_checksum(body)])


def test_exact_maintainer_failure_frame_not_published(node_type):
    frame=bytes.fromhex('55 aa 89 00 ff 01 f4 7c')
    assert frame==a_frame(0,500,pa.FN_CONTINUOUS)
    node,fake=make_node(node_type,responses={pa.continuous():frame})
    try:
        node.on_timer()
        assert node.published==[], 'Invalid STA=0 must not become a valid 50.0 metre Range'
        assert node.logger.debugs
    finally:node.lrf.close();node._stream.close() if node._stream is not None else None


def test_invalid_then_valid_stream_keeps_valid_measurement(node_type):
    frames=a_frame(0,500)+a_frame(1,420)
    node,fake=make_node(node_type,responses={pa.continuous():frames})
    try:
        node.on_timer();node.on_timer()
        assert [x.range for x in node.published]==[42.0]
        assert not node.timer.cancelled
        msg=node.published[0]
        assert msg.header.frame_id=='test_range'
        assert msg.header.stamp=='host-receive-time'
        assert msg.field_of_view==.125
    finally:node.lrf.close();node._stream.close() if node._stream is not None else None


def test_timeout_cancels_timer_and_releases_stream(node_type):
    node,fake=make_node(node_type)
    node.on_timer()
    assert node.timer.cancelled, 'A terminated stream must enter controlled stop'
    assert node._stream is None
    assert not node.lrf._streaming
    assert node.logger.warnings


def test_callback_after_timeout_does_not_crash_or_single_shot(node_type):
    node,fake=make_node(node_type)
    node.on_timer()
    before=bytes(fake.written)
    node.on_timer();node.on_timer()
    assert bytes(fake.written)==before, 'No implicit single-shot fallback or silent stream restart'
    assert node.published==[]


def test_normal_stream_exhaustion_controlled_stop(node_type):
    node,fake=make_node(node_type)
    node._stream=(x for x in ())
    node.on_timer()
    assert node.timer.cancelled
    assert node._stream is None
    node.on_timer()
    assert not fake.written


def test_single_shot_invalid_remains_rejected(node_type):
    node,fake=make_node(node_type,continuous=False,responses={pa.single_shot():a_frame(0,500)})
    node.on_timer()
    assert not node.published
    assert not node.timer.cancelled


def test_single_shot_valid_still_publishes(node_type):
    node,fake=make_node(node_type,continuous=False,responses={pa.single_shot():a_frame(1,420)})
    node.on_timer()
    assert node.published[0].range==42.0


def test_single_shot_timeout_does_not_cancel_regular_polling(node_type):
    node,fake=make_node(node_type,continuous=False)
    node.on_timer();node.on_timer()
    assert not node.timer.cancelled
    assert len(node.logger.warnings)==2


def test_family_b_out_of_range_marker_remains_positive_infinity(node_type):
    model='LRF100H';spec=get_model(model)
    frame=pb.build_data_frame(0xFFFF,spec)
    node,fake=make_node(node_type,model=model,stream=frame)
    try:
        node.on_timer()
        assert math.isinf(node.published[0].range) and node.published[0].range>0
    finally:node.lrf.close();node._stream.close() if node._stream is not None else None


def test_unknown_scaling_model_still_has_no_ros_metre_scale():
    assert get_model('SPD1200D03').metres_per_count is None


def test_protocol_hold_stops_without_sending_or_acknowledging(node_type):
    node,fake=make_node(node_type,model='LRF1200A1')
    node.on_timer()
    assert node.timer.cancelled
    assert not fake.written
    assert node._stream is None
    assert any('PROTOCOL HOLD' in text for text in node.logger.warnings)


def test_cleanup_error_keeps_terminal_state(node_type):
    node,fake=make_node(node_type)
    class BrokenClose:
        def __next__(self):raise StopIteration
        def close(self):raise ValueError('synthetic close failure')
    node._stream=BrokenClose()
    node.on_timer()
    assert node.timer.cancelled and node._stream is None
    assert any('cleanup failed' in text for text in node.logger.warnings)
    node.on_timer()
    assert not fake.written


def test_timeout_after_a_valid_frame_stops_without_republishing(node_type):
    node,fake=make_node(node_type,responses={pa.continuous():a_frame(1,420)})
    node.on_timer();node.on_timer();node.on_timer()
    assert [x.range for x in node.published]==[42.0]
    assert node.timer.cancelled and node._stream is None
