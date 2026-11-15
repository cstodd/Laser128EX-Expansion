# Hardware (KiCad)

`laser128-ramcard.kicad_sch` is **generated**. Edit `tools/gen_sch.py` (the pin→net table) and re-run it;
don't hand-edit the schematic, or the next regeneration will overwrite your changes. When the layout starts, the
schematic will be frozen and maintained in KiCad directly.

```sh
python3 tools/gen_lib.py      # hardware/lib/Laser128.kicad_sym + Laser128.pretty
python3 tools/gen_sch.py      # hardware/laser128-ramcard.kicad_sch
kicad-cli sch export netlist -o /tmp/l128.net hardware/laser128-ramcard.kicad_sch
python3 tools/check_netlist.py /tmp/l128.net
```

The files are KiCad 7 format and open in KiCad 8 and 9 (KiCad offers to upgrade them on save).
`laser128-ramcard.pdf` is a plot of the current schematic.

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
| 1 (GCLR) | /ECAS1 | in | | 21 | COLCLK | out |
| 2 (GCLK2) | /RASB | in | | 24 | MA18 | out |
| 43 (GCLK1) | /E1MOE | in | | 25 | /RAM_CE → DS1210 | out |
| 44 (OE1) | /ECAS2 | in | | 26 / 27 | /OE0, /OE1 | out |
| 4, 5 | /ECAS3, /ECAS4 | in | | 28 / 29 | /WE0, /WE1 | out |
| 6 | /RWR | in | | 31 | /BUF_OE ('245 G) | out |
| 8 | ERA8 | in | | 33 / 37 | MA8 (col), MA17 (row) | out |
| 39 | MEMRD | in | | 34 / 36 | SDA, SCL (open-drain) | i/o |
| 9 11 12 14 16 17 18 19 | XD0–XD7 | i/o | | 40 / 41 | DBG0, DBG1 (J3) | i/o |
| 20 | ROWCLK | out | | 7 13 32 38 | TDI TMS TCK TDO (J2) | jtag |

Power: VCC 3, 15, 23, 35; GND 10, 22, 30, 42.
