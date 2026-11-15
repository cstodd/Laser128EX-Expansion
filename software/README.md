# Clock software (ProDOS 8)

Reads the card's DS3231 through the CPLD's hidden RTC port and gives ProDOS a working clock:
file dates/times are stamped, and anything that asks ProDOS for the date gets it.

## Using it
`dist/LASERCLOCK.po` is a 140K ProDOS data disk with everything below. Copy its files to your
ProDOS boot disk with the Filer, Copy II+, CiderPress or ADTPro:

| File | Type | What to do |
|---|---|---|
| `CLOCK.SYSTEM` | SYS | Put it **before BASIC.SYSTEM** in the boot directory so ProDOS runs it first. It finds the card, installs the driver and then starts BASIC.SYSTEM. |
| `CLOCK.MAIN` | BIN | `BRUN` it from your `STARTUP` (the example `STARTUP` does). |
| `SET.CLOCK` | BAS | `RUN SET.CLOCK` once to set the date and time (24-hour). |
| `CLOCK.SET` | BIN | used by `SET.CLOCK` |
| `STARTUP` | BAS | example: `10 PRINT CHR$(4);"BRUN CLOCK.MAIN"` |
| `CARD.TEST` | BAS | `RUN CARD.TEST` to test the card (below). |
| `CARDTEST` | BIN | machine-language engine used by `CARD.TEST` |

### CARD.TEST
First pick the CPU speed (1 / 2.3 / 3.6 MHz, set via the `$C074` speed register). Then choose:
1. **Quick RAM test**: all 1 MB, one 256-byte block at a time: save, write and verify $00, $FF, $55, $AA and an
   address pattern, then restore. **The RAM disk is kept.** About a minute; one dot per 64K.
2. **Full address test**: fills all 1 MB with an address-derived pattern and verifies it. This catches
   shorted or open address lines, which the block test can't. **Erases the RAM disk.**
3. **Retention check**: after test 2, power the Laser off for a while, power on, boot, and run this.
   It verifies the pattern survived on the battery.
4. **Clock test**: shows the DS3231 date and time, checks the seconds advance, and reports the
   oscillator-stopped flag (the clock lost power since it was last set: check the battery).

On a failure it prints the error count, the first failing address in hex, and the values written and read.
At the 3.6 MHz setting the Laser itself slows expansion-RAM accesses to 2.3 MHz (Tech Ref App. A), so
tests at 2.3 and 3.6 MHz exercise the same card timing. Run tests 1 and 2 at 1 MHz and at 3.6 MHz.
After test 2, don't let anything write to the RAM disk before the retention check.

At boot you should see `LASER 128 CLOCK INSTALLED`. `NOT FOUND` means the card (or its CPLD
logic) didn't answer; nothing is changed in that case.

## How it works
- ProDOS only allows a clock driver of 125 bytes (at `$D742`). The work needs ~365 bytes, so a
  108-byte **stub** goes in ProDOS's slot and calls the **driver body** (2 pages, relocatable).
- The body exists in two places: **auxiliary memory** `$0C00-$0DFF` (installed by
  `CLOCK.SYSTEM`, which disconnects ProDOS's 64K `/RAM`; the 1 MB card replaces it), and **main
  memory** (two pages reserved through BASIC.SYSTEM by `CLOCK.MAIN`).
- The stub prefers the main copy, then the aux copy. It runs a copy only if its signature and a
  checksum over both pages are intact, so a copy that another program has overwritten is
  skipped and never executed. With neither copy present the date simply isn't updated.
  - Under BASIC.SYSTEM and most programs the clock works normally.
  - Programs that take over auxiliary *and* that main memory (e.g. AppleWorks) get the correct
    date/time when they start; while they run, the time doesn't advance.
- Each read: save the slinky address and the 8 RAM bytes at it, write the unlock key (it lands in
  those 8 bytes), read DS3231 registers 1-6 over I2C, lock, write the 8 bytes back, restore the
  address. The RAM disk is never disturbed. Interrupts are off for the ~2 ms this takes.
- The body uses only the stack and zero page `$3A-$41` (saved and restored) as scratch, and writes
  nothing in main memory except `DATE`/`TIME` (`$BF90-$BF93`). That is what lets the same code run
  from auxiliary memory, with reads switched to aux and writes left on main.

Files: `clkbody.s` (driver body), `stub.s`, `clocksys.s`, `clockmain.s`, `clockset.s`,
`i2c.inc` (I2C over the RTC port), `reloc.inc`, `defs.inc`.

## Building and testing
Needs `ca65`/`ld65` (cc65) and Python 3 with `py65`.
```sh
python3 software/build.py          # -> software/build/
python3 software/test/harness.py   # 65C02 emulation tests
python3 software/mkdisk.py         # -> software/dist/ (binaries + LASERCLOCK.po)
```
Independent image check with AppleCommander 1.10.1 (`net.sf.applecommander:AppleCommander`, Maven Central):
```sh
javac -cp AppleCommander-1.10.1.jar software/test/CheckImage.java
java -cp AppleCommander-1.10.1.jar:software/test CheckImage software/dist/LASERCLOCK.po software/dist
```
It lists the volume, checks each binary against `dist/`, and prints AppleCommander's own listing of the
BASIC programs. All of these matched as of this commit (19 blocks used, file types and load addresses correct).

The harness runs the real binaries on a 65C02 emulator, with models of the Laser's main/aux
memory and language card, the slinky registers (auto-increment, 1 MB), the card's CPLD (unlock
key and RTC port, as in `cpld/laser128_ramcard.v`), a bit-level DS3231, and the parts of ProDOS
the programs use. It covers install, reads from either copy, fallback when a copy is damaged, no
copies, a card without the RTC, 1 MB address wrap, setting the clock, and the `CARDTEST` engine
with injected faults (stuck data bit, stuck address line, dead battery, missing card).

## Not yet verified on hardware
- The ProDOS 8 version on the target disk must have its clock-driver slot at `$D742` (true for
  ProDOS 8 1.x-2.4.x). `CLOCK.SYSTEM` checks this and refuses otherwise.
- The Laser's own RAM-disk firmware is assumed not to keep anything in the 8 bytes at the current
  slinky address *between* its own calls (the driver restores them anyway).
