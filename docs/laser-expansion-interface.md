# Laser 128 / 128EX Expansion RAM Interface (from the Technical Reference Manual)

Source: *LASER 128 Technical Reference Manual v2*. PDF page numbers are in brackets.

- §7 Expansion RAM, pp. 7-1 to 7-5 [142–146]
- §11.10 Expansion RAM control, pp. 11-46 to 11-49 [259–262]
- Gate-array pin tables D-26 (MMU) [327] and D-57/58/63 (UDC) [358/359/364]
- Schematics: D-94 New Laser 128 sheet 4 [395], D-102 128EX sheet 4 [403],
  D-103 128EX sheet 5 = stock RAM card [404]
- Stock card PCB D-106 (component side) [407] and D-107 [408]

Reference crops are in [`ref/`](ref/).

## 1. Software view (unchanged by our card)

| Address  | R/W | Name   | Function |
|----------|-----|--------|----------|
| `$C0D0`  | R/W | XAREGL | Address register, low byte |
| `$C0D1`  | R/W | XAREGM | Address register, mid byte |
| `$C0D2`  | R/W | XAREGH | Address register, high nibble (bits 0–3; bits 4–7 read as 1) |
| `$C0D3`  | R/W | XDREG  | Data register. Each access auto-increments the 20-bit address |
| `$C5xx`  | R/W | XRAME  | Any access enables the expansion RAM (disabled after power-up and Ctrl-Reset) |

- The registers live in the **UDC/MMU gate arrays on the motherboard**, not on the card.
- The "INT/EXT PORT 5" switch disables the whole interface.
- The firmware RAM-disk driver is in the slot-5 ROM space. ProDOS, DOS 3.3 and Pascal 1.3 recognise it.

## 2. Connector J13 (motherboard) ↔ J17 (card)

Both connectors are 2×15 headers on a 0.1" grid. The pinout is **identical** on the New Laser 128 (D-94) and the
128EX (D-102). The only difference is the data bus name: SD0–7 (128, system bus) vs RD0–7
(128EX, CPU bus). The card labels them D0–D7 below.

On the card's component-side silkscreen, pin 1 and pin 30 are at the top and pins 15 and 16 at the bottom.
That is DIP-style numbering: 1–15 run down one column and 16–30 run back up the other.

| Pin | Signal  | Dir (card) | | Pin | Signal  | Dir (card) |
|----:|---------|-----------|-|----:|---------|-----------|
| 1   | +5 V    | pwr | | 30 | GND     | pwr |
| 2   | +5 V    | pwr | | 29 | GND     | pwr |
| 3   | /RWR    | in  | | 28 | GND     | pwr |
| 4   | /ECAS4  | in  | | 27 | /RASB   | in  |
| 5   | /ECAS2  | in  | | 26 | /ECAS3  | in  |
| 6   | ERA0    | in  | | 25 | /ECAS1  | in  |
| 7   | ERA2    | in  | | 24 | ERA1    | in  |
| 8   | ERA4    | in  | | 23 | ERA3    | in  |
| 9   | ERA6    | in  | | 22 | ERA5    | in  |
| 10  | ERA8    | in  | | 21 | ERA7    | in  |
| 11  | D1      | i/o | | 20 | D0      | i/o |
| 12  | D3      | i/o | | 19 | D2      | i/o |
| 13  | D5      | i/o | | 18 | D4      | i/o |
| 14  | D7      | i/o | | 17 | D6      | i/o |
| 15  | MEMRD   | in  | | 16 | /E1MOE  | in  |

Signal meanings:

- **ERA0–ERA8**: multiplexed DRAM address from the UDC (row when AX is high, column when AX is low). AX itself is **not** on the connector.
- **/RASB**: row strobe common to all four banks. The row is valid on its falling edge.
- **/ECAS1–/ECAS4**: one column strobe per 256 KB bank, so 4 × 256 KB = 1 MB. At most one is low at a time.
- **/RWR**: DRAM write enable (low means write).
- **MEMRD**: direction for the card's '245. High means the card drives the CPU (read); low means the CPU writes to the card.
- **/E1MOE**: '245 output enable. Low while `$C0D3` is accessed with the expansion RAM enabled.
- **Refresh**: X1MREF makes the UDC put the refresh counter on ERA0–8 and pulse /RASB with **no** ECAS (a RAS-only refresh). An SRAM card must **ignore** these cycles.

### Stock card (VTech 702175 rev B/C, D-103)
- U45 and U46 are '244-type buffers (always enabled) with series resistors R118–R132 on the
  address and strobe lines.
- U47 is a 74HCT245: A side = card D0–7, B side = connector, G = /E1MOE, DIR = MEMRD.
- Rev C adds R138 in series with a ferrite L132 on D0, plus R133 from D7 to GND.
- U48–U79 are 32 × 41256 DRAMs in four rows of eight.
- Decoupling and bulk capacitors: C204–C242.

## 3. Timing (Fig. 11-19, p. 11-48/49 → [`ref/fig11-19-expansion-ram-timing.png`](ref/fig11-19-expansion-ram-timing.png))

- **1 MHz:** each CPU cycle has one RAS/CAS access. In the diagram a refresh cycle (RAS only, no CAS)
  sits between a CPU read and a CPU write. /E1MOE spans the cycle; read data must be valid
  before CPUP0 falls.
- **2.3 / 3.6 MHz (128EX only):** the MMU builds the strobes from a delay line (D60/D90/D120).
  There is still one access per cycle. /RASB falls early in CPUP0 high and /ECAS about mid-phase.
  **/RASB, /ECAS and /RWR then stay low past the falling edge of CPUP0**, but
  **/E1MOE rises exactly at the CPUP0 fall**. So the card's '245 lets go of the bus while the DRAM strobes are still
  active. Read data appears only late in CPUP0 high. Write data is valid shortly after /E1MOE falls
  (where MEMRD falls) and stays valid until the CPUP0 fall.
- That matches Renée Harke's finding. The SRAM write must **end on /E1MOE↑** (early, before the
  data floats, rather than on /RWR↑ or /ECAS↑), and /OE must be **held until /E1MOE↑** (late).

### What this means for the CPLD
1. Latch ERA0–8 as the **row** on the falling edge of /RASB.
2. On the falling edge of any /ECASn, latch ERA0–8 as the **column** and encode n into bank bits.
   SRAM address = {bank[1:0], row[8:0], col[8:0]} = 20 bits = 1 MB. The UDC's mapping from the linear
   address to row/col/bank doesn't matter as long as it's consistent, which it is.
3. Generate the SRAM chip enable from "any ECAS low". RAS-only refresh never touches the SRAM.
4. Read: /OE asserted from /ECAS↓ and **held until /E1MOE goes high**, so data stays valid
   through the '245 until the CPU samples it.
5. Write: /WE = /RWR low **and** /ECAS low **and** /E1MOE low. It terminates on whichever of those
   rises first, which in accelerated mode is /E1MOE at the CPUP0 fall, before data floats.
6. Keep /CE asserted for the whole ECAS-low period. The latched address stays stable until the next /RASB↓.

## 4. Mechanical (estimated from the D-106 scan; MUST be measured on a real card)

The scan was calibrated from the 0.1" DRAM and connector pad pitch (≈45 px per 2.54 mm at 400 dpi).

| Feature | Estimate (origin = top-left, component side) |
|---|---|
| Board outline | ≈ 190 × 92 mm (7.5" × 3.6") |
| Mounting hole, top-left | ≈ (9.4, 3.9) mm |
| Mounting hole, top-right | ≈ (185.0, 3.9) mm |
| J17 pin 1 | ≈ (184, 33) mm; second column +2.54 mm toward the right edge; pin 15 ≈ 35.6 mm below pin 1 |

Things to verify on hardware:
- The exact outline and holes. Renée's first clone had the left-hand holes slightly off.
- Which side of the card J17 is fitted on. If the card mounts component-side up over pins, the
  socket may be on the solder side, which mirrors the footprint.
- Height clearance above the card under the case.
