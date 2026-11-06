# ErdiLRF

Arduino / PlatformIO driver for ERDI 905 nm laser rangefinder modules over UART.

Supports both published ERDI protocol families: the 8-byte `55 AA` command/response protocol (LR / LRF-A1 / SPD1200 series) and the free-running `5C` data-frame protocol (LRF-H and LRF-VB series). Works with `HardwareSerial` or `SoftwareSerial`.

See the examples folder and the main repository: https://github.com/ErdiTech/erdi-lrf-drivers

License: MIT
