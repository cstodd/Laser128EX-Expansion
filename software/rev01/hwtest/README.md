# Hardware test programs (driver v2 questions)

`software/rev01/dist/LASERTEST.po` holds two programs. Boot your normal ProDOS disk with `CLOCK.SYSTEM`
(it removes /RAM, which would otherwise own all aux memory), start BASIC.SYSTEM, then `BRUN` them from
this disk. Rebuild with `python3 software/rev01/hwtest/build.py`.

These run on real hardware only; they are **not** emulator-tested (our harness doesn't model ALTZP or
the aux language card).

## IRQ.TEST: question 1
Are interrupts handled correctly when they arrive with ALTZP on and aux language card bank 2 switched in,
during a ProDOS call? That is the state driver v2 would run in.

- Uses **serial port 2's** transmit-empty interrupt at 9600 baud as a steady interrupt source (~960/s).
  Nothing needs to be connected; if a modem is, it receives a stream of NUL bytes for about two seconds.
- First counts interrupts during a spin loop in normal memory (baseline), then installs a temporary
  clock driver that takes the v2 path (16-byte trampoline at `$0200` → spin loop at aux LC `$D100` with
  interrupts on → back), calls GET_TIME 50 times and counts again.
- Prints both counts (hex) and **PASS** if the second is at least 7/8 of the baseline.
- **A hang or crash during the test = FAIL** (the interrupt went somewhere bad). Reboot.
- "NO INTERRUPTS SEEN IN THE BASELINE" means port 2's transmit interrupt doesn't work on this machine,
  so the test is inconclusive (it would need another interrupt source, e.g. the mouse VBL).
- Restores everything it touched: the ProDOS clock driver slot and `DATETIME`, the aux `$D100` page,
  the port's interrupt setting.

## LC.CANARY: question 2
Does a program, AppleWorks 5.1 in particular, leave aux language card bank 2 `$D100-$DFFF` alone? ProDOS
Tech Note #26 reserves that area for third-party drivers.

1. `BRUN LC.CANARY`, press **M**: fills `$D100-$DFFF` with an address-derived pattern.
2. Run AppleWorks 5.1 and use it normally (open and edit files, use the desktop, let the screen
   blanker run, use TimeOut if you have it), then quit.
3. Start BASIC.SYSTEM again (don't reboot), `BRUN LC.CANARY`, press **C**: one character per page,
   `.` = intact, `X` = changed, plus the number of changed pages.
