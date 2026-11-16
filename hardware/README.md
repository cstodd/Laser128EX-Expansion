# Hardware (KiCad)

`laser128-ramcard.kicad_sch` and the first `laser128-ramcard.kicad_pcb` were **generated** by the scripts in
`tools/` (KiCad 7). **The board is now maintained in KiCad 10** (trimmed to 100 × 90 mm, H2 removed, H3 moved
to (5, 86), footprints updated to KiCad 10 libraries, island vias added). The `tools/` scripts can't read
KiCad 10 files; they remain for history and for a full regenerate-and-reroute if ever needed.

Status (rev 0.1): **fully routed, 2 layers, 100 × 90 mm.** Re-checked from the KiCad 10 board and Gerbers: 282 pads
match the schematic netlist, J1 pins 15/16 are 23.000 mm above H1 with the J1 centreline through H1, H1 is 4.000 mm
from the right/bottom edges, 480 drill hits all land on copper on both layers. The fab origin (drill/place
origin, stored in the board file) is the bottom-left board corner: all Gerber, drill and placement
coordinates run 0..100 × 0..90 mm. DRC: 0 unconnected, 0 clearance errors
(2 starved-thermal warnings on GND pads that also have their own tracks). Every board pad's net matches the
schematic netlist. Fabrication outputs are in `fab/`; the ordering list is in `docs/ordering.md`.
Previews: `render-gerber-top.png` / `render-gerber-bottom.png` (rendered from the Gerbers with gerbonara),
`render-3D-top.png` / `render-3D-bottom.png` (KiCad 10).

Notes on this route:
- Signal tracks are 0.25 mm (0.187 mm in a few places). Power nets (+5V, VBB, VBAT, GND) are also routed at
  0.25 mm, which is ample for the card's <200 mA. GND also has pours on both layers with 174 stitching vias.
- J1's socket body goes on the **bottom** side (marked on the bottom silkscreen).

```sh
python3 tools/gen_lib.py      # hardware/lib/Laser128.kicad_sym + Laser128.pretty
python3 tools/gen_sch.py      # hardware/laser128-ramcard.kicad_sch
kicad-cli sch export netlist -o /tmp/l128.net hardware/laser128-ramcard.kicad_sch
python3 tools/check_netlist.py /tmp/l128.net             # ERC substitute
/usr/bin/python3 tools/gen_pcb.py /tmp/l128.net          # outline, holes, placement, pours (unrouted)
ROUTE_GND_SIGNAL=1 /usr/bin/python3 tools/route_pcb.py freerouting-2.5.0-executable.jar <java25>
/usr/bin/python3 tools/stitch_gnd.py 5                   # GND stitching vias
/usr/bin/python3 tools/tidy_silk.py                      # silkscreen clean-up + DRC
/usr/bin/python3 tools/export_fab.py                     # hardware/fab/
```
Freerouting 2.5.0 is `app.freerouting:freerouting:2.5.0` (executable jar) from Maven Central and needs Java 25.
`route_pcb.py` turns off its analytics, GUI and API server, and caps the run with `job_timeout`.
Routing lessons: GND has to be routed as a normal net (as a plane, ground pins get boxed in), and the
registers' D inputs must face J1.

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
| 1 (GCLR) | /ECAS1 | in | | 21 | COL_LE ('573 LE) | out |
| 2 (GCLK2) | /RASB | in | | 24 | MA18 | out |
| 43 (GCLK1) | /E1MOE | in | | 25 | /RAM_CE → MAX693A CE IN | out |
| 44 (OE1) | /ECAS2 | in | | 26 / 27 | /OE0, /OE1 | out |
| 4, 5 | /ECAS3, /ECAS4 | in | | 28 / 29 | /WE0, /WE1 | out |
| 6 | /RWR | in | | 31 | /BUF_OE ('245 G) | out |
| 8 | ERA8 | in | | 33 / 37 | MA8 (col), MA17 (row) | out |
| 39 | MEMRD | in | | 34 / 36 | SDA, SCL (open-drain) | i/o |
| 9 11 12 14 16 17 18 19 | XD0–XD7 | i/o | | 40 / 41 | /PWR_RST (MAX693A), DBG0 (J3) | in, i/o |
| 20 | ROWCLK | out | | 7 13 32 38 | TDI TMS TCK TDO (J2) | jtag |

Power: VCC 3, 15, 23, 35; GND 10, 22, 30, 42.
