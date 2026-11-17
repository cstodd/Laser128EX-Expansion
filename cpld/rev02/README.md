# CPLD rev 0.2 (DS3234 on 3-wire SPI) — prototype

Same RAM logic and unlock key as rev 0.1 (`../rev01/`); the RTC port drives a DS3234 instead of a DS3231.
See `docs/design-notes.md` §10.

## RTC port (RTC mode only)
| Access | Effect |
|---|---|
| write, D7 = 1 | lock: deselect, release DIO, back to RAM mode |
| write, D6 = 1 | control: D0 = chip select, D1 = drive DIO (address/data out) |
| other write | data bit: D0 = next bit to send. **No clock** |
| read | **one SPI clock**: SCLK low while /E1MOE **and /RASB** are low (≥181 ns fast, ≥352 ns at 1 MHz, scoped; DS3234 needs ≥110 ns); the falling edge shifts out the next DOUT bit, returned in D0 as `{101101, CS, DIO}`; the rising edge latches the data bit written before |

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

## Strobe timing, scoped on a Laser 128EX (Nov 2026)
Siglent SDS1202X-E, 10× probes, J13 on a bare 128EX (no card: the Laser generates all of these). Procedure,
pins and the monitor test loops: [`docs/scope-tests.md`](../../docs/scope-tests.md).
Edges taken at 1.48 V, worst case over ~30 s of persistence, relative to /E1MOE falling.

| | 1 MHz | accelerated (2.3 and 3.6 settings identical: card cycles run at 2.3 MHz) |
|---|---|---|
| /RWR falls (write) | **8.7–14 ns before** | **up to 4.72 ns after** (MMU delay line) |
| /RASB falls | ≤ 34.4 ns after | 79.6–82.8 ns after |
| /RASB low width | ≥ 352 ns | ≥ 181 ns |
| /RASB rises | ~90 ns before /E1MOE rises | just before /E1MOE rises |
| /E1MOE low width | 474–478 ns | 266–270 ns |
| /ECAS falls | ~212 ns after | **≤ 174 ns after** |
| /ECAS rises | just before /E1MOE rises | ~27 ns after /E1MOE rises (harmless: the card is already off) |
| /ECAS outside the /E1MOE window | never | never |
| MEMRD, write: falls / rises | 22–26 ns before /E1MOE falls / ~15–20 ns after /E1MOE rises | 23–24 ns before /E1MOE falls / ~20 ns after /E1MOE rises |
| MEMRD, read | stays high | stays high (no dip) |
| write data (D0) valid | crosses 1.48 V as /E1MOE falls, settled ~25 ns after | crosses 1.48 V as /E1MOE falls, settled ~25 ns after |
| write data (D0) held after /E1MOE rises | ~1.69 µs | ~515 ns (until the CPU drives the bus again) |
| ERA0: row address set | (pending) | ~90 ns before /E1MOE falls (≈170 ns before /RASB↓) |
| ERA0: row → column switch | (pending) | starts ~125 ns, settled ~148 ns after /E1MOE falls (row hold ≈45 ns after /RASB↓, column setup ≈26 ns before /ECAS↓) |
| other /RASB pulses (refresh, Laser's own cycles) | end ≥ ~105 ns before / start ≥ ~60 ns after the /E1MOE window | ≥ ~185 ns before / ≥ ~190 ns after |

**What this changed.** The first design clocked SCLK on `/E1MOE low · /RWR high`, assuming /RWR is valid when
/E1MOE falls. That holds at 1 MHz but not in accelerated cycles: every write would start with a ~5 ns "looks like
a read" window, i.e. a stray SPI clock (the driver writes with CS active). SCLK is now also gated by **/RASB**,
which in every case falls long after /RWR has settled (≥75 ns fast) and appears exactly once inside each /E1MOE
window:

    SCLK = ~(RTC mode · CS · /E1MOE low · /RASB low · /RWR high)

SCLK low time is then the /RASB pulse (≥181 ns fast, ≥352 ns slow), SCLK ends on /RASB↑ (before /RWR can change),
and DOUT (valid ≤80 ns after SCLK↓) settles ~100 ns before the CPU samples it. No board change: /RASB is already
on CPLD pin 2. The testbench now uses these measured timings (fast writes drop /RWR 6 ns after /E1MOE; /RASB at
the latest measured times; /E1MOE 264 ns); the previous logic fails it (29 SPI timing violations), the new logic
passes as RTL, fitted equations and decoded fuses.

**RAM read margin (from the /ECAS measurement).** The bank is only known when /ECAS falls, so the first read after
a bank change starts a full SRAM access at /ECAS↓. With the measured 174 ns, the testbench (all parts at their
datasheet maximum, CPU sampling 10 ns before /E1MOE↑) leaves **2 ns** with 55 ns SRAM (fails from ~176 ns) and
~10 ns with the 45 ns CY62148ELL (fails from ~184 ns); 1 MHz has ~190 ns. Likely pessimistic (the stock DRAM card's
/ECAS→data path is slower), but order the 45 ns alternate too and run `CARD.TEST` option 5 (bank hop) at 3.6 MHz.

**Bring-up check:** with the write loop running in accelerated mode, RTC_SCLK (CPLD pin 36) must stay high
through every write; with the read loop and the RTC selected, it should show one ~180 ns low pulse per read.
