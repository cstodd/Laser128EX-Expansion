# Laser 128EX Battery-Backed SRAM Expansion + Clock — Design Notes

Status: **rev 0.1 complete: schematic, routed 2-layer board (DRC clean), Gerbers, CPLD logic + simulation. Next: fit the CPLD (Windows tools), order boards, write the 6502 RTC driver.**
Interface facts (pinout, timing) are in [`laser-expansion-interface.md`](laser-expansion-interface.md).
The decisions below come from the earlier design conversation (Claude.ai, Nov 2026) and were re-checked
against the Technical Reference Manual.

## 1. How it works

- The stock card (VTech 702175) is only DRAM: 32 × 41256 in four 256 KB banks. The Laser
  motherboard holds the slinky address register and auto-increment (`$C0D0–$C0D3`) and drives
  the card with multiplexed DRAM signals: ERA0–8, /RASB, /ECAS1–4, /RWR, MEMRD, /E1MOE and D0–7.
- Our card latches the row on /RASB↓ and the column plus bank on /ECASn↓, which gives a
  20-bit SRAM address. RAS-only refresh cycles are ignored. The existing Laser firmware, the ProDOS
  RAM disk and the built-in diagnostics work unchanged.
- J13 has no spare signals, so the **real-time clock is reached through the RAM data port**
  (`$C0D3`) after an unlock sequence (§3).
- Target: **Laser 128EX**, including 2.3 and 3.6 MHz. The J13 pinout is identical on the New Laser 128,
  so the card should work there too.

## 2. Locked parts: architecture B (socketed, through-hole), chosen Nov 2026

The TQFP-100 ATF1508AS + 1 MB TSOP plan (architecture A) was dropped. The AS6C8008 is going EOL, both
parts are scarce at JLCPCB/LCSC, and a socketable CPLD still exists. See [`sourcing.md`](sourcing.md).

| Ref | Part | Package | Notes |
|---|---|---|---|
| U1 | **ATF1504AS-10JU44** | PLCC-44 in THT socket | 5 V, 64 MC, 32 I/O + 4 inputs. Active. Pin map in `hardware/rev01/README.md`. |
| U2 | **74AHCT574** | DIP-20 | Row register: ERA0–7 → MA9–16, clocked by ROWCLK (/RASB↓). AHCT for speed; not LS/HC. |
| U3 | **74AHCT574** | DIP-20 | Column register: ERA0–7 → MA0–7, clocked by COLCLK (first /ECASn↓). |
| U4 | **74HCT245** | DIP-20 | Data buffer. A = card bus XD, B = Laser D. DIR = MEMRD (as on the stock card); /OE from the CPLD. |
| U5, U6 | **AS6C4008-55PCN** | DIP-32 | 512K×8, 2.7–5.5 V. U5 = bank 0, U6 = bank 1. **Not** a 3.3 V-only part. |
| U7 | **MAX693ACPE+** | DIP-16 | Replaces the obsolete DS1210. VOUT = battery-switched SRAM rail (250 mA from VCC, 10 mA from the battery). CE IN→CE OUT gating ≤10 ns, held high below 4.40 V. /RESET (pin 15) → CPLD power-on clear. WDI/OSC pins open, PFI→GND. 0.04 µA from the battery. |
| U8 | **DS3231M+** (or DS3231SN#) | SOIC-16W | I²C RTC, TCXO, ±2 ppm. Pins 5–12 grounded. 0.84 µA typ from the battery. |
| BT1 | CR2032 | Keystone 103 holder | Feeds the DS1210 VBAT1 and the DS3231 VBAT. |
| J1 | 2×15 socket, 2.54 mm | custom U-numbered footprint | Mates with the Laser J13. |
| J2 | 2×5 IDC | 0.1" | JTAG, Altera/Atmel 10-pin layout (1 TCK, 2 GND, 3 TDO, 4 VCC, 5 TMS, 9 TDI, 10 GND). |
| J3 | 1×4 header | 0.1" | GND, DBG0 (CPLD 41), /RESET, +5V. |

Address mapping: SRAM A0–A7 = column ERA0–7 (U3), A8 = column ERA8 (CPLD), A9–A16 = row ERA0–7 (U2),
A17 = row ERA8 (CPLD), A18 = bank bit 0 (CPLD), chip select = bank bit 1 (CPLD drives OE0/OE1, WE0/WE1).
The mapping only has to be consistent, so any permutation of ERA bits works.

**Why '574 and not '573:** at 1 MHz /RASB goes high *before* /ECAS ends (Fig. 11-19a). A transparent
'573 would then pass the refresh row to the SRAM mid-read. Edge-triggered registers hold the row until
the next /RASB↓, which comes after the access is over.

**Why separate OE/WE per SRAM:** the DS1210 has a single CE path. Both SRAMs share CE#, so the CPLD
selects a chip by giving only that one OE# or WE#. The other chip is enabled but idle, with its outputs high-Z.

### J1 footprint (confirmed with Renée's kit socket and the original card photo)
- 2.54 mm pitch, 2.54 mm row spacing. The socket's solder pins measure 36.35 mm end to end.
- Pins 1–15 run down the row facing the **board interior**; pins 30 down to 16 run down the row at the
  **board edge**, so pin 30 sits beside pin 1. Pin 1 is the square pad, marked by the extra
  silkscreen line at that corner.
- The stock KiCad 2×15 footprint numbers odd/even across the rows, so it **must not** be used.
- Before ordering, print 1:1 and check it against the socket or the original card.

Battery life estimate with the Laser off: two SRAMs at roughly 4–6 µA each (typical; to be measured) + DS3231
~0.84 µA + MAX693A <0.1 µA ≈ 10–13 µA, so a 220 mAh CR2032 lasts roughly 2 years of continuous off-time.

**Architecture under review:** see [`sourcing.md`](sourcing.md). The 1 MB SRAM is going EOL and a socketable
PLCC-44 option exists.

## 3. Clock integration: RTC port behind an unlock key

The CPLD gives the DS3231's SDA/SCL a tiny bit-bang port. Writing bit 0 = 1 pulls SDA low,
writing bit 1 = 1 pulls SCL low, and reading bit 0 returns SDA. A custom 6502 driver handles I²C in software.

**Change from the earlier plan:** that plan put the port in a fixed address window at the top of the 1 MB.
The Laser firmware's ProDOS RAM disk uses the whole expansion RAM, so a fixed window would
corrupt the top of the RAM disk. RAM-disk writes landing there would also toggle SDA/SCL at random,
which could write garbage into the clock. Instead the CPLD uses a **phantom-style unlock**, the same idea as Dallas's
DS1315 but implemented in the CPLD:

- The CPLD watches card data on every expansion-RAM **write**. A specific 8-byte key written
  in consecutive accesses (any address) switches the card into RTC mode. Any wrong byte resets the matcher.
  Random data matches with probability 2⁻⁶⁴.
- In RTC mode, accesses to `$C0D3` hit the RTC port and **never** the SRAM: /CE is held high,
  so RAM contents are untouched even though the address auto-increments.
- A write of a "lock" value, or any /RASB with no ECAS for longer than N cycles, drops back to RAM mode.
  Exact rules to be set in the CPLD spec.
- Cost: the CPLD needs card-side D0–7 as inputs (8 pins plus a small state machine). It fits easily in 128 MC.
- The driver saves the slinky address registers, sends the key, does the I²C transfer, locks, and
  restores the registers. RAM-disk contents are never disturbed.

## 4. Power and battery backup
- Normal: +5 V from J13 pins 1–2 feeds everything. The MAX693A VOUT feeds the SRAM.
- Laser off: the CR2032 feeds the DS3231 VBAT (timekeeping) and the MAX693A BATT input. VOUT switches to the
  battery and keeps the SRAM alive; the MAX693A's CE gate holds both SRAM CE# high below its 4.40 V threshold.
  The CPLD and '245 are unpowered; the SRAM sees their pins near 0 V, which is safe because CE# is high.
- Battery life: roughly 10–13 µA with the Laser off, about 2 years per CR2032 (§2, `ordering.md`).

## 5. 128EX timing rules for the CPLD (from Fig. 11-19)
- Expansion-RAM cycles never run faster than **2.3 MHz**: at the 3.6 MHz setting the Laser slows to 2.3 MHz for
  these accesses (Tech Ref App. A, p. A-3). With strobes at the delay-line tap times (an inference), the simulation
  shows ~14 ns worst-case read margin with 55 ns SRAM on a bank change; see `cpld/rev01/README.md`.
- /E1MOE rises exactly at the CPUP0 fall, while /RASB, /ECAS and /RWR are still low.
- SRAM /WE = /RWR·/ECAS·/E1MOE, so the write ends on /E1MOE↑ (early) before data floats.
- SRAM /OE and the '245 enable are held until /E1MOE↑ (late).
- '245 DIR follows MEMRD (high = card → CPU).

## 6. Toolchain
- CPLD logic in portable Verilog, simulated with Icarus Verilog.
- Fitting (done, Nov 2026): Yosys + hoglet67/atf15xx_yosys + Atmel `fit1504.exe` under Wine → `cpld/rev01/fit/laser128_ramcard.jed`.
  Checked three ways: RTL testbench, the fitter's equations, and the .jed decoded with prjbureau's fuse database
  (`cpld/rev01/fit/README.md`).
- Programming: ATDH1150USB + ATMISP, or an FT232H/USB-Blaster + OpenOCD via SVF.
- PCB: generated in KiCad 7, now maintained in KiCad 10 (`hardware/rev01/README.md`).
- 6502: ca65/ld65, tested on a py65 65C02 emulator harness; disk image built by `software/rev01/mkdisk.py`.

## 7. Task list
1. ~~KiCad symbols, footprints, schematic~~ (done)
2. ~~CPLD Verilog + testbench~~ (done), ~~fitted and verified~~ (done)
3. ~~PCB layout, DRC, Gerbers, drill, BOM, placement~~ (done; KiCad 10, 100 × 90 mm)
4. ~~6502 clock driver, set-clock utility, card test, disk image~~ (done)
5. Order boards and parts; assemble; program the CPLD; bring-up with `CARD.TEST` (tests 1, 2, 5 at 1 and 3.6 MHz).
6. AppleWorks 5.1 support (§8.3).
7. Driver: shorten the interrupts-off window for interrupt-driven serial (§8.2).

## 8. Software compatibility: comparison with AE's DClock, GBBS Pro, AppleWorks (Nov 2026)

### 8.1 How DClock did it (AE DClock User's Manual v1.0, 1988)
- Hardware: a Dallas **DS1215** phantom clock plugged into a DRAM socket on the IIc memory card (Ram Express or
  Apple's card), coexisting with the DRAM for **bit 0 of the third bank** (App. B, p. 14).
- Unlock: one read, then **64 writes** to that bit carrying `$5CA3 3AC5 5CA3 3AC5` (LSB first); a wrong bit or an
  intervening read aborts. Then the 8 BCD registers are read or written as one 64-bit block, one bit per access.
  AE quotes false-trigger odds under 1 in 10^19.
- Ours is the same idea: a 64-bit key arriving through ordinary expansion-RAM accesses (8 bytes instead of 64 bits),
  with the same false-trigger odds. The difference is after the key: DClock's chip shifts its bits out
  directly, while ours bit-bangs an I²C conversation (start/stop, ACKs, address and register pointer) with the
  DS3231. That is why our driver is ~365 bytes and doesn't fit in ProDOS's 125-byte clock slot.
- DClock's AppleWorks patch ("ClockWorks", Ch. 2) did not do the time reading. DCLOCK.SYSTEM made DClock a ProDOS
  clock; ClockWorks added a live date/time on AppleWorks' bottom line (replacing "Apple-? for Help") and `@` to
  fill DATE/TIME database categories. It was built into the AW 2 Expander. A live display under AppleWorks
  implies DClock's driver survived AppleWorks, i.e. fitted in the ProDOS slot (an inference; the manual
  doesn't say where the driver lives).

### 8.2 GBBS Pro (source: github.com/callapple/GBBS-2.x)
**Expected to work, with the time advancing.** Configure GBBS with the **ProDOS** clock (`CONFIG/CLOCKS/PRODOS.S`),
which just calls MLI GET_TIME and reads `$BF90-$BF93`.
- GBBS is started from BASIC.SYSTEM (`-ACOS`, per CONFIG's closing instructions), so CLOCK.SYSTEM's chain to
  BASIC.SYSTEM is right. Put `-ACOS` in STARTUP after `BRUN CLOCK.MAIN` (the main copy is lost when ACOS
  loads, which is fine).
- ACOS never touches the aux-memory switches (no RAMRD/RAMWRT/AUXMOVE anywhere in ACOS or the GBBS
  segments; only the Thunderclock driver does), so our **aux copy at $0C00 survives**. ACOS puts code in the
  language card at `$D500+` in bank 2 (`$C083`); ProDOS's clock slot at `$D742` is in bank 1, so the stub
  survives too.
- **Caveat: interrupts.** Since 1991 the GBBS SSC driver is interrupt-driven with a ring buffer
  (`CONFIG/MODEMS/HAYES.SSC.S`). Our driver runs with interrupts off for ~2 ms; at 9600 baud and above (~1 ms per
  character, one-byte receive register) a character arriving then can be lost. Fix (task 7): keep `sei` only
  around the parts that touch RAM-disk bytes (save, key, restore) and let the I²C transfer run with interrupts on.
  RTC mode is only entered after the key, and an interrupt handler that touched the expansion RAM mid-transfer
  would hit the RTC port. GBBS's handlers don't, but that case should still be handled before relaxing `sei`.
- Not yet tested on hardware or in an emulator.

### 8.3 AppleWorks 5.1 (target: the last 8-bit version)
Facts (AppleWorks 5 Delta manual):
- AW5 needs 256K; IIc-class machines need a slinky card (`SEG.XM`, "Apple Memory"). On a Laser 128EX our 1 MB card
  is what lets AW5 run, and AW5 uses it as desktop memory.
- AW5 reads the clock continuously: main-menu clock display, time-based screen blanking, and AfterWork modules
  that need a clock.

Today: AW5 takes over main and aux memory, so both copies of our driver body get overwritten. The stub's
signature/checksum check skips them safely, so the date/time stays frozen at AW5's launch. AW5's timed
features would stop working.

Plan for a patch:
1. The stub already accepts a body at any page (`stub+5` main page, `stub+6` aux page) and the body is relocatable.
   So the patch only needs **two pages AW5 will never use**, plus a small loader that copies the body there and
   pokes the page number into the stub.
2. Find those two pages: AW5's memory map (main, aux, language-card banks, what SEG.XM keeps in main memory).
   Sources to read: Lissner's AW 2.0 program/source notes (on the Asimov mirror; older version, but documents
   the hooks and memory structure), the TimeOut programmer documentation in
   `documentation/applications/appleworks/time_out/`, and the AW5 disk images.
3. Candidate approaches, in order of preference:
   - **Reserve two pages through AW5 itself** (lower its memory top, or a TimeOut module allocated as permanent
     and resident in main memory), then point the stub at them.
   - A small patch to AW5's startup (APLWORKS.SYSTEM) that does the same before AW5 sizes memory.
   - Last resort: rework the driver to fit the 125-byte slot (would need hardware help, see below).
4. Interaction to verify: AW5 uses the slinky card itself. Our driver saves and restores the slinky address and
   the 8 bytes under the key, and ProDOS calls the clock from AW5's main code, not inside its RAM transfers, so
   this should be safe, but it must be tested.
5. Test plan: AW5.1 on real hardware or an emulator with the user's ROMs (none available here). Check that the
   main-menu clock advances, a file saved later carries the later time, and screen blanking triggers.

Hardware alternative for a future revision: a 3-wire RTC (e.g. DS1302: one command byte, then a plain bit stream,
no ACK/addressing) behind the same key would make a driver small enough for ProDOS's slot, as DClock's was. That
would make AppleWorks and anything else work with no patch, but the DS1302 is crystal-based (more drift than the
DS3231's TCXO) and the board would change.

## 9. Driver v2 plan: body in aux language card bank 2 (**parked** Nov 2026: superseded by §10 if the DS3234 prototype works)

### Why
- Measured in the emulator (one ProDOS clock call, aux copy, caller had interrupts enabled): **18,347 cycles with
  interrupts off** (≈18 ms at 1 MHz). Stub integrity check 14,048; body 4,299. The README's "~2 ms" was wrong.
  For comparison, the a2stuff DClock driver (125 bytes, in the ProDOS slot) is ≈1.5–2 ms with interrupts off.
- Interrupt-driven serial (GBBS's SSC driver, ProTERM) loses characters at 9600+ (≈1 ms per character, 1-byte
  receive register), and even 2400 is marginal at 18 ms. GBBS and ProTERM are system programs, so they use
  our **aux** copy.
- The aux copy runs with RAMRD on, and nothing confirms ProDOS's language-card IRQ path is safe in that state, so
  `cli` can't simply be added there. (The Laser ROM handler in page $C4 does handle any memory configuration,
  Tech Ref p. 10-6, but during an MLI call the vector comes from ProDOS's language card.)
- ProDOS 8 TN #23: the MLI keeps interrupts off only briefly at entry, so our window does block interrupts.
- ProDOS 8 TN #26: with /RAM removed (CLOCK.SYSTEM removes it), applications may use aux memory **above $800**,
  which is where our aux copy ($0C00) lives. That explains AppleWorks overwriting it. **Aux language card bank 2,
  $D100-$DFFF, is reserved for third-party RAM-based drivers.** TN #23: ProDOS installs correct IRQ vectors in the
  aux language card at boot.

Note: the card's RAM disk is **`/RAM5`** (Laser port 5 firmware, ProDOS slot 5 drive 1; confirmed by the user and
Renée's original docs). ProDOS's `/RAM` is the separate 64K aux-memory RAM disk that CLOCK.SYSTEM removes.
To check later: AppleWorks 5 can use a slinky card as desktop memory. Does it respect files on /RAM5, or treat
the card as free memory?

### Design
1. **Body** at aux LC bank 2 `$D100` (installed by CLOCK.SYSTEM: ALTZP on, LC bank 2 write-enabled, copy,
   restore). It runs with **ALTZP on**, not RAMRD, so interrupts go through the aux-LC vectors ProDOS installs.
   The long parts can then run with the **caller's interrupt state** (only re-enable if the caller had them on).
   The body still keeps interrupts off around the parts that touch RAM-disk bytes: save the 8 bytes and the
   slinky address, send the key, restore.
2. **Stub** stays in ProDOS's 125-byte slot (main LC bank 1, `$D742`). It can't switch to aux LC bank 2 from there
   (its own code would vanish), so it uses a **trampoline in the GETLN buffer `$0200`**, which clock drivers may
   clobber (TN #1: first 17 bytes; a2stuff: `$200-$207`). The trampoline must be ≤17 bytes, for example:
   `STA $C009` (ALTZPON) / `LDA $C080` (read aux LC bank 2) / `JMP $D100` … and the body JMPs back to
   `LDA $C088` / `STA $C008` (ALTZPOFF) / `RTS` = 16 bytes; the stub then restores LC bank 1 read+write
   (`LDA $C08B` ×2, the state the MLI sets).
3. **Politeness with ALTZP on:** aux ZP and the aux stack belong to whoever uses ALTZP (TN #26 calls aux memory
   below $800 system-reserved, but apps like AppleWorks may use aux ZP). The body must not leave changes there:
   - Return to the trampoline by `JMP` (no return address on the aux stack).
   - Open question A: where the body's scratch lives. With bank 2 **read-only** (`LDA $C080`, one access) the
     body can't write its own page. Options: (a) write-enable bank 2 (`LDA $C083` ×2: trampoline grows to 19
     bytes, over TN #1's 17), (b) use aux ZP/stack bytes with save/restore on the aux stack (the aux stack's
     own contents below SP would still be touched), (c) split the odd-address double read between stub and
     trampoline (works by the LC latch rules but fragile on clones). To decide first thing.
4. **Integrity check** (stale-copy protection) stays, but runs with interrupts allowed (no RAMRD needed with
   ALTZP on). Also make it cheaper: cover only the code bytes, with a faster sum (e.g. `ADC (zp),y / ROL`, about 12
   cycles per byte, detects every single-byte change).
5. **Fallbacks:** keep the main-memory copy (CLOCK.MAIN) path. The stub prefers main, then aux LC.
6. **Harness work:** model ALTZP (aux ZP/stack + aux LC), LC bank 1/2 read/write latches, the trampoline, and
   IRQ windows. Measure the longest interrupts-off run (target ≲ 1,000 cycles, i.e. under one character time
   at 9600 baud at 1 MHz) and run the existing 52 checks plus new ones: aux ZP/stack and `$0200-$0210`
   restored, AppleWorks-style wipe of aux `$0800-$BFFF` survived.
7. **Hardware/emulator checks** we can't do here: IRQ with ALTZP on during an MLI call on a real Laser (serial
   receive at 9600 while a program calls GET_TIME in a loop), and whether AppleWorks 5.1 leaves aux LC bank 2
   `$D100-$DFFF` alone.

References downloaded this session: ProDOS 8 Technical Reference (Asimov mirror), ProDOS 8 TN #1, #12, #23, #26
(prodos8.com), a2stuff/prodos-drivers (clock driver conventions, DClock driver), GBBS-2.x source, AE DClock manual.

## 10. Rev 0.2 direction: DS3234 (SPI) and a driver in ProDOS's 125-byte slot (Nov 2026)

Divergence point: branch **`rev0.1-ds3231`** (commit `b042fed`) holds the complete rev 0.1 (DS3231 / I²C board,
fitted CPLD, driver v1). Rev 0.2 work lives in `cpld/rev02/` and `software/rev02/` until proven, then replaces
rev 0.1 in the main tree.

### Why
Historically ProDOS clock drivers are unobtrusive: the whole driver fits in ProDOS's 125-byte slot (DClock,
No-Slot Clock, Cricket). Ours can't because of I²C (start/stop, ACKs, addressing; three port writes per bit).
SPI plus a CPLD that clocks **one bit per `$C0D3` access** removes that, and with it the aux-memory body,
the /RAM removal, the AppleWorks problem and the long interrupts-off window (§9).

### DS3234 facts (datasheet, Maxim 19-5338, uploaded Nov 2026)
- DS3234S# (0 to +70 °C) / DS3234SN# (−40 to +85 °C), 20-pin SO 300 mil, 1.27 mm. Pins 2 and 7–14 are N.C. and
  **must be grounded**. Pins 18 and 20 are both SCLK (internally connected). RST (pin 6) is open-drain with an
  internal pull-up and can be left open; INT/SQW and 32kHz are unused.
- VCC 2.0–5.5 V (from +5 V), VBAT 2.0–3.8 V (CR2032). Inputs need VIH ≥ 0.7·VCC (3.5 V at 5 V): CPLD CMOS outputs
  are fine. DOUT is push-pull.
- SPI modes 1 and 3 (polarity chosen by SCLK's level when CS falls), up to 4 MHz, MSB first. The first byte is the
  address: bit 7 = 0 read, 1 write; burst transfers auto-increment. Time registers 00h–06h (seconds..year).
- **DOUT is high-impedance while CS is high, and in read mode until data is ready** (Table 3), so DIN and DOUT can
  share one CPLD pin (3-wire SPI).
- Battery current 1.5 µA typ / 2.3 µA max including temperature conversions every 64 s (CRATE = 00; 128/256/512 s
  selectable). **BB_TD** (register 13h bit 0) disables conversions on battery; no figure is given, but from
  IBATTC = 400 µA for ~125 ms every 64 s the conversions average ≈ 0.8 µA, so ≈ 0.7 µA with BB_TD (estimate).
  That's a modest gain against the ~10–13 µA total, which the SRAM dominates; the cost is uncompensated drift while
  off. Also has 256 bytes of battery-backed SRAM (could hold settings).

### CPLD (rev 0.2)
- Same key matcher and RAM logic. In RTC mode, the I²C port is replaced by:
  - a **control write** (D6 = 1): D0 → CS (1 = selected), no clock;
  - a **bit write** (D6 = 0, D7 = 0): D0 → MOSI (latched at the start of the access), SCLK low for the access and high
    at its end, so the DS3234 latches DIN on the rising edge (mode 3);
  - a **read**: SCLK low during the access, so DOUT shifts out the next bit on the falling edge; the CPLD returns it in
    D0 ({signature, DIO}); SCLK rises at the end;
  - **lock** (D7 = 1) as now, which also deselects CS;
  - DIO is driven only during bit writes, so the shared DIN/DOUT line is never fought over.
- Pins: CS, SCLK, DIO = 3 (today SDA and SCL = 2). Reuse pins 34/36 plus pin 39 (no longer wired to MEMRD; the '245
  still gets MEMRD directly) or pin 41 (debug).
- To check in simulation: DOUT valid time after SCLK falls against our read sample point, CS setup/hold (400 ns
  CS to SCLK, 400 ns CS inactive), and the 30 ns DIN setup/hold around SCLK's rise.

### Driver (rev 0.2): target ≤ 125 bytes, entirely in ProDOS's slot
- All 8 key writes go to one address (reset the slinky low byte before each, as the a2stuff DClock driver does), so
  only **1** RAM-disk byte is saved and restored.
- Interrupts off only around the key and the restore; `plp`/`php` hands the caller's interrupt state back for
  the SPI read. Target: interrupts-off window of a few hundred cycles.
- Read 00h–06h in one burst (address byte 00h = eight zero bits), BCD → ProDOS date/time, scratch in `$3A-$3E`
  (ProDOS's own clock driver uses those) and `$200-$210` (TN #1).
- Rough budget: entry/exit ~8, save/key ~28 (incl. 8-byte key), CS + address ~12, read 7 bytes ~20,
  BCD + packing ~40, lock + restore ~10 → ~120.
- No aux memory, no stub/body split, no checksum, no /RAM removal. CLOCK.SYSTEM just probes and installs.

**Prototype result (Nov 2026):** final port design is "writes set registers, **reads are the clock**" (a fast write
is only ~22 ns wide between /ECAS and /E1MOE, too short for tCL ≥ 110 ns). Fits in 40/64 macrocells; passes the
rev02 testbench (DS3234 timing model) as RTL, fitter equations and decoded fuses. **Hardware check needed: /RWR must
be valid before /E1MOE falls** (otherwise each RTC write starts with an SCLK glitch). Details: `cpld/rev02/README.md`.

### Plan
1. ~~Prototype: CPLD rev02 Verilog + testbench with a DS3234 SPI model; fit it.~~ (done)
2. ~~Driver rev02 in the emulator harness~~ (done: **122 bytes**, fits the slot; interrupts never disabled; `software/rev02/README.md`).
   Rev 0.2 CLOCK.SYSTEM, CLOCK.SET (incl. BB_TD option), CARD.TEST and disk image `software/rev02/dist/LASERCLOCK2.po`: done, emulator-tested.
   **Board note: DIN/DOUT line needs a pull-DOWN** (the driver relies on it to send read address 00h).
3. If both pass: board refactor (DS3234 footprint, CPLD pin changes) → rev 0.2.

### Board refactor status (rev 0.2 PCB, `hardware/rev02`, scripted in `tools/rev02_sch.py` / `tools/rev02_pcb.py`)
- Schematic done (DS3234SN#, R1 1k series DIN/DOUT link, R2 47k pull-down, CPLD pins 34/36/39); ERC clean.
- PCB `prep`: U8 → SOIC-20W, rev 0.2 nets, stale copper removed. Routing U8 at its old spot (bottom of the
  board) failed: three SPI nets need to get from the CPLD to the bottom and only two corridors exist (the old
  SDA/SCL routes).
- PCB `move` (option 1): U8 rotated 90° just right of the CPLD (old R3–R5 spot; SMD, so B.Cu passes under it),
  R3–R5 horizontal stacked below it, R1/R2 vertical DIN0207 (2.54 mm) and C3/C9 between the CPLD and the RAMs;
  the x 85–93 mm strip in front of J1 is kept clear. A first try that put R1/R2/C3/C9 in that strip walled off
  J1's fan-out and was dropped.
- All four RTC nets route easily now. Freerouting couldn't finish two CPLD↔J1 nets (ECAS3_n, ERA8); those,
  the GND island bridges (U8's ground pins, U1-10) and moving ECAS3_n / E1MOE_n under U8 on B.Cu were done by
  hand in KiCad 10. Lesson: Freerouting was routing GND as a signal (≈400 mm of GND traces) and the move step
  originally ripped up everything crossing a moved courtyard, both layers; both made it much harder.
- **Done:** DRC 0 unconnected / 0 errors, schematic parity clean, J1/H1 geometry unchanged, fab outputs and
  renders in `hardware/rev02` (status in `hardware/rev02/README.md`). Still open on hardware: the
  /RWR-before-/E1MOE scope check.
