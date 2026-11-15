# Laser 128EX Battery-Backed SRAM Expansion + Clock — Design Notes

Status: **rev 0.1 complete: schematic, routed 2-layer board (DRC clean), Gerbers, CPLD logic + simulation. Next: fit the CPLD (Windows tools), order boards, write the 6502 RTC driver.**
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

## 2. Locked parts: architecture B (socketed, through-hole), chosen Nov 2026

The TQFP-100 ATF1508AS + 1 MB TSOP plan (architecture A) was dropped. The AS6C8008 is going EOL, both
parts are scarce at JLCPCB/LCSC, and a socketable CPLD still exists. See [`sourcing.md`](sourcing.md).

| Ref | Part | Package | Notes |
|---|---|---|---|
| U1 | **ATF1504AS-10JU44** | PLCC-44 in THT socket | 5 V, 64 MC, 32 I/O + 4 inputs. Active. Pin map in `hardware/README.md`. |
| U2 | **74AHCT574** | DIP-20 | Row register: ERA0–7 → MA9–16, clocked by ROWCLK (/RASB↓). AHCT for speed; not LS/HC. |
| U3 | **74AHCT574** | DIP-20 | Column register: ERA0–7 → MA0–7, clocked by COLCLK (first /ECASn↓). |
| U4 | **74HCT245** | DIP-20 | Data buffer. A = card bus XD, B = Laser D. DIR = MEMRD (as on the stock card); /OE from the CPLD. |
| U5, U6 | **AS6C4008-55PCN** | DIP-32 | 512K×8, 2.7–5.5 V. U5 = bank 0, U6 = bank 1. **Not** a 3.3 V-only part. |
| U7 | **MAX693ACPE+** | DIP-16 | Replaces the obsolete DS1210. VOUT = battery-switched SRAM rail (250 mA from VCC, 10 mA from the battery). CE IN→CE OUT gating ≤10 ns, held high below 4.40 V. /RESET (pin 15) → CPLD power-on clear. WDI/OSC pins open, PFI→GND. 0.04 µA from the battery. |
| U8 | **DS3231M+** (or DS3231SN#) | SOIC-16W | I²C RTC, TCXO, ±2 ppm. Pins 5–12 grounded. 0.84 µA typ from the battery. |
| BT1 | CR2032 | Keystone 103 holder | Feeds the DS1210 VBAT1 and the DS3231 VBAT. |
| J1 | 2×15 socket, 2.54 mm | custom U-numbered footprint | Mates with the Laser J13. |
| J2 | 2×5 IDC | 0.1" | JTAG, Altera/Atmel 10-pin layout (1 TCK, 2 GND, 3 TDO, 4 VCC, 5 TMS, 9 TDI, 10 GND). |
| J3 | 1×4 header | 0.1" | GND, DBG0 (CPLD 41), /RESET, +5V. |

Address mapping: SRAM A0–A7 = column ERA0–7 (U3), A8 = column ERA8 (CPLD), A9–A16 = row ERA0–7 (U2),
A17 = row ERA8 (CPLD), A18 = bank bit 0 (CPLD), chip select = bank bit 1 (CPLD drives OE0/OE1, WE0/WE1).
The mapping only has to be consistent, so any permutation of ERA bits works.

**Why '574 and not '573:** at 1 MHz /RASB goes high *before* /ECAS ends (Fig. 11-19a). A transparent
'573 would then pass the refresh row to the SRAM mid-read. Edge-triggered registers hold the row until
the next /RASB↓, which comes after the access is over.

**Why separate OE/WE per SRAM:** the DS1210 has a single CE path. Both SRAMs share CE#, so the CPLD
selects a chip by giving only that one OE# or WE#. The other chip is enabled but idle, with its outputs high-Z.

### J1 footprint (confirmed with Renée's kit socket and the original card photo)
- 2.54 mm pitch, 2.54 mm row spacing. The socket's solder pins measure 36.35 mm end to end.
- Pins 1–15 run down the row facing the **board interior**; pins 30 down to 16 run down the row at the
  **board edge**, so pin 30 sits beside pin 1. Pin 1 is the square pad, marked by the extra
  silkscreen line at that corner.
- The stock KiCad 2×15 footprint numbers odd/even across the rows, so it **must not** be used.
- Before ordering, print 1:1 and check it against the socket or the original card.

Battery life estimate with the Laser off: SRAM ~6 µA typ + DS3231 ~0.84 µA + DS1210 0.1 µA ≈ 7 µA, so a
220 mAh CR2032 lasts about 3 years of continuous off-time.

**Architecture under review:** see [`sourcing.md`](sourcing.md). The 1 MB SRAM is going EOL and a socketable
PLCC-44 option exists.

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
- Checked: the DS1210 VCCO supplies ≤80 mA, against one active AS6C4008 (≤~60 mA) plus one idle chip. TOL→VCCO.
  The coin cell lasts ~3 years with the Laser off (§2).

## 5. 128EX timing rules for the CPLD (from Fig. 11-19)
- Expansion-RAM cycles never run faster than **2.3 MHz**: at the 3.6 MHz setting the Laser slows to 2.3 MHz for
  these accesses (Tech Ref App. A). The simulation shows ~74 ns read margin with 55 ns SRAM.
- /E1MOE rises exactly at the CPUP0 fall, while /RASB, /ECAS and /RWR are still low.
- SRAM /WE = /RWR·/ECAS·/E1MOE, so the write ends on /E1MOE↑ (early) before data floats.
- SRAM /OE and the '245 enable are held until /E1MOE↑ (late).
- '245 DIR follows MEMRD (high = card → CPU).

## 6. Toolchain
- CPLD logic in portable Verilog, simulated with Icarus Verilog.
- Fitting: WinCUPL/`fit1504` (Microchip, free), or Quartus II (EPM7064S target) → POF2JED → `.jed`.
  The ATF15xx open flow (prjbureau/yosys) is an alternative.
- Programming: ATDH1150USB or ATMISP7 with an FT232H breakout via SVF.
- KiCad files are generated as KiCad 7 format and open in KiCad 8 and 9.

## 7. Task list
1. ~~KiCad symbols and footprints~~ (done: `hardware/lib`)
2. ~~KiCad schematic~~ (done: v0.1; netlist checks pass, `tools/check_netlist.py`)
3. CPLD: Verilog plus testbench (1 MHz and 3.6 MHz waveforms, refresh, unlock/RTC mode).
4. ~~Confirm the ATF1504AS PLCC-44 pinout~~ (done: matches the datasheet).
4b. ~~Replace the DS1210 with a MAX693A~~ (done). The DS3231M+ is accepted.
5. ~~Board outline / hole / J1 position~~ (measured; see mechanical.md). The 100×90 board is placed (hardware/placement-preview.png).
6. PCB layout → DRC → gerbers, drill, BOM and position files.
7. Order boards and parts; assemble (all THT except the DS3231 SOIC).
8. ~~6502: RTC driver and set-clock utility~~ (done: `software/`, emulator-tested; dual copy aux + main).
9. 6502: RAM test (the built-in `C50AG` diagnostics should also pass).
