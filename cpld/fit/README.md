# Fitting the CPLD (ATF1504AS, PLCC-44)

**Ready-made output: `laser128_ramcard.jed`** (JEDEC fuse file, checksum `C4D63`). It works for both the
ATF1504AS-10JU44 and the -7JX44: the speed grade only changes the timing report, and the fuses are identical.
`laser128_ramcard.fit` is the fitter report for the same build.

## What was checked
- Fits: 38/64 macrocells, 9 flip-flops, 31/32 I/O pins, 91 product terms.
- `JTAG ON; Secure OFF`, power-down pins off, pin-keeper off, `power_reset` off.
- Every signal is on the pin the PCB uses (`-preassign keep`, from `pins.txt`). JTAG is on 7/13/32/38 (TDI/TMS/TCK/TDO).
- MEMRD (pin 39) is wired straight to the '245 DIR, so the CPLD doesn't use it. The fitter drops unused inputs,
  so pin 39 shows as NC in the report. **Confirmed from the fuses** (below): its macrocell (MC57) has
  `oe_mux = GND` and its logic powered down, so the CPLD can never drive it.
- Bank bits: each is one macrocell whose feedback holds the value (see the "programmed logic" section of the .fit).
- **Post-fit simulation:** `fit2v.py` turns the fitter's programmed-logic equations (what the .jed holds)
  back into Verilog, and `build.sh` runs `../tb_laser128_ramcard.v` on it. Result: PASS. The output matches the
  RTL run exactly (14.0 ns fast-cycle read margin), including the key, near-miss key, RTC port, lock and reset tests.

## Fuse-level check (the .jed itself)
The post-fit simulation above trusts the fitter's report to match its own .jed. `jed2v.py` removes that trust:
it decodes `laser128_ramcard.jed` using only Project Bureau's open fuse database
(github.com/whitequark/prjbureau, `database.json`, Mar 2025) and writes Verilog, which then runs through the
same testbench. Result: **PASS**, identical results (14.0 ns margin, 0 key-matcher errors). Read straight from
the fuses: JTAG on, PD1/PD2 = user I/O, read protection off, TMS/TDI pull-ups on, and every pin's
direction and output enable as expected.

What it relies on, and how each was checked:
- **prjbureau gap:** the database lacks `d_mux`/`o_mux`/`oe_mux` for **MC46** (pin 31, `buf_oe_n`) only. Those
  fuses step regularly from one macrocell to the next, so `jed2v.py` interpolates them from MC44/MC48 (checked
  unclaimed by any other field) and prints a NOTE when it does.
- **XOR polarity** (`xor_invert`): the docs' table for this is marked WIP. The hardware-measured truth table in
  prjbureau `notes/xor.txt` is used instead; on = non-inverting.
- **Cascade direction** (MC n → n+1): not in the database; taken from the fitter report.
- **Sensitivity:** each of those choices was deliberately broken in turn (polarity swapped, cascade reversed,
  P/N literal sense swapped, MC46's inferred output enable forced off), and each one fails the testbench.
- **Corrupted-fuse campaign** (40 random single product-term fuses: 20 literals removed, 20 added):
  - 20 caught by the original testbench;
  - 5 more caught after the gaps they exposed were closed (key writes in all four banks, RAM read back out of
    order plus a bank-alias test, and a quiet-bus check that SRAM CE and the '245 are off between card cycles);
  - 1 (A18 never set by bank 1) inconclusive: with no defined power-up state the simulation drowns in X
    values and never finishes, so it doesn't pass either;
  - the other 14 make no functional difference and can't be caught by any test: literals that are
    always true (an unused routing input, or a foldback line from a macrocell without foldback),
    terms that can never be true (e.g. "/ECAS4 low while bank bit 1 = 0": /ECAS4 sets that bit
    combinationally, and the fitter kept these redundant terms), or a hold term for a register that is
    always 0 outside clock mode.

Only the macrocell features this design uses are modelled (no latches, no flip-flop-feedback XOR); the script
stops if it meets anything else.

The exhaustive key-matcher test (section 7 of the testbench, 2048 state×byte cases) was added because the first
corrupted-fuse trial, which removed one condition from a key-matcher term, slipped past the original testbench. It takes
~45 s; `vvp ... +quick` skips it.

## Rebuilding
Tools (Linux; all free):
1. `yosys` (0.33 used), `iverilog`, `python3`.
2. `wine` with 32-bit support (Ubuntu: `dpkg --add-architecture i386; apt install wine wine32:i386`).
3. `git clone https://github.com/hoglet67/atf15xx_yosys`
4. Atmel's fitter, from Microchip's `ProChip5.0.1.zip`:
   `innoextract ProChip5_setup.exe`, then copy `app/Prochip/pldfit/{atmel.std,aprim.lib,fit1502.exe,fit1504.exe,fit1508.exe}`
   into `atf15xx_yosys/vendor/` (that folder's README lists the sha1sums; ours matched).

```
ATF15XX_YOSYS=/path/to/atf15xx_yosys ./build.sh
```
This runs Yosys, then the fitter, then the post-fit testbench, then (if `PRJBUREAU=/path/to/prjbureau` is set)
the fuse-level check, and copies the .jed and .fit here only if everything passes.
Intermediate files go to `out/` (git-ignored). Expect two "logic loop" warnings for the bank bits from
Yosys: they are intended.

## Programming
- **ATDH1150USB** (Microchip's USB JTAG cable) with ATMISP 7.x on Windows: create a chain with one
  ATF1504AS, action "Program", load `laser128_ramcard.jed`. Connect it to J2 (10-pin Altera/Atmel layout) with
  the card powered.
- **FT232H or USB-Blaster clone + OpenOCD:** ATMISP can write an SVF file from the .jed (no cable needed for
  that step), and OpenOCD plays the SVF. Same J2 header.
