# Laser 128 / 128EX Battery-Backed SRAM Expansion + Clock — Design Notes

Status: **architecture draft**. Everything marked *(verify)* needs to be checked
against the Laser 128 Technical Reference Manual or a real card before layout.

## 1. How the stock Laser expansion works

Source: Renée Harke's posts (2019-12-31 and 2021-01-05, reneeharke.com).

- The stock card (VTech 702175 rev B/C) is **only DRAM**: 32 × 41256
  (256K×1) for 1 MB, in four 256 KB banks. The 128EX shipped with 256 KB populated.
- The Laser motherboard has the slinky-style logic: the address
  registers, auto-increment, and the data port. It drives the card with
  **multiplexed DRAM signals**: RA0–RA8, RAS/CAS strobes, write enable, and
  the data bus through a '245 whose enable comes from the motherboard.
- Software sees it like an Apple IIc memory expansion card. ProDOS 8 builds a
  RAM disk from it, and the built-in diagnostics test it with `C50AG` from the
  monitor (Renée used this command; the slot it implies is *(verify)*).
- Rev C adds a series resistor plus ferrite on one data line for RF/ringing.
  Values aren't in the manual's BOM.

Consequence: our card never decodes $C0xx registers itself. It emulates
1 MB of DRAM, so it works with the existing Laser firmware and every
slinky-aware program with no changes.

## 2. Proposed architecture

```
 Laser expansion connector
   RA0-RA8, /RAS*, /CAS*, R/W, D0-D7, buffer enable
        │
        ▼
 ┌──────────────┐  A0-A19   ┌─────────────────┐
 │  CPLD        │──────────▶│ 1 MB low-power  │
 │ ATF1504AS/   │  /CE,/OE, │ SRAM (5 V)      │◀── VCCO (battery-backed)
 │ ATF1508AS 5V │  /WE      └─────────────────┘
 │              │──A0,A2,/CE,/OE,/WE──▶ DS1315 phantom clock ── 32.768 kHz xtal
 └──────────────┘                         │  VBAT (CR2032)
        │ D0-D7                            └─ VCCO powers SRAM, CEO gates SRAM /CE
        ▼
      74HCT245 (or the CPLD directly, if the bus timing allows)
```

### CPLD
- **ATF1504AS (64 macrocells) or ATF1508AS (128 MC)**, Microchip, 5 V native,
  still in production, PLCC-44 (socketable) or TQFP-44.
  Being a native 5 V part avoids the 3.3 V level shifting Renée needed with her first SRAM.
- Job: latch the row address on /RAS↓ and the column on /CAS↓, decode which
  bank's /RAS (or /CAS) fired, and drive A0–A19 plus /CE /OE /WE.
- 128EX accelerated mode (Renée's finding): **end writes early, end reads late**.
  The Laser turns off the '245 enable and the RAM strobes at different times.
- Toolchain: WinCUPL, or the open prjbureau / yosys flow for ATF15xx. Program over JTAG
  (ATDH1150USB, or an FT232H/OpenOCD-style cable using SVF).

### SRAM
- Low-power 5 V-capable CMOS SRAM with µA-level standby current, for example
  Alliance **AS6C8008** (1M×8, TSOP-44) or **2 × AS6C4008** (512K×8, DIP-32 / SOP-32).
  55 ns is far faster than the Laser needs.

### Real-time clock: how it integrates
The Laser has no free internal slot for a ThunderClock-style card, so the clock
has to sit *behind the memory interface*. That's what A2Heaven's RamExpress II+ does,
and the Applied Engineering **RamExpress + DClock** pair before it.

- A Dallas "phantom" clock (DS1215, today **DS1315**) sits on the RAM's chip-enable
  path and normally lets every access through to the RAM.
- A fixed 64-bit pattern, written one bit per access through the RAM interface, makes
  the next 64 accesses read or write the clock registers instead of RAM.
  After that it drops back to being RAM.
- Because the CPLD rebuilds the full linear address, it can feed the DS1315's
  A0 (data-in) and A2 (read/write select) from address bits, exactly as a
  DClock-equivalent wiring would require *(exact bit mapping: verify against the
  DClock driver / A2Heaven RamExpress II+)*.
- Software: the **AE DClock ProDOS driver** (Renée confirmed it works on the Laser).
  A ProDOS clock-driver patch or a small boot-time loader sets the date.
- Bonus: the DS1315 is also the **battery switch**. Its VCCO output powers the
  SRAM from the CR2032 when the Laser is off, and its CEO holds the SRAM
  deselected below the power-fail threshold. The result is a RAM disk that survives a power cycle.

Known issue to design around: Renée's clock lost about 7 s/day, which she suspected
came from a crystal ESR/load-capacitance mismatch. Use a crystal that meets the DS1315's
specified load (6 pF *(verify)*), keep the crystal traces short with a ground guard, and
consider a through-hole footprint so different crystals can be tried.

## 3. Open items (blocking schematic/PCB)

1. **Connector pinout, connector type, and board outline/mount holes** from the Tech Ref
   Manual (expansion card section and schematic).
2. Which strobes select the bank: four /RAS lines or four /CAS lines? And the
   RAS/CAS/'245-enable timing at 1 MHz and at 3.6 MHz.
3. DClock wiring and register protocol: which address bits go to the DS1315 A0/A2.
4. Whether the card fits the original Laser 128 (new-style) as well as the 128EX.
   Renée notes the old-style original 128 used a different pinout.

## 4. Deliverables plan

- `cpld/`: CUPL (or Verilog for the open flow) plus a testbench driven by
  RAS/CAS/RA waveforms, simulated before hardware.
- `hardware/`: a KiCad 8 project with schematic, PCB matching the stock card's
  outline and connector, BOM, and JLCPCB-ready gerbers plus drill and position files.
- `software/`: notes on, or a port of, the DClock ProDOS driver and a set-clock utility.
