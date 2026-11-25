# Architecture

A replacement for the Laser 128EX's internal memory-expansion card (VTech 702175, 32 × 41256 DRAM): 1 MB of
battery-backed SRAM plus a DS3234 real-time clock, on a 100 × 90 mm 2-layer board that plugs into the Laser's
J13 connector. Rev 0.2 is current. Details and history: `docs/design-notes.md`.

## 1. The Laser side (unchanged)
- The Laser's gate arrays (UDC/MMU) hold the "slinky" expansion-RAM interface: address registers `$C0D0–$C0D2`
  (20 bits), data port `$C0D3` (each access auto-increments the address). Any access to `$C5xx` enables the
  expansion RAM (off after power-up and Ctrl-Reset). The firmware's port-5 RAM disk shows in ProDOS as
  **`/RAM5`** (slot 5, drive 1). The card never sees CPU addresses.
- J13 (2×15, DIP-style numbering: 1–15 down one row, 16–30 back up the other) carries multiplexed DRAM
  signals: ERA0–8 (row then column address), /RASB, /ECAS1–4 (one per 256 KB bank), /RWR (write), MEMRD ('245
  direction), /E1MOE (card data-bus enable, low during a `$C0D3` access), D0–7, +5 V, GND. Refresh cycles
  are RAS-only (no /ECAS). Pinout: `docs/laser-expansion-interface.md`.
- Timing (scoped on a 128EX, Nov 2026; table in `cpld/rev02/README.md`): at 1 MHz /E1MOE is low ~475 ns;
  "accelerated" (2.3 and 3.6 MHz settings) card cycles always run at 2.3 MHz timing with /E1MOE low ~268 ns.
  In accelerated cycles the MMU's delay line drops /RWR up to 4.72 ns **after** /E1MOE; /RASB falls ~80 ns and
  /ECAS ~174 ns after /E1MOE falls.

## 2. The card
| Ref | Part | Role |
|---|---|---|
| U1 | ATF1504AS-10JU44 (PLCC-44, socketed) | All glue logic: latch control, bank decode, SRAM enables, unlock key matcher, SPI port for the RTC |
| U2 | 74AHCT574 | Row register: ERA0–7 → SRAM A9–A16, clocked on /RASB↓ |
| U3 | 74AHCT573 | Column latch: ERA0–7 → SRAM A0–A7, transparent until /ECAS falls |
| U4 | 74AHCT245 | Data buffer card ↔ Laser; DIR = MEMRD (straight from J13), enable = /E1MOE via the CPLD |
| U5, U6 | AS6C4008-55 (512K×8, DIP-32) | The 1 MB. Optional 45 ns CY62148ELL on TSOP-II→DIP adapters |
| U7 | MAX693A | Battery switchover (VOUT = SRAM supply), chip-enable gating below 4.40 V, power-on reset to the CPLD |
| U8 | DS3234SN# (SOIC-20W) | RTC on 3-wire SPI (DIN and DOUT joined), TCXO ±2 ppm, temperature sensor |
| R1 / R2 | 1 kΩ / 47 kΩ | R1 series link CPLD ↔ DS3234 data; R2 pull-down on that line (the driver relies on it) |
| BT1 | CR2032 | Backs the SRAMs (via U7) and the DS3234 |
| J1 / J2 / J3 | — | J13 mate (underside) / JTAG / debug header (GND, DBG0, /RESET, +5V) |

**SRAM address** (any consistent permutation works): A0–A7 = column ERA0–7 (U3), A8 = column ERA8 (CPLD
register on /ECAS↓), A9–A16 = row ERA0–7 (U2), A17 = row ERA8 (CPLD register on /RASB↓), A18 = bank bit 0,
chip select = bank bit 1 (the CPLD gives only the selected chip OE/WE). The bank bits come from **which**
/ECASn fell, so the bank is only known at /ECAS↓: the slowest path is the first read after a bank change
(~2 ns worst-case paper margin at 3.6 MHz with 55 ns SRAM, ~10 ns with 45 ns).

**Battery backup:** U7 switches the SRAM supply (VBB) from +5 V to the coin cell and holds chip-enable high
below 4.40 V. Standby: ~11–15 µA total with the Laser off (≈1.7–2 years per CR2032), ~0.1 µA with it on.

## 3. Reaching the clock through the RAM port
J13 has no spare pins, so the RTC is reached through `$C0D3`:
1. **Unlock:** writing the 8-byte key `8E 27 D1 5B 3F C4 72 A9` to `$C0D3` (all bytes land in RAM normally)
   switches the CPLD into **RTC mode** after the 8th write. A near-miss key doesn't unlock.
2. **RTC mode** (SRAMs deselected): writes with D7 = 1 **lock** (back to RAM mode); D6 = 1 is **control**
   (D0 = chip select, D1 = drive the data line); other writes set the next bit to send. **Every read is one SPI
   clock** and returns `{101101, CS, DIO}` (signature + data bit).
3. SCLK = low while RTC mode · CS · /E1MOE low · **/RASB low** · /RWR high. The /RASB term was added after the
   scope showed the accelerated-mode /RWR lag (it would otherwise put a stray clock at the start of every
   write); SCLK low time is then ≥181 ns (DS3234 needs ≥110 ns).

## 4. Software (ProDOS 8, `software/rev02`)
- **Clock driver** (`clkdrv.s`, 122 bytes): fits entirely in ProDOS's 125-byte clock-driver slot. It saves the
  one RAM-disk byte it writes the key to, unlocks, reads registers 00h–06h over SPI (the pull-down supplies the
  read address 00h), locks, restores the byte, and packs ProDOS DATE/TIME. Interrupts are never disabled.
- **CLOCK.SYSTEM** installs the driver (stands aside if a clock already exists; leaves /RAM alone).
- **SET.CLOCK / CLOCK.SET**: shows the current date, time and temperature, then sets the clock (BB_TD option to
  skip temperature compensation on battery).
- **CARD.TEST / CARDTEST**: RAM tests (quick, full address, battery retention, bank hop) and a clock test with
  date, time and temperature. Sets the CPU speed via `$C074` (0 / 128 / 192 = 1 / 2.3 / 3.6 MHz).
- Disk image: `software/rev02/dist/LASERCLOCK2.po`.

## 5. Where things live
| Path | Contents |
|---|---|
| `hardware/rev02/` | KiCad 10 project, `fab/` outputs, renders, `todo.md` |
| `cpld/rev02/` | Verilog, testbench (DS3234 model + measured timing), `fit/` flow and `.jed` |
| `software/rev02/` | 65C02 sources, BASIC listings, build + emulator tests, `dist/` |
| `docs/` | interface, design notes, ordering, bring-up, scope tests, sourcing, mechanical |
| `tools/` | Python (pcbnew API) scripts that generated/edited the boards, fab export |
| `*/rev01/` | Rev 0.1 (DS3231/I²C), superseded |
