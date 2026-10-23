# Integrating a laser rangefinder with PX4 or ArduPilot

Maintained by ERDI TECH LTD (ERDILRF). This note describes integration patterns.
It does **not** claim that any ERDI module is natively supported by PX4, ArduPilot
or ROS 2. Native support depends on the flight-stack driver matching the module's
protocol, and on a bench test with the exact firmware revision.

## Three patterns

### 1. Native driver (only if the protocol matches)

Both stacks ship drivers for a set of rangefinder protocols. A module can use a
native driver only when its frame format, baud rate and timing match one of those
drivers. Check the driver source for the exact frame layout before wiring.

- ArduPilot: <https://ardupilot.org/copter/docs/common-rangefinder-landingpage.html>
- PX4: <https://docs.px4.io/main/en/sensor/rangefinders>

If the frame does not match, do not "try the closest driver". A driver that
accepts the frame but misreads the distance field is worse than no driver.

### 2. Companion computer publishing MAVLink `DISTANCE_SENSOR`

This is the pattern we recommend for first integration:

1. Read the module over UART from a companion computer (Raspberry Pi, Jetson,
   flight-controller-adjacent Linux board).
2. Validate the frame and the status field.
3. Publish `DISTANCE_SENSOR` (`DISTANCE_SENSOR` message id 132) with
   `MIN_DISTANCE`, `MAX_DISTANCE`, `CURRENT_DISTANCE`, `ORIENTATION` and the
   `COVARIANCE` field set from your own log.
4. Subscribe on the flight controller and map it to the rangefinder input.

Advantages: the flight stack only sees a stable MAVLink stream, and you can filter
outliers in one place. The cost is an extra board and a power budget.

### 3. ROS 2 node

For ground robots and benches, the ROS 2 node in this repository publishes a
`Range` message. See [`ros2/`](../ros2/) and the launch file. A ROS 2 node is not a
flight-controller driver; do not assume that publishing `Range` makes the module
appear in PX4 or ArduPilot.

## Bench validation before flight

| Step | Pass condition |
|---|---|
| Frame capture at the real baud rate | 100% of frames parse with a valid checksum over 10 minutes |
| Static distances at 3 targets | Error inside the module's stated accuracy at each distance |
| Moving target at the intended rate | No aliasing; dropouts counted, not hidden |
| Vibration and motor noise | Outlier rate unchanged from the static test |
| Power interruption | Driver recovers without a reboot |
| Log review | Every rejection has a reason code |

Keep the raw log. A plot of filtered output is not evidence.

## Common mistakes

- Assuming the rangefinder is the only consumer of the UART; a second reader
  corrupts the stream.
- Mapping a downward rangefinder to a forward orientation (or the reverse) and
  blaming the sensor.
- Using the module's maximum range as the flight-stack `MAX_DISTANCE` without
  checking the target at the real attitude.
- Forgetting that the flight stack expects a minimum distance and rejects values
  below it.
- Reporting a successful bench test as "supported by PX4".

Background on the driver side:
[PX4 laser rangefinder integration notes](https://erdilrf.com/knowledge/px4-laser-rangefinder-integration/).
Model index: <https://erdilrf.com/models/>.
