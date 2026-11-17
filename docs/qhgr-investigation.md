# The Laser 128 "QHGR" / Quad Hi-Res rumor: what the ROMs show

Nov 2026. This is a ROM-only investigation of 12 system ROMs and one video ROM. It is not a definitive answer.
The scripts are in `tools/rom-analysis/`. Run them with `python3 -I` on each ROM file. The ROM images are not in
this repo.

## The claim
The claim is that some Laser 128 had a Laser-only graphics mode, called "QHGR" or "QHR". It is usually described
as **560×384**: two DHGR pages shown together, interlaced or stacked. Some versions instead describe a doubling
of the DHGR horizontal resolution. Wikipedia says the mode existed on the **first** Laser 128 and was dropped later.
I couldn't reach Wikipedia, Usenet or archive.org from the analysis environment, so those sources are still unchecked.

## ROMs examined
| File | Banner / origin |
|---|---|
| `laser128-860801`, `laser128-860915` | No version banner. *"COPYRIGHT 1986 LANGUAGE ARTS, INC. & VIDEO TECHNOLOGY"*: VTech's own in-house firmware, dated 1 Aug and 15 Sep 1986 |
| `Laser128_2.9`, `v3.0`, `v3.3`, `3.5`, `v4.1`, `4.2`, `4.3`, `v4.5`, `6.0` | Central Point Software, "LASER 128 ROM Version n.n" |
| `Laser128_EX2_6.1` | "LASER 128EX/2 ROM Version 6.1" (1985-88) |
| `laser128-video-VT27-0706-0` | 8 KB video ROM |

The 32 KB ROMs have two 16 KB banks. File offset + `$C000` gives the address in bank 0. Offset − `$4000` + `$C000`
gives the address in bank 1.

## Finding 1: the 0706 video ROM holds a pixel generator, and it has only the standard modes
- `$0000–$0FFF` holds two 2 KB character sets. They differ in about 22 glyphs.
- **`$1000–$1FFF` is not a font. It is the gate array's graphics lookup table.** Each video byte indexes
  8 entries (`addr = $1000 | A11 | data<<3 | slot`), and each entry is the next 7 dots to shift out. All 16
  sub-tables decode to standard Apple modes:
  - **LGR**: nibble to 4-dot repeating color pattern. There are four phases, covering the low/high nibble and
    the first/second 7 dots.
  - **HGR**: each of 7 bits doubled to 14 dots. Bit 7 shifts by half a dot, and one slot carries in the
    previous byte's last dot (the standard hi-res "fill").
  - **DLGR** (`A11`=1): the same patterns rotated, for the aux-byte color phase.
  - **DHGR / 80-col graphics** (`A11`=1): identity on 7 bits, i.e. 1 bit = 1 dot at 560.
- No sub-table is left unexplained, and every address line is in use. **This ROM has no extra pixel format**
  and no way to put more than 560 dots on a line. That rules out the "DHGR × 2 horizontally" form of the rumor
  on this hardware.
- It does **not** rule out a 560×384 *interlaced* mode. That needs field-alternating timing and a page-select
  bit, not a new pixel table.

**Important:** MAME's `laser128o` ("original hardware") set lists a different, **undumped** video ROM,
`vt27-0430-0` (marked "need to dump actual part"). The 0706 part is used for the 128, 128EX and EX/2. If an
early-only mode existed, its table would be in **0430**, which no one seems to have read.

## Finding 2: the earliest firmware resets the early-only video switches at `$C021–$C026`
At `$F954` (bank 0, a video-init subroutine; it is called from the code just after it, at `$F985`), the early ROMs run:
```
F954  STZ $C021
F957  LDA #$F0
F959  STA $C022
F95C  STZ $C023
F95F  STZ $C024
F962  STZ $C026
F965  STZ $C051   ; TEXT
F968  STZ $C054   ; PAGE1
F96B  STZ $C056   ; LORES
F96E  STZ $C05F   ; AN3 high (DHGR off)
```
| ROM | `$C021–$C026` init |
|---|---|
| 860801, 860915 (VTech), 2.9, 3.0 | **present** |
| 3.3, 3.5, 4.1, 4.2, 4.3, 4.5, 6.0, EX/2 6.1 | **removed**. The routine starts at `STZ $C051` |

No ROM reads or writes `$C02x` anywhere else. On an Apple IIe or IIc these addresses do nothing useful:
`$C020` is cassette output, and on the IIc `$C028` is the ROM bank switch. So **the early Laser hardware had some
register block at `$C021–$C026` that needed a known state at every reset, next to the video switches**. Later
boards no longer did.

### These writes match the Applefritter description of the early switches
The [Applefritter thread](https://www.applefritter.com/content/quick-delve-laser-128-ex2) describes these
early-hardware soft switches, based on others' experiments (not from the ROMs):

> $C023 controlling the border color for graphics modes … $C024..$C027 control the rest of the unique behavior.
> … $C027 seems to enable the stacked mode, $C026 disables it. $C025 affects interlacing (?) and $C024 again
> disables it.

The early reset code matches it:

| Address | Thread | Early reset code |
|---|---|---|
| `$C021` | (not described) | writes `$00` |
| `$C022` | (not described) | writes `$F0`, likely a text foreground/background color pair (white on black) |
| `$C023` | graphics border color | writes `$00`, a black border |
| `$C024` | interlace **off** | touched, so interlace is off |
| `$C025` | interlace **on** | **never touched by any ROM** |
| `$C026` | stacked mode **off** | touched, so stacked mode is off |
| `$C027` | stacked mode **on** | **never touched by any ROM** |

Reset puts every special feature in its off or default state and never turns one on. `$C024/$C025` and
`$C026/$C027` follow the Apple convention of even address = off, odd address = on. Two independent
sources, one from hands-on poking and one from the firmware, agree this closely, so **the early Laser 128
almost certainly had interlace and stacked-page (384-line) video modes, plus border and probably text
color registers**. The firmware never used them, and they were removed from the hardware by the time of ROM 3.3.
`$C021` is still unknown. Possibilities include color/monochrome, a mode select, or something not related to video.

"Stacked mode" with interlace is presumably the 560×384 "Quad Hi-Res": DHGR page 1 on one field and page 2
on the other. This needs no new pixel table, which fits Finding 1. A version of the mode with more horizontal
resolution has no support anywhere.

## Ruled out
- **No firmware support in any version.** Video soft-switch use (`$C050–$C05F`) is the same in all 12 ROMs.
  `$C05E` (DHGR on) is never written, and no ROM has text naming a graphics mode. Any QHGR mode would have been
  driven by application software, not the ROM.
- **EX/2 `$C078`** is an RTC (index/data port, 4-bit registers, register `$D` HOLD=bit 0 and BUSY=bit 1, the
  OKI MSM6242 layout). It backs the "Date and Time" item in the setup menu and is not video.
- `$C074` (3.5 and later) is the speed control. `$C0C4/$C0C6` (3.0 and later) are slot-4 (mouse) I/O.

## How to settle it
1. **Dump a `vt27-0430-0` video ROM** from an early Laser 128 board. Run `videorom.py` on it and look for
   sub-tables that don't match LGR, HGR, DLGR or DHGR, or for a changed address layout.
2. On an early board (one that ships with ROM 2.9 or 3.0, or a VTech 8608xx ROM), load different DHGR images
   into page 1 and page 2. From the monitor, enter DHGR: `C050:0`, `C052:0`, `C057:0`, `C00D:0`, `C05E:0`
   (80COL on, DHGR on). Then try `C027:0` (stacked on), `C025:0` (interlace on), and `C023:` followed by a
   color value. Undo them with `C026:0` and `C024:0`. Check that
   a later board (ROM 3.3 or later) ignores the same writes.
3. Read the Technical Reference Manual's I/O map for `$C020–$C02F`. Check it against the early schematics, if
   there are any, to see which chip decodes those addresses.
