# Request/response association on a shared UART rangefinder bus

When one host talks to several rangefinder modules on the same UART — or to one module through a radio link with latency — the hard problem is no longer parsing a frame. It is knowing **which measurement a frame belongs to**.

This note describes a simple, robust scheme that works with any module whose protocol carries an address or a command echo, and what to do when it does not.

## The failure mode

A host sends `MEASURE` to sensor A. The reply arrives late; meanwhile the host sends `MEASURE` to sensor B. If the parser accepts "the next frame that looks valid", B's reply can be attributed to A. The distance is real, the timestamp is wrong, and nothing in the log looks broken.

At 10 Hz this is rare. At 1 kHz, or over a half-duplex RS-485 link with arbitration, it is routine.

## Three association rules, in order of preference

1. **Address in the frame.** If the protocol carries a source address (or the reply echoes the command), key pending requests by `(address, command, sequence)`. Reject replies whose key is not pending.
2. **Explicit sequence number.** Some protocols number requests. Increment per request, wrap at the field width, and never reuse a number while the reply window is open.
3. **Timing window with one outstanding request.** If the protocol gives no identifier, keep exactly one request in flight. The next frame received inside the timeout belongs to that request; anything outside the window is discarded. This costs throughput but removes ambiguity.

Never mix rule 3 with "just read whatever arrives" — that is the case that produces silently misattributed data.

## Timing budget

For each request, record:

```
t_send      host wrote the last byte
t_first     first byte of the reply
t_last      last byte of the reply
```

The deadline is `t_send + (frame_time × 2) + processing_margin`. Frame time is bytes × 10 / baud. At 115200 baud, an 8-byte frame takes about 0.7 ms; at 9600 baud, about 8.3 ms. A 20 Hz module on a 9600-baud link can saturate the wire with replies alone — check the arithmetic before blaming the sensor.

## What to expose to the control loop

- **Measurement timestamp**, taken at `t_first` or `t_last` and carried with the value. A distance without a timestamp is not a measurement.
- **Request id or sequence** so the value can be traced back in the log.
- **Validity flag** that distinguishes "no reply", "checksum error", "out-of-range reply" and "valid distance". These are different faults with different fixes.

## A parser sketch

```
pending = {}                      # key -> (sent_at, deadline)
def request(addr, cmd):
    key = (addr, cmd, next_seq())
    pending[key] = now() + timeout
    write_frame(addr, cmd)
    return key

def on_frame(frame):
    key = frame.key()             # address/seq from the frame
    if key not in pending:        # late, duplicate or unsolicited
        return "unmatched"
    del pending[key]
    return parse(frame)
```

Expire entries in `pending` on every loop tick, and count expiries. A rising expiry count is the earliest signal that the bus is losing frames — earlier than a wrong distance will show it.

Further reading:

- Request/response association: https://erdilrf.com/knowledge/laser-rangefinder-request-response-association/
- UART TTL integration guide: https://erdilrf.com/knowledge/uart-ttl-integration-guide-lrf-modules/
- Raspberry Pi UART notes: https://erdilrf.com/knowledge/raspberry-pi-laser-rangefinder-uart/
- Module list and datasheets: https://erdilrf.com/models/

*Disclosure: maintained by integration support at ERDI TECH LTD (erdilrf.com), a manufacturer of laser rangefinder modules.*
