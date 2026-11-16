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
- the key matcher, exhaustively: every state (0–7 bytes matched) × every byte value, 2048 cases, each
  checked by which key tails then unlock. It takes ~45 s; add `+quick` to the `vvp` command to skip it.

## Results (Nov 2026)

**Tech Ref Manual, Appendix A (p. A-3):** the 128EX never runs expansion-RAM cycles at 3.6 MHz. At the
3.6 MHz setting the clock drops to 2.3 MHz for every expansion-RAM access. So the fast bus cycle has
CPUP0 high for ~217 ns (`PH_FAST`).

**Strobe positions are an inference.** The MMU builds the fast-mode strobes from a delay line with taps
D60, D90 and D120. The testbench puts /RASB at +60 ns, the column address at +90 ns and /ECAS at +120 ns.
That leaves ~97 ns from /ECAS to the CPU's sample point, which fits Renée Harke's observation that 120 ns
DRAMs (60 ns from CAS) work and 150 ns ones (75 ns) do not.

| CPLD | SRAM tAA | Logic tests | Fast-cycle read margin (worst-case datasheet delays) |
|---|---|---|---|
| -10 | 55 ns (AS6C4008-55) | pass | **~14 ns** |
| -7 | 55 ns | pass | ~16 ns |
| -10 | 45 ns (CY62148ELL on adapter) | pass | ~24 ns |

The tight path is the first access after a **bank change**: A18 is only known when /ECASn falls, then
CPLD → SRAM tAA → '245. Within one bank the address is ready earlier and the margin is larger. Real parts
at 5 V and room temperature are faster than these worst-case numbers, so expect it to work, but with modest
margin. `CARD.TEST` option 5 (bank-hop test) exercises exactly this path in-system; run it at 3.6 MHz.
If it fails, fit the 45 ns SRAM on a TSOP-to-DIP adapter or a -7 CPLD.

## Bugs the simulation caught (fixed)
1. Bank latch race: a latch gated by "any /ECAS low" sees its data change as the gate closes, which glitched
   A18 at the end of 1 MHz writes. Replaced with set/reset latches per bank bit.
2. Mode switch mid-cycle: unlock/lock took effect at the column strobe, so the lock byte (0x80)
   was written into RAM. Mode changes now apply when the write cycle ends.

## Fitting and programming
**Done: `fit/laser128_ramcard.jed`** is the programming file (both the -10JU44 and the -7JX44; same fuses).
Flow, all on Linux: Yosys → hoglet67/atf15xx_yosys → Atmel `fit1504.exe` under Wine. `fit/build.sh` reruns it
and has three checks, each of which must pass before the .jed is accepted:
1. **RTL testbench** (`tb_laser128_ramcard.v`) on the source design.
2. **Post-fit:** the fitter's own equation listing, turned back into Verilog (`fit/fit2v.py`), on the same testbench.
3. **Fuse-level:** the .jed itself, decoded with Project Bureau's open fuse database (`fit/jed2v.py`), on the
   same testbench. This one doesn't trust the fitter at all.

All three pass with identical results. Details, the one prjbureau database gap (MC46) and how it was
handled, and tool setup: `fit/README.md`. Pin constraints: `fit/pins.txt` (matches `hardware/README.md`).
JTAG programming via J2: ATDH1150USB + ATMISP (loads the .jed directly), or FT232H/USB-Blaster + OpenOCD
with an SVF made by ATMISP.

The fallback flow (Quartus II 13.0sp1 for EPM7064SLC44, then POF2JED) wasn't needed.

**Fitter settings that matter:**
- **Keep JTAG enabled** (`-strategy JTAG on` / the ISP device variant). A design fitted with JTAG off can
  no longer be programmed in-circuit. Recovery needs 12 V on OE1/VPP (pin 44), which this board wires to
  J1 as /ECAS2, so the chip would have to be pulled and erased in a standalone programmer.
- **Power-down pins off** (PD1 = pin 11, PD2 = pin 25): both are used as ordinary I/O (XD1, /RAM_CE).
- **Latches:** the design no longer relies on latch inference. `ma8` is a flip-flop. The two bank bits are
  set/reset latches written out as `Q = S | (Q & ~R)`, which is glitch-free as a plain sum of products.
  Synthesis reports two "logic loop" / combinational-feedback warnings for `bank[0]` and `bank[1]`:
  **these are intended.** In the fitter report, check that each bank bit is one macrocell with feedback and
  that the equation still has both terms.
- **Result (Nov 2026):** 38/64 macrocells, 9 flip-flops, 31/32 I/O, JTAG on, PD1/PD2 off, every pin as on
  the PCB. Both bank bits came out as one macrocell each with both terms intact
  (`ma18 = !ecas2_n # !ecas4_n # (ecas1_n & ecas3_n & ma18)`), read both from the fitter report and from the
  decoded fuses. MEMRD's pin 39 has its output permanently off in the fuses.

On the first board, scope /ECAS against /E1MOE at the fast-cycle boundary. The logic assumes the
previous cycle's /ECAS has gone high before the next /E1MOE falls.
