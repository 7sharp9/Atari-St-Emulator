# lcp: handoff

Updated 2026-11-17 by the session that ended at commit `b2adce5`.

## Resume point

- Last commit of this workstream: `b2adce5` (needs and clock tick `$24648`).
- Working data: `scratchpad/lcp/` (disk images in `disk/`, extracted files in `files/`, decompile in `decomp/`, boot
  segments in `boot/`, query drive in `q/`, clock runs in `clock/`, RAM dump and tick disassembly in `tick/`).
  Rebuild: `reversing/lcp/README.md` "Provenance" (unzip, `msa2st.py`, `py/patch_odd.py`, `extract_disk.py`) and
  "How it was run"; `clock/` from `py/clock_rate.py` and `py/natural_tick.py`.
- Start from: `scratchpad/lcp/house.snap` (the house running with the shipped man Bart, 12:08 on 17 November 1986,
  guestbook done).
- Uncommitted work left behind: none in the repo; the Ghidra project and `lcp.c` are in `scratchpad/lcp/decomp/`.

## Proven so far

- `$16f50` (the action cascade): 1000/1000 with four failing controls, `py/gate_toplevel.py 1000 3`.
- `$1747e` (secondary desire): 2000/2000, six failing controls, `py/gate_secondary.py 2000 7`.
- `$17c46` (new person): 100/100, two failing controls, `py/gate_newperson.py 100 1`.
- `$24648` (clock and needs tick: thirst, hunger, illness, bladder, the 2-in-101 house-event roll, happiness, the
  calendar): 1000/1000, five failing controls, `py/gate_tick.py 1000 1`; on a natural run of one game hour,
  29123/29123 ticks against the run's own writes, through a pee, a drink and an hour rollover; 110 of 29233 frames never reach the tick, so the clock runs 0.5% slow (`py/natural_tick.py 2.2e9 1e8`). README "Needs and the clock".
- Game time keeps emulated real time: a frame is gated at 125 ms and 2 VBLs (`$263a6`), a game second is 8 frames;
  30M steps = 50 emulated seconds = 398 frames = 50 game seconds (`py/clock_rate.py 30 1000000`). A game hour is
  about 1.8G steps, about 8 minutes of wall time on this Mac.
- Illness under neglect never passes 2 (each starvation resets it to 1): model arithmetic over all timer pairs, not
  a run.
- The query queue leaks dropped requests (gate control 839/1000, `queue_leak30.txt`).
- `tools/gates.py run lcp`: 4/4 PASS.
- Personalities 6 = 0 and 7 = 5 (period table `$2b49e`).

## Running

Nothing running.

## Open, in priority order

1. The LLM-in-the-house comparison: the cascade, secondary desire and needs tick are now all gated models, so a
   pure-Python house (`lcp_model`: `needs_tick` per game second, `toplevel` when he is free) can run days of game
   time. Missing for that: how long each action takes and what it writes (drink zeroes thirst, eat zeroes hunger and
   restarts the bladder, `$23444`, `$225c2`, `$2142c`), so name the action routines dispatched by `$172a6` from their
   bodies first (was item 5). Prove each by callcap of the action's state writes, then a natural-run comparison of the
   simulated day against `natural_tick.py`-style watches.
2. House event `$1e` (raised by the tick about once an hour, with the ring sound `$2ae12`): which handler in
   `$1721c` runs it, and which end of happiness is happy (read the UI text that shows the level).
3. The query parser and priority: who computes `$5539a` (base priority + rnd(0,3) + PLEASE + mood, per Kroah), and the
   vocabulary in `WORDS`; then whether enough low-priority drops make him deaf for a session (the leak's end state).
4. A new person through a real boot: delete `HYBER` from a copy of the run disk (`tools/add_file_to_disk.py --remove`
   needs a subdirectory check first) and drive the move-in; confirms `$17c46` is the path a fresh disk takes.
   `PE2..PE6.LCP` as head types 2..6 is Kroah's mapping, unchecked.
5. Secrets: compare the code's control keys (`$18656` handles key codes 1, 2, 3, 4, 6, `$17`) with the crack's
   READ.ME list; the house-event handlers behind `$1721c`.
6. `HYBER` save path: which routine writes it (the leak drive wrote one disk sector) and when.

## Known traps

- The shipped `LCP.PRG` bombs on TOS 1.00 (odd DATA size): use `disk/tmbird03_even.st`, made by `py/patch_odd.py`.
- Menu choice 2 quits to the desktop; the first double click on `LCP.PRG` after the pointer move does not launch, the
  second does (`drive.txt`).
- `ATARI_TRACE_GEMDOS=1` past the launch writes a huge log (`Cconis` polled constantly).
- The man reaches `$16f50` only once or twice per 30M steps: a `hits`/`bp` budget for a decision must be long.
- stserver's `hits` counts an interrupt taken at a counted address and its RTE back as two arrivals (`Server.fs`
  "hits" checks the PC after every `stepOne`, no `CensusStep`): `$26bb4` counted 401 against 398 frames. For exact
  call counts use a read watch on an instruction the routine runs once (`natural_tick.py` at `$2464e`).

## Waiting on Dave

- Focus set by Dave: AI and algorithms, curiosities and secrets.
- The behaviour model is a fixed-priority cascade with lookup tables, not needs-weighted scoring, and Kroah published
  its structure in 2006 (README "Prior art"). The needs tick adds quirks of the same kind: illness capped at 2 by its
  own reset, the bladder filled by eating, not drinking, and happiness as a fixed triangle wave. Whether that is enough
  for a post is your call.
- Proposed: fix stserver `hits` to count through `CensusStep` as the REPL does (an emulator-side change behind the
  regression net), or add its double count to CLAUDE.md's `hits` rule.

## Next session

Open item 1: name the action routines `$172a6` dispatches (start with drink `$23444`, eat `$225c2`, toilet `$2142c`)
from their bodies and gate their state writes; then assemble the pure-Python house from `lcp_model` and compare a
simulated day with a natural run. `/resume lcp`.
