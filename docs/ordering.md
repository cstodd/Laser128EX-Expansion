# Ordering: rev 0.1 board and parts

## PCB
Upload `hardware/fab/laser128-ramcard-gerbers.zip` (Gerbers + Excellon drill) to JLCPCB or similar.

| Setting | Value |
|---|---|
| Size | 108 × 90 mm |
| Layers | 2 |
| Thickness | 1.6 mm |
| Copper | 1 oz |
| Min track / clearance | 0.187 mm / 0.2 mm (standard process) |
| Min drill | 0.3 mm (vias) |
| Surface finish | HASL or ENIG (ENIG is easier for the SOIC DS3231) |

No assembly is needed: every part is through-hole except U8 (SOIC-16W, 1.27 mm pitch).

## Parts (per board)

| Ref | Qty | Part | Notes |
|---|---|---|---|
| U1 | 1 | **ATF1504AS-10JU44** (or -7JX44, faster) | PLCC-44 |
| — | 1 | **PLCC-44 through-hole socket** | for U1 |
| U2 | 1 | **74AHCT574** DIP-20 | not LS/HC/HCT |
| U3 | 1 | **74AHCT573** DIP-20 | not LS/HC/HCT |
| U4 | 1 | **74AHCT245** DIP-20 | HCT works, but is ~10 ns slower |
| — | 3 | DIP-20 socket (0.3") | |
| U5, U6 | 2 | **AS6C4008-55PCN** DIP-32 | 2.7–5.5 V. **Not** a 3.3 V-only part |
| — | 2 | DIP-32 socket (0.6") | |
| (alt) | 2 | CY62148ELL-45ZSXI + TSOP-II-32 → DIP-32 adapter | **not needed**: expansion RAM runs at ≤2.3 MHz, so the 55 ns part has ~74 ns margin |
| U7 | 1 | **MAX693ACPE+** DIP-16 | 4.40 V threshold. Not the MAX691A (4.65 V) |
| — | 1 | DIP-16 socket (0.3") | |
| U8 | 1 | **DS3231M+** (or DS3231SN#) | SOIC-16 wide (300 mil) |
| BT1 | 1 | Keystone 103 (or equivalent 20 mm through-hole) CR2032 holder + CR2032 | check that the footprint matches the holder you buy |
| J1 | 1 | **2×15 female socket, 2.54 mm** | fitted on the **underside**; pin 1 = square pad |
| J2 | 1 | 2×5 shrouded IDC header, 2.54 mm | JTAG (Altera/Atmel 10-pin layout) |
| J3 | 1 | 1×4 pin header | debug: GND, DBG0, /RESET, +5V |
| C1–C11 | 11 | 100 nF ceramic, 5 mm pitch | |
| C12 | 1 | 1 µF ceramic (X7R), 5 mm pitch | battery-backed rail. Ceramic, not electrolytic (leakage) |
| C13 | 1 | 22 µF electrolytic, 2 mm pitch, 5 mm dia | +5 V bulk |
| R1, R2 | 2 | 4.7 kΩ ¼ W | I²C pull-ups |
| R3, R4 | 2 | 10 kΩ ¼ W | JTAG TMS/TDI pull-ups |
| R5 | 1 | 1 kΩ ¼ W | JTAG TCK pull-down |
| H1–H3 | — | M3 screws / standoffs | H1 = the Laser's standoff; H2/H3 = your spacers |

Machine-readable versions: `hardware/fab/laser128-ramcard-bom.csv` and `-cpl.csv` (sockets not listed).

## Before ordering
1. Print `hardware/fab/laser128-ramcard-F_Cu.gtl` (or the KiCad PCB) at 1:1. Check J1 against a real
   2×15 socket and the stock card: pin 1 position, and 23.0 mm from the J1 bottom pins to the H1 centre.
2. Measure the Laser's +5 V at J13 pins 1–2 (should be ~5 V; the MAX693A locks out the SRAM below 4.4 V).
3. Check height clearance above the card: the PLCC socket with chip, the CR2032 holder, and any TSOP adapter.
