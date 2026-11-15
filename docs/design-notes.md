# Laser 128EX Battery-Backed SRAM Expansion + Clock — Design Notes

Status: **parts locked, moving to KiCad symbols/footprints, then CPLD logic.**
Interface facts (pinout, timing) are in [`laser-expansion-interface.md`](laser-expansion-interface.md).
The decisions below come from the earlier design conversation (Claude.ai, Nov 2026) and were re-checked
against the Technical Reference Manual.

## 1. How it works

- The stock card (VTech 702175) is only DRAM: 32 × 41256 in four 256 KB banks. The Laser
  motherboard holds the slinky address register and auto-increment (`$C0D0–$C0D3`) and drives
  the card with multiplexed DRAM signals: ERA0–8, /RASB, /ECAS1–4, /RWR, MEMRD, /E1MOE and D0–7.
- Our card latches the row on /RASB↓ and the column plus bank on /ECASn↓, which gives a
  20-bit SRAM address. RAS-only refresh cycles are ignored. The existing Laser firmware, the ProDOS
  RAM disk and the built-in diagnostics work unchanged.
- J13 has no spare signals, so the **real-time clock is reached through the RAM data port**
  (`$C0D3`) after an unlock sequence (§3).
- Target: **Laser 128EX**, including 2.3 and 3.6 MHz. The J13 pinout is identical on the New Laser 128,
  so the card should work there too.

## 2. Locked parts

| Ref | Part | Package | Notes |
|---|---|---|---|
| U1 | **ATF1508AS-7AX100** (or -10AU100) | TQFP-100, 0.5 mm | 5 V native, 128 MC, 80 I/O. The PLCC-84 parts went EOL in Oct 2025, so this is the only actively made 5 V option. Buy spares. |
| U2 | **AS6C8008-55ZIN** | TSOP-II-44 | 1M×8, 2.7–5.5 V, low standby current. One chip, so one chip enable. |
| U3 | **74HCT245** | DIP-20 (socketed) | Data buffer. DIR and /OE come from the CPLD, not straight from J13, so the timing can be tuned. |
| U4 | **DS1210** (or MXD1210) | DIP-8 | SRAM battery switch plus /CE write-protect at power-fail. Check the TOL pin setting against the measured Laser +5 V. |
| U5 | **DS3231** (SN) | SOIC-16W | I²C RTC with internal TCXO, ±2 ppm, no crystal. This avoids Renée's 7 s/day drift. |
| BT1 | CR2032 holder | — | Backs both the DS3231 VBAT and the DS1210 BAT. |
| J1 | 2×15 socket, 2.54 mm | custom footprint | Mates with the Laser's J13 pins. **U-numbering** (below). |
| J2 | JTAG header | per programmer | FT232H or ATDH1150USB. Pinout to be chosen. |
| J3 | Debug header | 0.1" | Spare CPLD I/O. Renée regretted leaving these off. |

**SRAM ordering warning (from Alliance datasheets):** the original **AS6C8008-55ZIN** runs on 2.7–5.5 V
and is the part we need. The newer **AS6C8008B** is **3.3 V only**: 2.7–3.6 V, absolute max 4.6 V.
On this 5 V card it would be destroyed. Pinout (TSOP-II-44, same for both): 1 A4, 2 A3, 3 A2, 4 A1, 5 A0,
6 CE#, 7–8 NC, 9 DQ0, 10 DQ1, 11 Vcc, 12 Vss, 13 DQ2, 14 DQ3, 15–16 NC, 17 WE#, 18 A19, 19 A18, 20 A17,
21 A16, 22 A15, 23 A14, 24 A13, 25 A12, 26 A11, 27 A10, 28 A9, 29–30 NC, 31 DQ4, 32 DQ5, 33 Vcc,
34 Vss, 35 DQ6, 36 DQ7, 37–38 NC, 39 A8, 40 CE2, 41 OE#, 42 A7, 43 A6, 44 A5.
CE2 (active high) is tied to the battery-backed VCCO rail. Operating current is 30 mA typ / 60 mA max at minimum
cycle time; standby (ISB1) is 6 µA typ / 50 µA max. Data retention works down to 1.5 V.

Optional insurance: series-resistor footprints (or 0 Ω links) on the strobes and data,
as the factory card had (R118–R133, plus the R138/L132 ferrite on D0 in rev C).

### J1 footprint (confirmed with Renée's kit socket and the original card photo)
- 2.54 mm pitch, 2.54 mm row spacing. The socket's solder pins measure 36.35 mm end to end.
- Pins 1–15 run down the row facing the **board interior**; pins 30 down to 16 run down the row at the
  **board edge**, so pin 30 sits beside pin 1. Pin 1 is the square pad, marked by the extra
  silkscreen line at that corner.
- The stock KiCad 2×15 footprint numbers odd/even across the rows, so it **must not** be used.
- Before ordering, print 1:1 and check it against the socket or the original card.

## 3. Clock integration: RTC port behind an unlock key

The CPLD gives the DS3231's SDA/SCL a tiny bit-bang port. Writing bit 0 = 1 pulls SDA low,
writing bit 1 = 1 pulls SCL low, and reading bit 0 returns SDA. A custom 6502 driver handles I²C in software.

**Change from the earlier plan:** that plan put the port in a fixed address window at the top of the 1 MB.
The Laser firmware's ProDOS RAM disk uses the whole expansion RAM, so a fixed window would
corrupt the top of the RAM disk. RAM-disk writes landing there would also toggle SDA/SCL at random,
which could write garbage into the clock. Instead the CPLD uses a **phantom-style unlock**, the same idea as Dallas's
DS1315 but implemented in the CPLD:

- The CPLD watches card data on every expansion-RAM **write**. A specific 8-byte key written
  in consecutive accesses (any address) switches the card into RTC mode. Any wrong byte resets the matcher.
  Random data matches with probability 2⁻⁶⁴.
- In RTC mode, accesses to `$C0D3` hit the RTC port and **never** the SRAM: /CE is held high,
  so RAM contents are untouched even though the address auto-increments.
- A write of a "lock" value, or any /RASB with no ECAS for longer than N cycles, drops back to RAM mode.
  Exact rules to be set in the CPLD spec.
- Cost: the CPLD needs card-side D0–7 as inputs (8 pins plus a small state machine). It fits easily in 128 MC.
- The driver saves the slinky address registers, sends the key, does the I²C transfer, locks, and
  restores the registers. RAM-disk contents are never disturbed.

## 4. Power and battery backup
- Normal: +5 V from J13 pins 1–2 feeds everything. The DS1210 VCCO feeds the SRAM.
- Laser off: the CR2032 feeds the DS3231 VBAT (timekeeping) and the DS1210 BAT. The DS1210 VCCO keeps the SRAM
  alive and its CEO holds the SRAM /CE high. The CPLD and '245 are unpowered; the SRAM sees their
  pins near 0 V, which is safe because /CE is high.
- To verify: DS1210 VCCO current capability vs. AS6C8008 active current, the DS1210 TOL setting,
  and the coin-cell life estimate (SRAM standby plus DS3231 timekeeping current).

## 5. 128EX timing rules for the CPLD (from Fig. 11-19)
- /E1MOE rises exactly at the CPUP0 fall, while /RASB, /ECAS and /RWR are still low.
- SRAM /WE = /RWR·/ECAS·/E1MOE, so the write ends on /E1MOE↑ (early) before data floats.
- SRAM /OE and the '245 enable are held until /E1MOE↑ (late).
- '245 DIR follows MEMRD (high = card → CPU).

## 6. Toolchain
- CPLD logic in portable Verilog, simulated with Icarus Verilog.
- Fitting: Quartus II (MAX7000S target) → POF2JED → `.jed`, or WinCUPL/`fit1508`. The
  ATF15xx open flow (prjbureau) is an alternative.
- Programming: ATDH1150USB or ATMISP7 with an FT232H breakout via SVF.
- KiCad files are generated as KiCad 7 format and open in KiCad 8 and 9.

## 7. Task list
1. KiCad: symbols (J1, DS1210, AS6C8008, ATF1508AS if not in the stock library) and footprints (J1).
2. KiCad schematic → ERC.
3. CPLD: Verilog plus testbench (1 MHz and 3.6 MHz waveforms, refresh, unlock/RTC mode).
4. CPLD pin assignment, back-annotated into the schematic.
5. Board outline, mounting holes and J1 position, **measured from an original card**.
6. PCB layout → DRC → gerbers, drill, BOM and position files.
7. Order boards; assemble the TQFP/TSOP (or have them factory placed).
8. 6502: RTC driver (unlock, I²C, ProDOS clock hook) and a set-clock utility.
9. 6502: RAM test (the built-in `C50AG` diagnostics should also pass).
