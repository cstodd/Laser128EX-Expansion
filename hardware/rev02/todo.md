# Rev 0.2 to-do

## Before ordering
- [x] **J1 position and orientation** (physical clearances verified on the board, Nov 2026). Print `fab/laser128-ramcard-F_Cu.gtl` (or the KiCad PCB) at 1:1 and lay it
      on the stock card or a real 2×15 socket: pin 1 in the same place (J1 uses DIP-style numbering, pins 1–15
      down one row and 16–30 back up the other, not KiCad's odd/even), and 23.0 mm from the J1 bottom pins to the
      H1 centre. The board can't be fixed after ordering.
- [ ] **Laser +5 V under load at J13 pins 1–2.** The MAX693A deselects the SRAMs below 4.40 V, and the optional
      45 ns CY62148ELL needs ≥ 4.5 V after the MAX693A's 0.2–0.3 V drop, so ≳ 4.8 V at J13. If it is lower,
      the 45 ns fallback is doubtful.
- [ ] *(optional)* **ERA8 timing, J13 pin 10.** Only ERA0 was scoped; ERA8 is the address line the CPLD registers
      itself (row bit 8 on /RASB↓, column bit 8 on /ECAS↓). Plain write loop at 3.6 MHz
      (`docs/scope-tests.md`): it should switch where ERA0 does (~90 ns before and ~148 ns after /E1MOE falls).

## On the first board (`docs/bring-up.md`)
- [ ] CARD.TEST test 5 (bank hop) at 3.6 MHz: decides 55 ns vs 45 ns SRAM (the CPU's read-sample point can't be
      scoped; ~2 ns worst-case paper margin with 55 ns parts).
- [ ] RTC_SCLK (CPLD pin 36) stays high through writes at 3.6 MHz.
- [ ] SRAM standby current on battery (decides real battery life; estimate 11–15 µA total).
