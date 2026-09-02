"""ROS 2 node publishing ``sensor_msgs/Range`` from an ERDI 905 nm module.

Parameters
----------
port : str
    Serial port, e.g. ``/dev/ttyUSB0``.
model : str
    ERDI model name, e.g. ``LRF3000A1``.  Determines the protocol family,
    the default baud rate, the distance unit and the Range message limits.
baud : int
    ``0`` (default) uses the model's documented default.  ``SPD1200D03``
    has no usable documented default and requires an explicit value.
rate : float
    Publish rate in Hz.
frame_id : str
    ``header.frame_id`` of the published Range message.
field_of_view : float
    Radians.  Defaults to 0.0, meaning "not declared".  The per-model beam
    divergence is in the model's datasheet at https://erdilrf.com/models/ ;
    it is not hard-coded here because the protocol manuals do not carry it.
acknowledge_protocol_hold : bool
    Required to stream continuously on LRF1200A1 / LRF3000A1, whose manuals
    leave the continuous-reply function byte unresolved.
continuous : bool
    Use continuous streaming instead of one request per publish tick.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Range

from erdi_lrf import ErdiLRF, ErdiLrfError, get_model


class ErdiRangeNode(Node):

    def __init__(self):
        super().__init__('erdi_lrf_range')

        self.declare_parameter('port', '/dev/ttyUSB0')
        self.declare_parameter('model', 'LRF3000A1')
        self.declare_parameter('baud', 0)
        self.declare_parameter('rate', 10.0)
        self.declare_parameter('frame_id', 'erdi_lrf')
        self.declare_parameter('field_of_view', 0.0)
        self.declare_parameter('acknowledge_protocol_hold', False)
        self.declare_parameter('continuous', False)

        port = self.get_parameter('port').value
        model = self.get_parameter('model').value
        baud = int(self.get_parameter('baud').value) or None
        rate = float(self.get_parameter('rate').value)
        self.frame_id = self.get_parameter('frame_id').value
        self.field_of_view = float(self.get_parameter('field_of_view').value)
        self.ack_hold = bool(self.get_parameter('acknowledge_protocol_hold').value)
        self.continuous = bool(self.get_parameter('continuous').value)

        self.spec = get_model(model)
        if self.spec.metres_per_count is None:
            raise RuntimeError(
                f'{self.spec.model}: this model\'s manual publishes no distance '
                'scaling, so a sensor_msgs/Range in metres cannot be produced '
                'honestly.  Use the Python API and handle raw counts, or ask '
                'ERDI to confirm the scaling: https://erdilrf.com/contact/'
            )

        self.lrf = ErdiLRF(port, model=model, baud=baud, timeout=1.0 / max(rate, 1.0))
        self.get_logger().info(
            f'{self.spec.model}: family {self.spec.family}, {self.lrf.baud} bps, '
            f'range {self.spec.min_range_m}-{self.spec.max_range_m} m, '
            f'unit {self.spec.unit}'
        )
        for note in self.spec.notes:
            self.get_logger().warn(f'{self.spec.model}: {note}')

        self.publisher = self.create_publisher(Range, 'range', 10)
        self._stream = None
        if self.continuous:
            self._stream = self.lrf.stream(
                acknowledge_protocol_hold=self.ack_hold)
        self.timer = self.create_timer(1.0 / rate, self.on_timer)

    def _make_msg(self, metres: float) -> Range:
        msg = Range()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self.frame_id
        # These modules are single-point time-of-flight rangefinders, not
        # ultrasonic cones; INFRARED is the closest Range.radiation_type.
        msg.radiation_type = Range.INFRARED
        msg.field_of_view = self.field_of_view
        msg.min_range = float(self.spec.min_range_m)
        msg.max_range = float(self.spec.max_range_m)
        msg.range = float(metres)
        return msg

    def on_timer(self):
        try:
            if self._stream is not None:
                m = next(self._stream)
            else:
                m = self.lrf.measure(raise_on_failure=False)
                if self.spec.family == 'A' and not m.ok:
                    self.get_logger().debug(
                        f'measurement failed, STA=0x{m.status:02X}')
                    return
            if getattr(m, 'out_of_range', False):
                # Report the documented marker as +inf rather than as a
                # plausible-looking distance.
                self.publisher.publish(self._make_msg(float('inf')))
                return
            self.publisher.publish(self._make_msg(m.metres))
        except ErdiLrfError as exc:
            self.get_logger().warn(str(exc))

    def destroy_node(self):
        try:
            if self._stream is not None:
                self._stream.close()
            self.lrf.close()
        except Exception:  # noqa: BLE001
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ErdiRangeNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
