# CPLD rev 0.2 (DS3234 on 3-wire SPI) — prototype

Same RAM logic and unlock key as rev 0.1 (`../`); the RTC port drives a DS3234 instead of a DS3231.
See `docs/design-notes.md` §10.

## RTC port (RTC mode only)
| Access | Effect |
|---|---|
| write, D7 = 1 | lock: deselect, release DIO, back to RAM mode |
| write, D6 = 1 | control: D0 = chip select, D1 = drive DIO (address/data out) |
| other write | data bit: D0 = next bit to send. **No clock** |
| read | **one SPI clock**: SCLK low for the /E1MOE-low part of the read (≈214 ns fast, DS3234 needs ≥110 ns); the falling edge shifts out the next DOUT bit, returned in D0 as `{101101, CS, DIO}`; the rising edge latches the data bit written before |

SCLK idles high whenever CS is off (mode 3), so the signature read after unlock clocks nothing.
Sending a bit = write then read; receiving = read. Pins: 34 = /CS, 36 = SCLK, 39 = DIO (DIN and DOUT
together on the board, through a series resistor). Pin 39 no longer carries MEMRD (the '245 has it directly).

## Results (Nov 2026)
- Fits: **40/64 macrocells, 10 flip-flops, 32/32 I/O**, JTAG on (`fit/laser128_ramcard.jed`).
- `tb_laser128_ramcard.v` (rev02) with a DS3234 SPI model that checks SCLK low/high ≥ 110 ns, DIN setup/hold
  30 ns, CS→SCLK 400 ns, CS inactive 400 ns, DOUT 80 ns after SCLK falls, and DIO contention: **PASS** for
  the RTL, the fitter's equations (`fit/fit2v.py`) and the .jed decoded from its fuses (`fit/jed2v.py`):
  burst reads of 00h–06h at 3.6 and 1 MHz, a register write + read-back, plus all rev 0.1 tests
  (RAM, quiet bus, exhaustive key matcher).

## Assumption to verify on hardware
**/RWR must be valid before /E1MOE falls.** SCLK = ~(RTC mode · CS · /E1MOE low · /RWR high); if /RWR settled
after /E1MOE fell, every RTC write would start with a short SCLK glitch (an extra clock). The decoded-fuse
simulation found this when the testbench changed both in the same instant; the testbench now sets /RWR 5 ns
earlier, matching the 65C02 (R/W is valid early in the cycle). Scope /RWR vs /E1MOE on the first board
(rev 0.1 can be used for this).
