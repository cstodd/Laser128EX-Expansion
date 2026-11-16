# Rev 0.2 clock driver (DS3234 / SPI) — prototype

`clkdrv.s`: the **whole ProDOS clock driver in ProDOS's 125-byte clock slot** (currently 122 bytes, enforced
by an assert). No aux-memory body, no stub, no checksum, no /RAM removal. Needs the rev 0.2 CPLD
(`cpld/rev02/`) and board (DS3234 on SPI, **pull-down** on the shared DIN/DOUT line).

How it works:
1. Enable the expansion RAM (`bit $C500`), point the slinky address at byte `00` of the current page, save
   that one RAM-disk byte.
2. Write the 8-byte unlock key **and** the chip-select control byte, all to that same byte (low address byte
   reset to 0 before each write). The last write is the chip-select because RTC mode starts after the 8th.
3. 64 reads, each one SPI clock: with DIO undriven, the pull-down sends address 00h; the first byte read is
   discarded, then registers 00h–06h (BCD → binary in the loop) land in `$200-$206`.
4. Lock and restore the saved byte, both aimed at byte `00`, so a card without the RTC (never in RTC mode)
   can only ever touch that one restored byte.
5. Pack ProDOS DATE/TIME.

**Interrupts are never disabled** (no interrupts-off window). This relies on no interrupt handler using the
expansion RAM while the driver runs (serial, mouse and timer handlers don't). `php/sei/plp` would push the
driver past 125 bytes. About 1,600 cycles per call (~1.6 ms at 1 MHz).

Scratch: `$3B-$3D` (ProDOS's own clock driver uses `$3A-$3E`) and `$200-$207` (ProDOS TN #1). The slinky
address's mid/high bytes are kept; its low byte ends at `01` (the RAM-disk firmware sets the address before
each transfer, as with the DClock driver).

Installer (to do, rev 0.2 CLOCK.SYSTEM): probe for the rev 0.2 RTC, copy the driver to `DATETIME+1`, patch the
key-table pointer (`KEYOP_OFS` → slot + `KEYREV_OFS`), set `DATETIME` to `JMP`, set the MACHID clock bit, chain.
Also to do: rev 0.2 CLOCK.SET (SPI writes, 24-hour mode, and the BB_TD / CRATE settings) and CARD.TEST's
clock test.

## Test
`python3 software/rev02/test_drv.py`: 65C02 emulation (the rev 0.1 harness) with the rev 0.2 CPLD port
and a DS3234 model. Six dates/times (incl. 2099-12-31 23:59 and months 8–12) at slinky addresses on page
boundaries and the 1 MB wrap: correct DATE/TIME, RAM disk bit-for-bit unchanged, address mid/high kept,
card back in RAM mode, no DIO contention, main memory untouched outside the scratch areas, interrupts never
disabled; plus a card without the RTC (returns, RAM disk unchanged). **ALL PASS.**
