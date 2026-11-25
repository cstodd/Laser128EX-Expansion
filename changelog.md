# Changelog

Newest first. Rule (see `CLAUDE.md`): add an entry at least every couple of hours of work, and before ending a
session. Earlier entries were reconstructed from the git history.

## 2026-11-25
- Added session hand-off docs: `CLAUDE.md` (rules and reading order), `architecture.md`, `building.md`,
  `progress.md` and this changelog, so a fresh session can pick up without re-reading old conversations.

## 2026-11-20 – 2026-11-23
- Boards and parts ordered (JLCPCB, leaded HASL, tented vias, order mark removed). CPLD programmer chosen:
  ATDH1150USB (an FT232H + OpenOCD is the flexible alternative; MAXQ kit, T48/TL866 and FT232RL aren't
  suitable for the ATF1504AS). -10JU44 vs -7JX44: either, same `.jed` (U = industrial, X = commercial grade).
- Laser +5 V measured at J13 pin 1 on eight supplies: 5.13–5.20 V. Both SRAM options OK (`docs/mechanical.md`).
- Board physical clearances and J1 position verified on the printed/real board.
- ERA8 scope check deferred to the first board (CARD.TEST test 2 covers it). `hardware/rev02/todo.md` updated.
- Cost-reduction and Pico/Pi discussion: a microcontroller can't meet 1 MB + ~80 ns response + battery
  retention; savings would come from volume, a cheaper RTC, or SMD assembly (`progress.md`, parked ideas).

## 2026-11-17
- **Scope session on a bare 128EX** (procedure: `docs/scope-tests.md`; results: `cpld/rev02/README.md`):
  - /RWR lags /E1MOE by up to 4.72 ns in accelerated cycles (leads by 8.7–14 ns at 1 MHz) → **CPLD fix: SCLK
    gated by /RASB** (no board change). Old logic fails the new testbench; new logic passes all three checks.
  - /RASB, /ECAS, MEMRD, write data (D0) and ERA0 timing measured at both speeds; the testbench now models all
    of them, including ERA moving on mid-cycle at 1 MHz.
  - /ECAS falls 174 ns after /E1MOE → bank-change read margin ~2 ns with 55 ns SRAM → order the 45 ns
    CY62148ELL as a backup; CARD.TEST test 5 at 3.6 MHz decides.
- Docs pass before ordering: new `README.md`, `docs/bring-up.md`; `docs/ordering.md` rewritten for rev 0.2;
  CPLD programming section; `$C074` speed register documented; 11 mm clearance to the RF shield; PA0216
  TSOP-II adapter checked; dual-wipe DIP-32 sockets; PLCC socket 8.28 mm; battery estimate updated for the
  DS3234 (~11–15 µA, ~1.7–2 years). `hardware/rev02/todo.md` added.
- SET.CLOCK and CARD.TEST show weekday, date, time and temperature (°C/°F); CLOCK.SET got a read-only mode.
- Side research moved to their own repos: Apple //c expansion (`cstodd/AppleIIC-Expansion`), Laser 128 Quad
  Hi-Res ROM analysis (`cstodd/Laser128-QHGR`).

## 2026-11-16
- CPLD fitted for the ATF1504AS (Yosys + Atmel fitter under Wine), with post-fit and prjbureau fuse-level
  simulation and an exhaustive key-matcher test; testbench gaps closed by fuse-corruption trials.
- Rev 0.1 driver work (I²C, stub + aux-memory body), DClock/GBBS/AppleWorks compatibility study, hardware tests
  (IRQ.TEST, LC.CANARY). Then the **rev 0.2 direction**: DS3234 on SPI so the driver fits ProDOS's 125-byte slot.
- Rev 0.2: CPLD SPI port, 122-byte driver, CLOCK.SYSTEM/CLOCK.SET/CARDTEST, disk image. Rev 0.1 material moved
  into `*/rev01`.
- Rev 0.2 board: DS3234 footprint and nets, DS3234 cluster moved beside the CPLD, routed (last two nets, ground
  bridging and U8 ground pins by hand in KiCad 10), silkscreen/parity fixes, fab outputs, renders.
  `tools/export_fab.py` origin bug fixed (Gerbers and drill were on different origins).

## 2026-11-15
- Project start: Laser expansion interface documented from the Tech Reference Manual; architecture B chosen
  (socketed through-hole: ATF1504AS + '574/'573/'245 + 2 × AS6C4008 + MAX693A + RTC); MAX693A replaces the
  obsolete DS1210; generated KiCad library, schematic and 100 × 90 mm board; autorouting with Freerouting.
- CPLD logic and timing testbench; rev 0.1 ProDOS clock software, CARD.TEST, disk image (verified with
  AppleCommander). Owner finished the rev 0.1 board in KiCad 10 (origin, holes, island vias).
