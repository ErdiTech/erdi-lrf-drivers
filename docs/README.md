# Field notes index

Maintained by ERDI TECH LTD (ERDILRF). These notes are written for engineers who
have to make a rangefinder work in a real product, not for a datasheet shortlist.
They are vendor notes: every model link points to our own catalogue, and every
claim that depends on a model is left to that model's document.

| Note | Use it when |
|---|---|
| [Evaluation checklist](evaluation-checklist.md) | You are choosing a module or freezing a mechanical design |
| [905 nm vs 1535 nm](905nm-vs-1535nm.md) | You are deciding which wavelength family fits the safety and range case |
| [Flight-controller integration](flight-controller-integration.md) | You need the module in PX4, ArduPilot or ROS 2 |
| [UART hardware notes](uart-hardware-notes.md) | You are wiring the module for the first time |
| [Field troubleshooting](field-troubleshooting.md) | Bytes arrive but the numbers are wrong |

Protocol references live in [Protocol A](protocol-A-55AA.md) and
[Protocol B](protocol-B-5C.md); the model table is in [models](models.md).

## Scope and limits

- No document here certifies native flight-stack support.
- No document here states a laser class for a finished product.
- Range figures always depend on target, reflectivity and visibility; use the
  conditions on the model page.
- Software tests in this repository do not establish live hardware performance.

Catalogue: <https://erdilrf.com/models/> · Contact:
<https://erdilrf.com/contact/> · Company: <https://erdilrf.com/>.
