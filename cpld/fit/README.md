# Fitting the CPLD (ATF1504AS, PLCC-44)

**Ready-made output: `laser128_ramcard.jed`** (JEDEC fuse file, checksum `C4D63`). It works for both the
ATF1504AS-10JU44 and the -7JX44: the speed grade only changes the timing report, and the fuses are identical.
`laser128_ramcard.fit` is the fitter report for the same build.

## What was checked
- Fits: 38/64 macrocells, 9 flip-flops, 31/32 I/O pins, 91 product terms.
- `JTAG ON; Secure OFF`, power-down pins off, pin-keeper off, `power_reset` off.
- Every signal is on the pin the PCB uses (`-preassign keep`, from `pins.txt`). JTAG is on 7/13/32/38 (TDI/TMS/TCK/TDO).
- MEMRD (pin 39) is wired straight to the '245 DIR, so the CPLD doesn't use it. The fitter drops unused inputs,
  so pin 39 shows as NC in the report. The fitter enables no output on it, so it stays an undriven input.
  On the first board, check that pin 39 follows MEMRD.
- Bank bits: each is one macrocell whose feedback holds the value (see the "programmed logic" section of the .fit).
- **Post-fit simulation:** `fit2v.py` turns the fitter's programmed-logic equations (what the .jed holds)
  back into Verilog, and `build.sh` runs `../tb_laser128_ramcard.v` on it. Result: PASS. The output matches the
  RTL run exactly (14.0 ns fast-cycle read margin), including the key, near-miss key, RTC port, lock and reset tests.

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
This runs Yosys, then the fitter, then the post-fit testbench, and copies the .jed and .fit here if it passes.
Intermediate files go to `out/` (git-ignored). Expect two "logic loop" warnings for the bank bits from
Yosys: they are intended.

## Programming
- **ATDH1150USB** (Microchip's USB JTAG cable) with ATMISP 7.x on Windows: create a chain with one
  ATF1504AS, action "Program", load `laser128_ramcard.jed`. Connect it to J2 (10-pin Altera/Atmel layout) with
  the card powered.
- **FT232H or USB-Blaster clone + OpenOCD:** ATMISP can write an SVF file from the .jed (no cable needed for
  that step), and OpenOCD plays the SVF. Same J2 header.
