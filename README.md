# Laser 128EX 1 MB RAM + Clock Expansion

A replacement memory-expansion card for the **Laser 128EX** (and, by the shared connector, the New Laser 128):
**1 MB of battery-backed SRAM** in place of the stock card's 32 DRAMs, plus a **real-time clock** that gives
ProDOS 8 file dates and the time. It plugs into the Laser's internal J13 expansion connector, uses the Laser's
own expansion-RAM interface (`$C0D0–$C0D3`), so the built-in `/RAM5` RAM disk, the firmware and the diagnostics
work unchanged, and the RAM disk survives power-off.

It continues Renée Harke's earlier CPLD + SRAM card for the Laser, which was never finished.

## Status (Nov 2026)
- **Rev 0.2 board: ready to order.** Routed 2-layer, 100 × 90 mm, DRC clean, Gerbers in `hardware/rev02/fab/`.
- **CPLD logic: fitted** (ATF1504AS, 40/64 macrocells); passes its testbench as RTL, fitted equations and decoded
  fuses. The testbench uses strobe timing measured with a scope on a real 128EX (`cpld/rev02/README.md`).
- **ProDOS clock driver: done** (fits in ProDOS's 125-byte clock slot, never disables interrupts), with
  CLOCK.SYSTEM, SET.CLOCK and CARD.TEST on `software/rev02/dist/LASERCLOCK2.po`; emulator-tested.
- **Not yet built.** Next: order boards, assemble, bring up (`docs/bring-up.md`).

## How it works, briefly
The Laser's gate arrays already hold the slinky address register and drive the card with multiplexed DRAM
signals. A CPLD turns those into SRAM addresses and strobes (latching row and column the way DRAM would) for two
512K×8 SRAMs, whose supply and chip enable come from a MAX693A so they keep their contents on a CR2032. J13 has
no spare pins, so the clock (a DS3234 on SPI) is reached **through the RAM data port**: an 8-byte unlock key
written to `$C0D3` switches the CPLD into RTC mode for one transfer. Details: `docs/design-notes.md`.

## Repository
| Path | What |
|---|---|
| `hardware/rev02/` | **Current board**: KiCad 10 schematic + PCB, `fab/` (Gerbers, drill, BOM, placement), renders, README |
| `cpld/rev02/` | CPLD Verilog, testbench (DS3234 model, measured Laser timing), fitter flow and `.jed` |
| `software/rev02/` | ProDOS clock driver, CLOCK.SYSTEM, SET.CLOCK, CARD.TEST, disk image, emulator tests |
| `docs/ordering.md` | What to order (PCB settings, parts list); open checks in `hardware/rev02/todo.md` |
| `docs/bring-up.md` | Assembly order, programming the CPLD, first power-up and tests |
| `docs/scope-tests.md` | How the J13 timing was measured, with monitor test loops |
| `docs/design-notes.md` | Design decisions and history |
| `docs/laser-expansion-interface.md` | The Laser's expansion RAM interface (from the Technical Reference Manual) |
| `docs/sourcing.md`, `docs/mechanical.md` | Part availability; board outline and clearances |
| `hardware/rev01/`, `cpld/rev01/`, `software/rev01/` | Rev 0.1 (DS3231 on I²C): superseded, kept for reference |
| `tools/` | Scripts that generated / edited the boards and fab outputs |
