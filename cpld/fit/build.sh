#!/bin/bash
# Fit cpld/laser128_ramcard.v for the ATF1504AS (PLCC-44) -> laser128_ramcard.jed
# Needs: yosys, wine (with 32-bit support), and a checkout of
# https://github.com/hoglet67/atf15xx_yosys whose vendor/ holds Atmel's fit1504.exe,
# aprim.lib and atmel.std (from Microchip's ProChip5.0.1.zip; see README.md).
#   ATF15XX_YOSYS=/path/to/atf15xx_yosys ./build.sh
set -e
: "${ATF15XX_YOSYS:?set ATF15XX_YOSYS to your atf15xx_yosys checkout}"
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=$HERE/out
mkdir -p "$OUT" && cd "$OUT"
# the atf15xx scripts read <name>.v, and take pin assignments from //PIN: comments in it
cat "$HERE/../laser128_ramcard.v" "$HERE/pins.txt" > laser128_ramcard.v
"$ATF15XX_YOSYS/run_yosys.sh" laser128_ramcard > yosys.log 2>&1
# -preassign keep: pins must land exactly where the PCB has them (fit fails otherwise)
# JTAG stays on (default); power-down pins and power_reset stay off (defaults)
# speed grade only affects the timing report: -10 and -7 give identical fuses
"$ATF15XX_YOSYS/run_fitter.sh" -d ATF1504AS -p PLCC44 -s 10 laser128_ramcard \
    -preassign keep -strategy JTAG on -strategy pd1 off -strategy pd2 off \
    -strategy TDI_pullup on -strategy TMS_pullup on -strategy Verilog_sim verilog

# post-fit check: rebuild Verilog from the fitter's equations (what is in the .jed) and run the
# same testbench as the RTL
python3 "$HERE/fit2v.py" laser128_ramcard.fit > fitted.v
iverilog -g2012 -o tb_fitted fitted.v "$HERE/../tb_laser128_ramcard.v"
vvp -n tb_fitted | tee tb_fitted.log
grep -q '^PASS' tb_fitted.log
# fuse-level check (optional): decode the .jed itself with Project Bureau's fuse database
# (github.com/whitequark/prjbureau) and run the same testbench on that
if [ -n "$PRJBUREAU" ]; then
    python3 "$HERE/jed2v.py" "$PRJBUREAU" laser128_ramcard.jed "$HERE/pins.txt" > decoded.v 2> decoded.log
    cat decoded.log
    iverilog -g2012 -o tb_decoded decoded.v "$HERE/../tb_laser128_ramcard.v"
    vvp -n tb_decoded | tee tb_decoded.log
    grep -q '^PASS' tb_decoded.log
else
    echo "PRJBUREAU not set: skipping the fuse-level (.jed) check"
fi
cp laser128_ramcard.jed laser128_ramcard.fit "$HERE/"
echo "OK: $HERE/laser128_ramcard.jed"
