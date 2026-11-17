# Apple //c memory expansion connector compared with the Laser's J13

Background for the parked //c variant ([design-notes §11](design-notes.md#11-future-idea-parked-a-version-for-the-apple-c-and-maybe-c)).

Sources:
- *The Apple IIc Technical Reference Manual*, 2nd ed. (covers the original, UniDisk 3.5 and memory expansion //c).
  PDF from the Asimov mirror (`mirrors.apple2.org.za/ftp.apple.asimov.net/documentation/hardware/machines/`,
  "Apple IIc Technical Reference Manual (alt).pdf").
  - p. 291 [PDF 319], Fig. 11-43: connector pinout table → [`ref/iic-fig11-43-pinout-table.png`](ref/iic-fig11-43-pinout-table.png)
  - p. 296 [PDF 324], Fig. 11-44e: schematic 050-0180-A "Logic, //c w/Mem Exp", sheet 5, J13 →
    [`ref/iic-j13-memory-expansion-schematic.png`](ref/iic-j13-memory-expansion-schematic.png)
  - p. 2–3 and Ch. 6–7: memory expansion //c = ROM version `$03`; the card is I/O port 4 (`$C400` entry, `$C0Cx`),
    and the mouse moves to port 7.
- The Laser side is from [laser-expansion-interface.md](laser-expansion-interface.md).

Both motherboards call this header **J13**.

## 1. //c J13 pinout (2×17, 0.1")

The Fig. 11-43 table misprints pin 23 as a second "A15". The schematic shows **pin 23 = A14** and pin 24 = A15.
**A2 and A3 are not on the connector**; the table and the schematic agree on that.

Numbering alternates across the rows (1 opposite 2, 3 opposite 4 …). That differs from the Laser J13's DIP-style
numbering (1–15 down one column, 16–30 back up the other).

| Pin | Signal | | Pin | Signal |
|----:|--------|-|----:|--------|
| 1  | D0     | | 2  | D1     |
| 3  | D2     | | 4  | D3     |
| 5  | D4     | | 6  | D5     |
| 7  | D6     | | 8  | D7     |
| 9  | GND    | | 10 | GND    |
| 11 | A0     | | 12 | A1     |
| 13 | A4     | | 14 | A5     |
| 15 | A6     | | 16 | A7     |
| 17 | A8     | | 18 | A9     |
| 19 | A10    | | 20 | A11    |
| 21 | A12    | | 22 | A13    |
| 23 | A14    | | 24 | A15    |
| 25 | /RESET | | 26 | R/W    |
| 27 | +5 V   | | 28 | +5 V   |
| 29 | PH0    | | 30 | GND    |
| 31 | 7M     | | 32 | GND    |
| 33 | Q3     | | 34 | +5 V   |

Totals: 8 data, 14 address, R/W, /RESET, 3 clocks (PH0, 7M, Q3), 3 × +5 V, 4 × GND.

## 2. Side by side

| | Laser 128 / 128EX J13 | Apple //c (memory expansion) J13 |
|---|---|---|
| Size | 2×15 = 30 pins | 2×17 = 34 pins |
| Kind of interface | **DRAM port**: the gate array is the memory controller | **CPU bus port**: the card is the memory controller |
| Data | D0–D7 (system/CPU bus) through the card's '245 | D0–D7 (CPU bus), no direction or enable signals |
| Address | ERA0–ERA8, multiplexed row/column DRAM address | A0, A1, A4–A15 CPU address (no A2/A3) |
| Strobes / select | /RASB, /ECAS1–4, /E1MOE, MEMRD | **None.** The card decodes `$C0Cx` itself from A4–A15 |
| Read/write | /RWR (DRAM write enable, timed) | R/W (6502 level, valid for the whole cycle) |
| Clocks | None | PH0, Q3, 7M |
| Reset | None (registers on the motherboard) | /RESET |
| Address registers | On the motherboard (UDC/MMU), `$C0D0–$C0D3`, slot 5 | On the card, `$C0C0–$C0C3`, slot 4 |
| Refresh | Motherboard: RAS-only cycles the card must ignore | Card's own job (CAS-before-RAS DRAMs on Apple's card) |
| Firmware | Slot-5 ROM on the motherboard | `$C400` ROM on the motherboard (ROM `$03`) |
| Power | 2 × +5 V, 3 × GND | 3 × +5 V, 4 × GND |

The only things in common are D0–D7, +5 V and GND. The software model is the same Slinky-style
"address low/mid/high + auto-incrementing data" register set, apart from the slot (5 vs 4).

## 3. What the //c card has to do (and the Laser card doesn't)

1. **Decode its own registers.** Select = A15–A4 = `$C0C` while PH0 is high. A1:A0 choose the register. With
   no A2/A3, a minimal decode also answers at `$C0C4–$C0CF` (three mirrors). That's probably intended, but check
   whether any //c firmware touches those addresses.
2. **Hold the address register and counter.** Low/mid/high bytes, readable and writable, auto-incrementing on every
   access to the data register. Apple's card is described as 1 MB in 256 KB steps, so 20 bits are used. How the
   unused high bits read back still needs checking against the *Apple IIc Memory Expansion Card Reference*
   (not found yet).
3. **Drive D0–D7 on reads** only during PH0 high, for a select with R/W high, and release it at the PH0 fall. Write
   data is latched on the PH0 fall with R/W low.
4. **Refresh**: DRAM cards refresh themselves using 7M/Q3. An SRAM card needs none.
5. **/RESET**: whether it clears the address register is not documented on these pages. Check the card reference.

## 4. What this means for a //c version of our card

- **The CPLD logic is replaced, not ported.** Row/column latches, bank encoding and refresh filtering go. In their
  place: the `$C0Cx` decode, three address registers with read-back, a 20-bit incrementer and the data-bus
  drive. That's a bigger design but a simpler timing problem: everything follows PH0 and R/W.
- **The SRAM side gets simpler.** The SRAM address comes straight from the counter; /CE and /OE follow the select
  and PH0, and /WE is select·/R/W·PH0, ending at the PH0 fall.
- **Pin budget:** 8 data + 14 address + R/W + /RESET + PH0 (+ Q3/7M if useful) ≈ 25–27 CPLD inputs and I/Os,
  plus 20 SRAM address lines, about the same as the Laser design's 25 header signals. The CPLD can drive D0–D7
  directly or through a '245 whose direction and enable it generates.
- **Timing to scope:** data hold after the PH0 fall on reads, and write data valid before it. On the //c+
  (4 MHz accelerator), Apple's card needs a different PAL ([wiki.apple2.org RAM Cards](http://wiki.apple2.org/index.php?title=RAM_Cards)),
  so repeat the 128EX lesson there: don't trust the 1 MHz timing.
- **Mechanical:** a different connector (2×17), different pin numbering and a different board outline.
  Fig. 11-43's outline shows a break at the pin 17/18 row. It may be a key or polarisation feature; check on a
  real board.
