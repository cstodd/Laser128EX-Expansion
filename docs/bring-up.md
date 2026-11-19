# Bring-up: first rev 0.2 board

A suggested order, so that each step can only fail in a small, findable way. Parts: `docs/ordering.md`.

## 1. Bare board
- Look it over against `hardware/rev02/render-gerber-top.png` / `-bottom.png`.
- Meter: **+5 V to GND must not be a short** (J3 pin 4 to pin 1, or J1 pins 1–2 to 28–30).

## 2. Assembly (no chips in the sockets yet)
1. **U8 (DS3234, SOIC-20W) first**, while the board is bare: pin 1 by the dot/bevel. Check for bridges between
   pins with a loupe; pins 2 and 7–15 are all ground anyway.
2. Resistors: R1 (1k) and R2 (47k) stand **vertically**; R3/R4 (10k) and R5 (1k) lie flat.
3. Capacitors: C12 (1 µF) ceramic; C13 (22 µF) electrolytic, mind the polarity.
4. Sockets: PLCC-44 (U1; mind the bevelled corner), DIP-20 × 3, DIP-32 × 2 (dual-wipe), DIP-16.
5. J2 (JTAG), J3 (debug), BT1 holder (**no coin cell yet**).
6. **J1 on the underside** (the bottom silkscreen says "J1 SOCKET THIS SIDE"), pin 1 = square pad. Check its
   position against the stock card before soldering all 30 pins.

## 3. Program the CPLD on the bench
Fit **only U1** (ATF1504AS) and power the board from a bench 5 V supply on **J3: pin 4 = +5 V, pin 1 = GND**
(current-limit it to ~100 mA). With nothing else fitted, a blank CPLD's floating outputs can't drive anything.
Program `cpld/rev02/fit/laser128_ramcard.jed` through J2 (`cpld/rev02/README.md`, "Programming"). Verify.
Current with only the programmed CPLD fitted should be tens of mA.

## 4. Fit the rest and power up in the Laser
1. Fit U2–U4 (74AHCT574/573/245), U7 (MAX693A), then U5/U6 (AS6C4008-55). Mind pin 1 on each.
2. Laser off. Plug the card into J13 (the INT/EXT PORT 5 switch set to enable the RAM interface). Power on.
3. Check: the Laser boots as usual; +5 V at J3 pin 4; **VOUT of U7 (pin 2, net VBB) ≈ 4.7–4.8 V**
   (that's the SRAMs' supply).
4. Boot ProDOS: **`/RAM5`** (slot 5, drive 1) should appear and be usable.

## 5. Tests (`software/rev02/dist/LASERCLOCK2.po`)
The disk is bootable (ProDOS 2.4, with CLOCK.SYSTEM before BASIC.SYSTEM): boot it and it lists the utilities.
To use your own boot disk instead, copy the files across, keeping CLOCK.SYSTEM before BASIC.SYSTEM. `CARD.TEST` asks for the CPU speed
first (it sets it with `POKE 49268`, i.e. `$C074`: 0 = 1 MHz, 128 = 2.3, 192 = 3.6).
1. At **1 MHz** and again at **3.6 MHz**: test 1 (quick RAM), test 2 (full address, erases the RAM disk) and
   **test 5 (bank hop)**. Test 5 at 3.6 MHz is the deciding one for the SRAM speed: if it fails there, fit the
   45 ns CY62148ELL on adapters (`docs/ordering.md`) and repeat.
2. `RUN SET.CLOCK`, set the time; then CARD.TEST test 4 (clock): the seconds should advance and the
   oscillator-stopped flag should be clear.
3. Fit the CR2032. Run test 2, power the Laser off for a while (an hour or more), power on, boot, run test 3
   (battery retention). Then check the clock kept time.
4. Reboot with CLOCK.SYSTEM installed: ProDOS dates on new files, `CAT` shows them.

## 6. Scope checks on the finished card (optional, recommended)
Same setup and monitor loops as `docs/scope-tests.md`:
- With the **write** loop running at 3.6 MHz, **RTC_SCLK (CPLD pin 36)** must stay flat high through every
  write (this is the glitch the /RASB gating fixes; `cpld/rev02/README.md`).
- Read-data timing on a bank change, if test 5 is marginal: CH2 on a data line at the card, against /E1MOE↑.

## If something is wrong
- **No /RAM5 or RAM errors everywhere:** CPLD not programmed or wrong file; U2/U3 swapped ('574 vs '573); a
  socket pin bent; VOUT of U7 (pin 2) low, or +5 V below 4.4 V (U7 then holds the SRAMs deselected).
- **Errors only in test 5 at 3.6 MHz:** read margin on bank changes; use the 45 ns SRAMs.
- **Clock reads $FF / "NOT FOUND":** U8 soldering (pins 1, 4, 16–20), R1/R2 values, CPLD file; J3 pin 2
  (DBG0) goes high while the card is in RTC mode, which shows the unlock worked.
- **Time lost with the Laser off:** coin cell, BT1 polarity, U8 pin 16 (VBAT).
