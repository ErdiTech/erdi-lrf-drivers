# UART hardware notes for laser rangefinder modules

Maintained by ERDI TECH LTD (ERDILRF). These notes cover the wiring problems we
see most often. They are generic electrical guidance, not a wiring diagram for a
specific model; use the model's own document for pin order.

## Logic level is not supply voltage

A module that runs from 5 V may still use 3.3 V UART levels, or the reverse. Read
both rows of the electrical table before connecting a host. If the host is 3.3 V
and the module output is 5 V, use a level shifter or a series/divider network on
the module TX line; do not rely on the host pin being "5 V tolerant".

Background: [UART/TTL integration guide](https://erdilrf.com/knowledge/uart-ttl-integration-guide-lrf-modules/).

## Grounds and returns

- Connect signal ground and power ground at one point near the module.
- Do not use the cable shield as the return conductor.
- On a vehicle, a long ground loop between the module and the controller picks up
  ESC current. Twisted pair for TX/RX and a separate supply pair is usually
  enough; a ferrite at the module end helps with motor noise.

## Supply

- Size the regulator for the peak current, not the average.
- Put 10–100 µF bulk capacitance near the module and a 100 nF ceramic at the
  connector.
- Check the module's brown-out behaviour: some units emit a valid-looking frame
  with a zero or maximum distance during start-up.
- If the module shares a rail with a motor or a servo, power it from a separate
  regulator.

## Cable length

TTL UART is not a field bus. At 115200 baud, keep the run short and shielded; if
the module must sit far from the controller, convert to RS-485 or move the reader
next to the module and send the parsed result over a robust link. Do not "fix"
long-cable errors by lowering the baud rate alone: the checksum will still fail
under motor noise.

## Connector discipline

- Record the mating connector part number in your build documentation.
- Pin order is not standard across vendors; a mirrored connector can put the
  supply on the TX pin.
- Strain-relieve the cable at the module; the connector is not a load-bearing part.

## What the module does not include

- No galvanic isolation.
- No reverse-polarity protection on every model; check the datasheet.
- No surge protection for outdoor cable runs.
- No guarantee that the UART is silent during power-up.

## First power-on sequence

1. Current-limited bench supply at the nominal voltage.
2. Measure the TX idle level before connecting the host.
3. Connect ground first, then TX/RX, then power.
4. Capture bytes with a logic analyser or a terminal at the documented baud rate.
5. Confirm the frame header and checksum before writing a parser.

Frame layout for the two ERDI protocol families is in
[Protocol A](protocol-A-55AA.md) and [Protocol B](protocol-B-5C.md).
Model index and per-model documents: <https://erdilrf.com/models/>.
