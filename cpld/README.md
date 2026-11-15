# CPLD logic: ATF1504AS (PLCC-44)

`laser128_ramcard.v` is the card logic; `tb_laser128_ramcard.v` simulates it inside a model of the
whole card, driven by the Laser's expansion-RAM bus timing (Tech Ref Manual Fig. 11-19).

```sh
iverilog -g2012 -o tb cpld/laser128_ramcard.v cpld/tb_laser128_ramcard.v && vvp -n tb
# try other part speeds:
iverilog -g2012 -Ptb.T_CPLD=7.5 -Ptb.T_AA=45 -o tb cpld/laser128_ramcard.v cpld/tb_laser128_ramcard.v
```

The testbench models the CPLD, 74AHCT574 row register, 74AHCT573 column latch, 74AHCT245, MAX693A CE
delay, and 2× AS6C4008 with datasheet read access times and write-timing checks
(tWP, tDW, data valid at end of write). It runs 400 random writes/reads across all four banks at
1 MHz (with RAS-only refresh) and 3.6 MHz, plus these tests:
- a near-miss key (7 good bytes, then a bad one) must not unlock;
- the correct key unlocks, and the RTC port's SDA/SCL drive and read-back work;
- clock-mode accesses never touch RAM, including the lock write;
- the power-on reset clears clock mode.

## Results (Nov 2026)

| CPLD | SRAM tAA | Logic tests | 3.6 MHz reads |
|---|---|---|---|
| -10 (10 ns) | 55 ns (AS6C4008-55, datasheet max) | pass | **67 of ~130 reads not ready** at the CPU sample point |
| -7 (7.5 ns) | 55 ns | pass | same |
| -10 | 45 ns | pass | pass |
| -7 | 45 ns | pass | **pass, ~9 ns margin** |

The critical path is a bank change. Bank bit 0 (SRAM A18) is only known once /ECASn falls, then
it takes CPLD → SRAM tAA → '245. The Laser edge times are read off a figure that is not to scale, so the absolute
margins are estimates. Real AS6C4008s at 5 V and room temperature are normally faster than the 55 ns
spec, which covers 2.7–5.5 V. Treat 3.6 MHz with 55 ns parts as "probably works, verify on the scope".

## Bugs the simulation caught (fixed)
1. Bank latch race: a latch gated by "any /ECAS low" sees its data change as the gate closes, which glitched
   A18 at the end of 1 MHz writes. Replaced with set/reset latches per bank bit.
2. Mode switch mid-cycle: unlock/lock took effect at the column strobe, so the lock byte (0x80)
   was written into RAM. Mode changes now apply when the write cycle ends.

## Fitting and programming
Not done here (Windows tools). Either use WinCUPL/`fit1504` via the Yosys→EDIF flow
(github: hoglet67/atf15xx_yosys), or Quartus II 13.0sp1 targeting EPM7064SLC44 followed by POF2JED.
Pin constraints: `hardware/README.md`. JTAG programming: ATDH1150USB, or ATMISP + FT232H via SVF.
