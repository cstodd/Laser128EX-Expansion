# Ordering: rev 0.2 board and parts

Rev 0.2 is the board to build (DS3234 real-time clock on SPI). Rev 0.1 (DS3231 on I²C) is kept in
`hardware/rev01` for reference only; it is superseded and has not been built.

## PCB (JLCPCB or similar)
Upload **`hardware/rev02/fab/laser128-ramcard-gerbers.zip`** (Gerbers + merged Excellon drill, all on the
bottom-left board-corner origin).

| Setting | Value |
|---|---|
| Size | 100 × 90 mm |
| Layers | 2 |
| Thickness | 1.6 mm |
| Copper | 1 oz |
| Min track / clearance | 0.2 mm / 0.2 mm (standard process) |
| Min drill | 0.3 mm (vias, 0.6 mm pad; 89 of them) |
| Holes | 357 drill hits, plated, incl. two 3.2 mm mounting holes (H1, H3) |
| Surface finish | HASL is fine; ENIG is easier for the one SOIC part (U8) |
| Solder mask / silkscreen | any colour; silkscreen on both sides (the bottom side marks the J1 socket side) |
| Order number | JLC prints one on the silkscreen by default; its order options let you remove it (extra cost) or place it yourself |

No assembly service is needed: everything is through-hole except **U8** (DS3234, SOIC-20 wide, 1.27 mm pitch,
easy by hand). `hardware/rev02/fab/laser128-ramcard-all-pos.csv` (KiCad placement) and `-bom.csv` are there if
you ever want assembly.

Before uploading, look at the previews: `hardware/rev02/render-gerber-top.png` / `-bottom.png` (made from the
Gerbers themselves) and the KiCad 3D renders. The JLC online Gerber viewer should show the same picture.

## Parts (per board)

| Ref | Qty | Part | Notes |
|---|---|---|---|
| U1 | 1 | **ATF1504AS-10JU44** (or -7JX44, faster) | PLCC-44. Programmed via J2 (see `cpld/rev02/README.md`) |
| — | 1 | **PLCC-44 through-hole socket** (e.g. Assmann A-CCS 044-Z-T, 8.28 mm high) | for U1 |
| U2 | 1 | **74AHCT574** DIP-20 | not LS/HC/HCT |
| U3 | 1 | **74AHCT573** DIP-20 | not LS/HC/HCT |
| U4 | 1 | **74AHCT245** DIP-20 | HCT works, but is ~10 ns slower |
| — | 3 | DIP-20 socket (0.3") | |
| U5, U6 | 2 | **AS6C4008-55PCN** DIP-32 | 2.7–5.5 V. **Not** a 3.3 V-only part |
| — | 2 | DIP-32 socket (0.6"), **stamped dual-wipe** | not machined round-pin: the PA0216 adapter's 0.025" square pins don't fit those |
| (alt) | 2 | **CY62148ELL-45ZSXI** + **TSOP-II-32 → DIP-32 adapter** | **Recommended to order too.** Scoped /ECAS timing leaves the 55 ns parts only ~2 ns of worst-case margin on a bank-change read at 3.6 MHz (~10 ns with these; `docs/sourcing.md`). Fit them if `CARD.TEST` option 5 (bank hop) fails at 3.6 MHz. The adapter must be **TSOP-II** (1.27 mm pitch), not the common TSOP-I (0.5 mm) type: **Chip Quik PA0216** checked (TSOP-32(II), 1.27 mm, 10.16 mm body, 0.600" DIP, 0.025" square pins), but stock is thin; any 1:1 TSOP-II/SOP-32 400-mil → 0.6" DIP-32 adapter works (the A17/A18 swap between the two pinouts is harmless for SRAM). ~7–7.5 mm high in a socket, under the 11 mm to the shield. Needs the Laser's +5 V ≳ 4.8 V (part min 4.5 V, MAX693A drops 0.2–0.3 V) |
| U7 | 1 | **MAX693ACPE+** DIP-16 | 4.40 V threshold. Not the MAX691A (4.65 V) |
| — | 1 | DIP-16 socket (0.3") | |
| U8 | 1 | **DS3234SN#** | SOIC-20 wide (300 mil), soldered (no socket). ±2 ppm 0–40 °C |
| BT1 | 1 | Keystone 103 (or equivalent 20 mm through-hole) CR2032 holder + CR2032 | check that the footprint matches the holder you buy |
| J1 | 1 | **2×15 female socket, 2.54 mm** | fitted on the **underside**; pin 1 = square pad |
| J2 | 1 | 2×5 shrouded IDC header, 2.54 mm | JTAG (Altera/Atmel 10-pin layout) |
| J3 | 1 | 1×4 pin header | debug: GND, DBG0, /RESET, +5V. Optional |
| C1–C11 | 11 | 100 nF ceramic, 5 mm pitch | C9 decouples U8, C3 the CPLD |
| C12 | 1 | 1 µF ceramic (X7R), 5 mm pitch | battery-backed rail. Ceramic, not electrolytic (leakage) |
| C13 | 1 | 22 µF electrolytic, 2 mm pitch, 5 mm dia | +5 V bulk |
| R1 | 1 | **1 kΩ** ¼ W, mounted **vertically** (2.54 mm pitch) | series link CPLD RTC_DIO ↔ DS3234 DIN/DOUT |
| R2 | 1 | **47 kΩ** ¼ W, mounted **vertically** (2.54 mm pitch) | pull-down on DIN/DOUT: the driver relies on it to send read address 00h |
| R3, R4 | 2 | 10 kΩ ¼ W (10.16 mm pitch) | JTAG TMS/TDI pull-ups |
| R5 | 1 | 1 kΩ ¼ W (10.16 mm pitch) | JTAG TCK pull-down |
| H1, H3 | — | M3 screws / standoffs | H1 = the Laser's standoff; H3 = your spacer |

Machine-readable BOM: `hardware/rev02/fab/laser128-ramcard-bom.csv` (sockets not listed).

Also needed: a JTAG programmer for the ATF1504AS (ATDH1150USB with ATMISP, or an FT232H / USB-Blaster with
OpenOCD and an SVF; `cpld/rev02/README.md`).

## Before ordering
1. Print `hardware/rev02/fab/laser128-ramcard-F_Cu.gtl` (or the KiCad PCB) at 1:1. Check J1 against a real
   2×15 socket and the stock card: pin 1 position, and 23.0 mm from the J1 bottom pins to the H1 centre
   (unchanged from rev 0.1 and re-checked on the rev 0.2 board).
2. Measure the Laser's +5 V at J13 pins 1–2 (should be ~5 V; the MAX693A locks out the SRAM below 4.4 V, and
   the 45 ns SRAMs want ≳ 4.8 V there).
3. Battery: expect roughly 10–13 µA with the Laser off (about 2 years per CR2032).
4. Height above the card: **11 mm** measured to the RF shield; the PLCC socket with chip is 8.28 mm and a
   socketed TSOP adapter ~7–7.5 mm (`docs/mechanical.md`).

## After the boards arrive
`docs/bring-up.md`: assembly order, power checks before fitting chips, programming the CPLD, and the tests.
