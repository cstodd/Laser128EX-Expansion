# Progress

Last updated: 2026-11-25

## Where we are
**Rev 0.2 boards and parts are ordered** (JLCPCB: 5 boards, 2 layers, 1.6 mm, 1 oz, leaded HASL, tented vias,
order mark removed). Next step is assembly and bring-up by the owner, following `docs/bring-up.md`.

| Part | Status |
|---|---|
| Board (`hardware/rev02`) | Done: routed, DRC 0/0, parity clean, fab outputs in `fab/`. Clearances and J1 position verified physically. Ordered |
| CPLD (`cpld/rev02`) | Done: fitted (40/64 MC), passes RTL / fitted / fuse-level simulation against **measured** 128EX timing |
| Software (`software/rev02`) | Done and emulator-tested: 122-byte ProDOS driver, CLOCK.SYSTEM, SET.CLOCK, CARD.TEST (with date/time/temperature) |
| Real hardware | Not yet built |

## Next
1. Owner assembles a board and brings it up (`docs/bring-up.md`): program the CPLD from J3 power, `/RAM5`
   appears, CARD.TEST tests 1/2/5 at 1 and 3.6 MHz, SET.CLOCK, battery retention.
2. Open first-board checks (`hardware/rev02/todo.md`):
   - CARD.TEST test 5 (bank hop) at 3.6 MHz decides 55 ns vs 45 ns SRAM (~2 ns paper margin with 55 ns).
   - RTC_SCLK (CPLD pin 36) stays high through writes at 3.6 MHz.
   - SRAM standby current on battery (estimate 11–15 µA).
   - Optional ERA8 scope check (only if test 2 fails).
3. Fix whatever bring-up finds (software and CPLD are cheap to change; the board isn't).

## Decisions worth knowing (why things are the way they are)
- **DS3234 (SPI) instead of rev 0.1's DS3231 (I²C)** so the whole ProDOS driver fits the 125-byte clock slot and
  never disables interrupts (DClock/GBBS/AppleWorks/ProTERM-friendly). Rev 0.1 never got built.
- **RTC reached through `$C0D3` with an 8-byte unlock key**, because J13 has no spare pins.
- **SCLK gated by /RASB** (Nov 17): scoping showed /RWR lags /E1MOE by up to 4.72 ns in accelerated cycles.
- **45 ns SRAM recommended as a backup** (Nov 17): scoped /ECAS falls at 174 ns, leaving bank-change reads
  only ~2 ns of worst-case margin with 55 ns parts. Adapter: TSOP-II (1.27 mm), e.g. Chip Quik PA0216; DIP-32
  sockets must be dual-wipe for its square pins.
- DS3234 placed beside the CPLD (rev 0.2 PCB) so the three SPI nets are short; J1's fan-out corridor kept clear.
- Laser +5 V measured 5.13–5.20 V on eight supplies: both SRAM options are fine.
- A microcontroller (Pico) version isn't viable: 1 MB + ~80 ns response + battery retention (see changelog
  2026-11-23).

## Parked ideas
- Apple //c (//c+) variant: research moved to `cstodd/AppleIIC-Expansion` (design notes §11).
- Laser 128 "Quad Hi-Res" ROM investigation: moved to `cstodd/Laser128-QHGR`.
- Cost reduction for a larger run: build 10–20 at once; cheaper SPI RTC (e.g. Epson RX6110SA, needs a driver
  rewrite within 125 bytes); SMD/JLC assembly (TQFP-44 CPLD, SOP SRAMs, no sockets).
- New Laser 128 and 128EX/2: same J13 scope routine (`docs/scope-tests.md`) would confirm compatibility.
- Driver v2 (aux-memory body) is parked; rev 0.2 made it unnecessary.
