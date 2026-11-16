# Hardware (KiCad) — rev 0.2

Rev 0.2 replaces rev 0.1's DS3231M (I²C, bit-banged through the CPLD) with a **DS3234SN#** (SPI) so the
ProDOS clock driver fits entirely in ProDOS's 125-byte clock slot and never disables interrupts
(`software/rev02`, `cpld/rev02`, `docs/design-notes.md` §10). Everything else (RAM, CPLD, J1, outline,
holes) is unchanged from rev 0.1 (`hardware/rev01`).

Status (rev 0.2): **fully routed, 2 layers, 100 × 90 mm, KiCad 10.** DRC: 0 unconnected, 0 clearance /
silkscreen errors (only "footprint differs from library" notices for footprints carried over from the
KiCad 7 generation). Schematic parity: every pad's net and every footprint/value/field matches; H1/H3 are
board-only mounting holes. J1/H1 geometry re-checked: H1 4.000 mm from the right and bottom edges, J1 pins
15/16 23.000 mm above H1 with J1's centreline through H1. The fab origin (drill/place origin) is the
bottom-left board corner; Gerbers, drill and placement all use it (the 357 drill hits were checked against
the board's pads and vias). Fabrication outputs are in `fab/`. Previews: `render-gerber-top.png` /
`render-gerber-bottom.png` (from the Gerbers with gerbonara), `render-3D-top.png` / `render-3D-bottom.png`
(KiCad 10).

What changed from rev 0.1:
- **U8 DS3234SN#** (SOIC-20W, 300 mil) right of the CPLD, rotated 90°, so CS/SCLK/DIN/DOUT are short.
  DIN (17) and DOUT (19) are joined (3-wire SPI) as `RTC_SDIO`; SCLK on both 18 and 20 (bonded inside);
  N.C. pins 2 and 7–14 and GND 15 to ground (datasheet); VBAT (16) from BT1; 32kHz, INT/SQW, RST open.
  C9 (100 nF) decouples it.
- **R1 1k** CPLD `RTC_DIO` (pin 39) ↔ `RTC_SDIO` (series: limits current if the CPLD and the DS3234 ever drive
  at once). **R2 47k** `RTC_SDIO` → GND: the pull-down the driver relies on to clock in read address 00h.
  Both use the vertical DIN0207 footprint (2.54 mm pitch) to fit beside the CPLD.
- R3–R5 (JTAG pull-ups) and C3 (CPLD decoupling) moved to make room; the strip in front of J1 is kept
  clear for its fan-out.
- CPLD pins 34 / 36 / 39 are now `RTC_CS_n` / `RTC_SCLK` / `RTC_DIO` (were SDA / SCL / MEMRD; MEMRD was
  unused by the logic).
- Board text reads "rev 0.2".
- **Hardware check still open:** the CPLD generates SCLK from /E1MOE while /RWR is high, so /RWR must be
  valid before /E1MOE falls (J13 pin 3 vs pin 16 on a scope). See `cpld/rev02/README.md`.

How it was made: `tools/rev02_sch.py` (schematic edit), `tools/rev02_pcb.py` (`prep`: DS3234 footprint and
rev 0.2 nets with stale copper removed; `move`: the placement above; `rip` / `route`: protected incremental
Freerouting passes), then the last two CPLD↔J1 nets (ECAS3_n, ERA8), GND island bridging (U8's ground pins,
U1-10) and moving ECAS3_n / E1MOE_n under U8 on B.Cu were done by hand in KiCad 10, so the scripts no longer
reproduce the board exactly; the `.kicad_pcb` is the source of truth. Fab outputs:
`/usr/bin/python3 tools/export_fab.py rev02`.

Notes on this route:
- Signal tracks 0.2–0.25 mm; GND pours on both layers, stitched with vias.
- J1's socket body goes on the **bottom** side (marked on the bottom silkscreen).
- `laser128-ramcard.pdf` is a plot of the rev 0.2 schematic.

## Project libraries
- `Laser128:Laser128_J1`: J13 mate symbol (pins drawn like the physical socket).
- `Laser128:Laser128_J1_Socket_2x15_P2.54mm_Unumbered`: pins 1–15 down the interior-side row,
  30–16 down the board-edge row. **Not** the stock odd/even 2×15. Print it 1:1 and check against a real socket.
- `Laser128:ATF1504AS-xJx44`: PLCC-44, derived from the stock TQFP-44 ATF1502/1504 symbol
  (PLCC pin = TQFP pin + 6, mod 44). **Verified** against the Atmel-0950 ATF1504AS(L) datasheet tables 16.1/16.2:
  all 32 I/O pins and the dedicated, JTAG and power pins match.

## CPLD pin assignment (ATF1504AS-10JU44, PLCC-44)

| Pin | Signal | Dir | | Pin | Signal | Dir |
|---|---|---|---|---|---|---|
| 1 (GCLR) | /ECAS1 | in | | 21 | COL_LE ('573 LE) | out |
| 2 (GCLK2) | /RASB | in | | 24 | MA18 | out |
| 43 (GCLK1) | /E1MOE | in | | 25 | /RAM_CE → MAX693A CE IN | out |
| 44 (OE1) | /ECAS2 | in | | 26 / 27 | /OE0, /OE1 | out |
| 4, 5 | /ECAS3, /ECAS4 | in | | 28 / 29 | /WE0, /WE1 | out |
| 6 | /RWR | in | | 31 | /BUF_OE ('245 G) | out |
| 8 | ERA8 | in | | 33 / 37 | MA8 (col), MA17 (row) | out |
| 39 | RTC_DIO (via R1 to DS3234 DIN/DOUT) | i/o | | 34 / 36 | RTC_CS_n, RTC_SCLK | out |
| 9 11 12 14 16 17 18 19 | XD0–XD7 | i/o | | 40 / 41 | /PWR_RST (MAX693A), DBG0 (J3) | in, i/o |
| 20 | ROWCLK | out | | 7 13 32 38 | TDI TMS TCK TDO (J2) | jtag |

Power: VCC 3, 15, 23, 35; GND 10, 22, 30, 42.
