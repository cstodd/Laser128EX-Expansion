# Scope tests on the J13 expansion connector

How the 128EX strobe timing in `cpld/rev02/README.md` was measured (Nov 2026), so it can be repeated on another
machine (New Laser 128, 128EX/2, a //c variant) or on a finished card. **No card is needed**: the Laser generates
every one of these signals itself.

## Equipment and setup
- Two-channel scope; used here: Siglent SDS1202X-E (200 MHz, 1 GSa/s). A cheap USB logic analyzer (~24 MHz
  sampling, ~41 ns per sample) is too coarse: some of these margins are a few ns.
- 10× probes with the **short ground springs**, grounded on a J13 GND pin. Set each channel's Probe menu to 10×
  to match the probe switch (a mismatch makes 5 V logic read as ~500 mV).
- Both channels 2 V/div, DC coupling. To compare two edges, give both channels the **same offset** so the traces
  overlay, put a Y cursor at 1.48 V (about the CPLD's TTL threshold), and put X cursors where each edge crosses it.
- Trigger: Edge, CH1 falling, **Normal** mode, level ~1.5 V. **CH1 = /E1MOE throughout**, so its falling edge is the
  time reference for everything.
- Worst case: Display → Persistence (30 s or so), then put the cursor on the far edge of the smeared band. For
  automatic numbers use Measure → Delay (FFF, LRR) or Time (−Width) with **Statistics** on and read Min/Max; press
  Clear between runs, or old results mix in.
- Note: this scope has **14** horizontal divisions (50 px each on a screenshot), not 10.

## J13 pins (DIP-style numbering)
Pins 1–15 run down one column and 16–30 back up the other, so pin 16 is beside pin 15 and pin 30 beside pin 1.
Find the orientation with a meter: pins 1 and 2 are +5 V, the pins beside them (30, 29, 28) are GND.

| Signal | Pin | | Signal | Pin |
|---|---|---|---|---|
| /E1MOE (CH1) | 16 | | /ECAS1–4 | 25, 5, 26, 4 |
| /RWR | 3 | | MEMRD | 15 |
| /RASB | 27 | | D0 | 20 |
| ERA0 | 6 | | GND | 28, 29, 30 |

## Test loops (monitor)
From BASIC, `CALL -151` enters the monitor. Type the line, then `300G` to run. **Ctrl-Reset** stops the loop and
also turns the expansion RAM off again; the loops turn it back on themselves, and they survive the reset, so
`CALL -151` then `300G` restarts one (`300L` lists it). Every loop starts with `LDA $C500`: any access to `$C5xx`
enables the expansion RAM, and /E1MOE stays idle without it. The INT/EXT PORT 5 switch must also have the
interface enabled.

| Loop | Monitor line | Code | Use |
|---|---|---|---|
| Write | `300:AD 00 C5 8D D3 C0 4C 03 03` | `LDA $C500` / `STA $C0D3` / `JMP $0303` | every /E1MOE pulse is a write |
| Read | `300:AD 00 C5 AD D3 C0 4C 03 03` | `LDA $C500` / `LDA $C0D3` / `JMP $0303` | every /E1MOE pulse is a read |
| Write, one bank | `300:AD 00 C5 9C D2 C0 8D D3 C0 4C 03 03` | `LDA $C500` / `STZ $C0D2` / `STA $C0D3` / `JMP $0303` | address stays in the first 64 KB, so the same /ECAS line pulses every time |
| Write, toggling data | `300:AD 00 C5 A9 55 8D D3 C0 A9 AA 8D D3 C0 4C 03 03` | `LDA $C500` / `LDA #$55` / `STA $C0D3` / `LDA #$AA` / `STA $C0D3` / `JMP $0303` | D0 alternates, for data valid/hold |

Each access auto-increments the 20-bit slinky address, so the plain loops walk through all four banks and the ERA
lines keep toggling. Avoid Applesoft `POKE`/`PEEK` loops: they are slow (one access every few ms), and `POKE`
goes through an indirect store that can add a dummy read, so "writes only" isn't guaranteed.

## Speed
- **1 MHz:** Ctrl-Reset without holding a key (the 128EX defaults to 1 MHz).
- **Accelerated:** hold **3** (3.6 MHz) or **2** (2.3 MHz) while pressing Ctrl-Reset or at power-on.
- Check: the cursor blinks noticeably faster when accelerated, and the /E1MOE low pulse is ~475 ns at 1 MHz
  and ~268 ns accelerated. Card cycles never run faster than 2.3 MHz (Tech Ref App. A): the 2.3 and 3.6
  settings measured identically.

## What each test checks
| Test | CH2 | Loop | Design assumption it checks |
|---|---|---|---|
| /RWR vs /E1MOE, falling | /RWR | write | SPI clock must not glitch at the start of a write (found: /RWR lags by ≤4.72 ns accelerated → SCLK gated by /RASB) |
| /RASB vs /E1MOE | /RASB | write | /RASB falls well after /RWR settles; its low time is the SPI clock low time (≥110 ns); exactly one /RASB pulse inside each /E1MOE window |
| /ECAS vs /E1MOE | /ECASn | write, one bank | when the bank is known (read margin on a bank change); /ECAS never pulses outside an /E1MOE window |
| MEMRD vs /E1MOE | MEMRD | write and read | '245 direction is set before it is enabled and held until it is off; no dip during reads |
| Write data | D0 | write, toggling data | data valid soon after /E1MOE falls and held past /E1MOE rising (the SRAM write ends there) |
| Address setup | ERA0 | write | row valid before /RASB falls, column valid before /ECAS falls |

Results for the 128EX are in the table in `cpld/rev02/README.md`.
