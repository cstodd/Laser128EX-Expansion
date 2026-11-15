# Sourcing & Architecture Options (checked Nov 2026)

Stock figures are snapshots. Check them live before ordering.

## Part status

| Part | Status | Notes |
|---|---|---|
| ATF1508AS-10AU100 (TQFP-100) | Active | DigiKey ~1.8k, Newark/Future ~100s. **LCSC/JLCPCB only ~5–11 pcs** at ~$23, so JLC would need Global Sourcing or consigned parts. |
| ATF1508AS PLCC-84 (all grades) | **EOL**, last orders Oct 2025 | Only leftover stock remains. |
| **ATF1504AS-10JU44 (PLCC-44)** | **Active** | Microchip lists the ATF1504AS as In Production. The 2025 PCNs are test-site changes, not EOL. Socketable. |
| AS6C8008-55ZIN (1M×8, TSOP-44) | **Being discontinued** | Mouser: "scheduled for obsolescence". LCSC (C1349342) out of stock. DigiKey ~2.8k. |
| AS6C8008**B** | Active, **3.3 V only** | Not usable on 5 V. |
| CY62158ELL-45ZSXI (1M×8, 4.5–5.5 V) | NRND | Pin-compatible TSOP-44 alternative while it lasts. |
| Lyontek LY62W10248 (2.7–5.5 V, TSOP-44) | Unverified | Possible second source; check its datasheet. |
| AS6C4008-55PCN (512K×8, **DIP-32**) / -55SIN (SOP-32) | Active (DigiKey), 20-week lead | Common in retro projects. Socketable. |
| DS3231SN, DS1210, 74HCT245 / 74AHCT573 | Commodity | — |

## Option A: TQFP-100 CPLD + one 1 MB TSOP SRAM (current plan)
- 5 ICs. The CPLD latches everything. Smallest board.
- JLC places the TQFP-100 and TSOP-44, but both parts are scarce at LCSC and the 1 MB SRAM is going EOL.

## Option B: fully socketable, through-hole (proposed)
- **U1 ATF1504AS-10JU44** (PLCC-44 in a socket, 64 macrocells, 32 I/O + 4 dedicated inputs).
- **Row latch:** 2 × 74AHCT573 with LE = /RASB directly. Transparent while high, latched on the fall.
  RAS-only refresh just reloads it, which is harmless.
- **Column latch:** 2 × 74AHCT573 with LE from the CPLD (transparent until any /ECAS↓).
  AHCT parts take ~7 ns versus ~25 ns for HCT, which matters on the 3.6 MHz read path.
- **SRAM:** 2 × AS6C4008-55PCN (DIP-32 sockets). Both chips' CE# come from the DS1210 CEO
  (common battery write-protect). The CPLD selects the chip with separate /OE0, /OE1, /WE0, /WE1. The deselected chip
  sees CE# low but OE# and WE# high, so it stays high-Z and is never written. In battery mode CEO is high and both chips
  are in standby.
- CPLD pin budget: 8 bus inputs, D0–7 (key detect plus RTC read-back), A18, OE0/1, WE0/1, CE,
  '245 DIR and /OE, column LE, SDA, SCL = **27 of 32**, with JTAG kept. That leaves ~5 spare for a debug header.
- 9 ICs, all in sockets except the DS3231 (SOIC-16W, 1.27 mm pitch, easy by hand). Space is plentiful:
  the stock card is ~190 × 92 mm and held 32 DRAMs.

## Read-path timing note (both options)
At 3.6 MHz, CPUP0 high lasts ~140 ns. The column address appears on ERA shortly before /ECAS↓, roughly mid-phase.
The read path is UDC → latch/CPLD (7–10 ns) → SRAM tAA (55 ns) → '245 (~10–20 ns). That is similar to the
stock DRAM's CAS path, and Renée's CPLD + low-power SRAM card worked at 3.6 MHz once reads were held
until /E1MOE↑. Use AHCT logic and the -7/-10 CPLD speed grade, never the -25 "L" grade, and
scope the real waveforms on the first board.
