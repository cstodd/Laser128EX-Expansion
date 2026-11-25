# CLAUDE.md — working on this repository

Laser 128EX 1 MB battery-backed SRAM + real-time clock expansion card (KiCad board, ATF1504AS CPLD, 6502/ProDOS
software). Owner: Chris (GitHub `cstodd`), a hobbyist; Claude does most of the design, code and docs.

## Start here (fresh session)
Read these, in order, instead of re-deriving anything:
1. `progress.md` — where the project is, what's next, open questions.
2. `changelog.md` — the most recent entries (top of the file).
3. `architecture.md` — how the card and software work.
4. `building.md` — toolchains and how to rebuild / re-verify each part.
5. `hardware/rev02/todo.md` — open hardware checks.
Deeper detail only when needed: `docs/design-notes.md` (decisions and history), `cpld/rev02/README.md` (CPLD and
**measured** Laser timing), `docs/scope-tests.md`, `docs/bring-up.md`, `docs/ordering.md`, `docs/sourcing.md`.

## Rules
- **Keep `changelog.md` up to date**: add an entry **at least every couple of hours of work together**, and
  always before ending a session, after a milestone, or before the context is likely to run out. Newest first,
  dated (YYYY-MM-DD), short bullets of what changed and why, with commit hashes where useful. Also update
  `progress.md` whenever the status, the next steps or the open questions change.
- **Rev 0.2 is current** (`hardware/rev02`, `cpld/rev02`, `software/rev02`). Rev 0.1 (`*/rev01`, DS3231 on I²C)
  is superseded and kept for reference only; don't develop it further.
- **The KiCad 10 board file is the source of truth** for `hardware/rev02`: the last routing and ground fixes were
  done by hand in KiCad, so `tools/rev02_*.py` no longer reproduce it. Edit the `.kicad_pcb` carefully (pcbnew
  API or KiCad), never regenerate it from the scripts. **Revert `.kicad_prl` churn** before committing.
- **The testbench models measured timing** (scoped on a real 128EX, `cpld/rev02/README.md`). Don't replace
  measured values with inferred ones; if a timing assumption changes, update the table there too.
- Verification standards before committing:
  - CPLD: `cpld/rev02/fit/build.sh` must pass all three checks (RTL, fitted equations, decoded fuses); keep
    JTAG enabled in the fit. Check macrocell use (currently 40/64).
  - Software: `python3 software/rev02/build.py` and `python3 software/rev02/test_drv.py` (**ALL PASS**). The
    ProDOS clock driver must stay ≤ 125 bytes (currently 122; the build asserts it). BASIC menus fit 40 columns.
  - PCB: KiCad DRC with 0 unconnected and 0 errors, schematic parity clean (H1/H3 are board-only), then
    regenerate fab outputs with `/usr/bin/python3 tools/export_fab.py rev02` and re-check the drill hits.
- Git: develop on the branch the session is given; commit and push when a piece of work is done; **no pull
  requests unless asked**. Never put model names/IDs in commits or files. Keep the owner's email private.
- Network: when a site is blocked, propose adding it to the environment's allowed hosts (the approval prompt is
  the ask) rather than guessing at its contents.
- Owner preferences: through-hole and socketed parts where possible; plain-English explanations; flag
  assumptions that only hardware can confirm; hardware mistakes are expensive, software can be fixed later.
- Owner's bench: Siglent SDS1202X-E scope, Rigol bench supply, UNI-T UT61E and BK 2709B meters, MESR-100 LCR,
  FloppyEmu, microscope, T48 programmer, ATDH1150USB (CPLD JTAG), Pololu AVR programmer, ST-Link. Machines:
  Laser 128EX (main target), New Laser 128, Laser 128EX/2 (has its own clock), Apple //c.
