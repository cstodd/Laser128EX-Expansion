# Building and verifying

Everything here runs on Linux (Ubuntu 24.04 in the cloud sessions). Tools are not in the repo; a fresh container
needs them reinstalled (none of this is needed just to order or assemble the card: the outputs are committed).

## Tools
| For | Tool | Notes |
|---|---|---|
| Board | **KiCad 10** (10.0.8 used) + `kicad-footprints`, `kicad-symbols` | From the KiCad PPA (`ppa:kicad/kicad-10.0-releases`; hosts `ppa.launchpadcontent.net` and `keyserver.ubuntu.com` must be allowed). Gives `kicad-cli` and the `pcbnew` Python API (`/usr/bin/python3`) |
| Autorouting (rarely) | Freerouting 2.5.0 executable jar (Maven Central `app.freerouting:freerouting:2.5.0`) + **Java 25** | Only used to make the first routes; the current board was finished by hand |
| Gerber previews | `gerbonara` (pip), Chromium/Playwright (preinstalled in cloud sessions) | `pip install --ignore-installed blinker gerbonara` if pip refuses over Debian's blinker |
| CPLD | `yosys` (0.33), `iverilog`/`vvp`, `wine` (32-bit), `python3` | |
| CPLD fitter | `github.com/hoglet67/atf15xx_yosys` + Atmel's `fit1504.exe`, `aprim.lib`, `atmel.std` | Vendor files come from Microchip's `ProChip5.0.1.zip` (`innoextract ProChip5_setup.exe`); copy into `atf15xx_yosys/vendor/` (sha1sums in its README) |
| Fuse-level check | `github.com/whitequark/prjbureau` (`database.json`) | Optional but recommended |
| 6502 software | `cc65` (`ca65`/`ld65`), Python 3 with `py65` | |
| Disk image check (optional) | AppleCommander 1.10.1 jar + Java | See `software/rev01/README.md` |

## Board (`hardware/rev02`)
- Open `hardware/rev02/laser128-ramcard.kicad_pro` in KiCad 10. It is the source of truth (finished by hand).
- DRC + parity: `kicad-cli pcb drc --refill-zones --schematic-parity --format json -o drc.json hardware/rev02/laser128-ramcard.kicad_pcb`
  — expect 0 unconnected, no errors (only "footprint differs from library" notices), parity only H1/H3.
- Fab outputs: `/usr/bin/python3 tools/export_fab.py rev02` → `hardware/rev02/fab/` (Gerbers, merged drill,
  BOM, KiCad placement CSV, zip). Everything is on the drill/place origin (bottom-left corner, 0..100 × 0..90).
- Renders: `kicad-cli pcb render --side top|bottom` for 3D; Gerber previews with gerbonara `LayerStack.open(zip).to_pretty_svg()`
  then a Chromium screenshot.
- Schematic PDF: `kicad-cli sch export pdf`.
- Revert `.kicad_prl` changes before committing.
- History only: `tools/rev02_sch.py` / `tools/rev02_pcb.py` (`prep`, `move`, `rip`, `route`, `strip`) produced the
  rev 0.2 edits from rev 0.1 but no longer reproduce the hand-finished board.

## CPLD (`cpld/rev02`)
```sh
cd cpld/rev02/fit
ATF15XX_YOSYS=/path/to/atf15xx_yosys PRJBUREAU=/path/to/prjbureau ./build.sh
```
Runs Yosys → fitter (pins forced from `pins.txt`, JTAG on) → testbench on the fitter's equations (`fit2v.py`) →
testbench on the decoded `.jed` (`jed2v.py`, prjbureau) and only then copies `laser128_ramcard.jed/.fit` in.
Quick RTL-only run: `iverilog -g2012 -o tb laser128_ramcard.v tb_laser128_ramcard.v && vvp -n tb` (add `+quick`
to skip the ~45 s exhaustive key test). Expect `PASS`, 40/64 macrocells, a fast-cycle read margin of ~2 ns.
Timing parameters (all measured) are at the top of `tb_laser128_ramcard.v`; try SRAM speed with
`-Ptb.T_AA=45 -Ptb.T_ACE=45`.
Programming: ATDH1150USB + ATMISP (Windows) with the `.jed`, or OpenOCD + FT232H with an SVF from ATMISP
(`cpld/rev02/README.md`).

## Software (`software/rev02`)
```sh
python3 software/rev02/build.py      # assembles, tokenises the BASIC, writes dist/ and LASERCLOCK2.po
python3 software/rev02/test_drv.py   # 65C02 emulation with CPLD port + DS3234 model: expect ALL PASS
```
`build.py` asserts the clock driver is ≤ 125 bytes. BASIC sources are plain Applesoft in `software/rev02/basic/`
(uppercase keywords, ≤ 40-column text, no keywords hidden in variable names). Shared helpers come from
`software/rev01/` (`defs.inc`, `mkdisk.py`, `test/harness.py`), so keep that directory.
