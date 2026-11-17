# lcp: handoff

Updated 2026-11-17 by the session that started the workstream (see `git log -- M68000/reversing/lcp` for the commit).

## Resume point

- Last commit of this workstream: the one adding `reversing/lcp/` and this file.
- Working data: `scratchpad/lcp/` (disk images in `disk/`, extracted files in `files/`, decompile in `decomp/`, boot
  segments in `boot/`, query drive in `q/`). Rebuild: `reversing/lcp/README.md` "Provenance" (unzip, `msa2st.py`,
  `py/patch_odd.py`, `extract_disk.py`) and "How it was run".
- Start from: `scratchpad/lcp/house.snap` (the house running with the shipped man Bart, hour 12, guestbook done).
- Uncommitted work left behind: none in the repo; the Ghidra project and `lcp.c` are in `scratchpad/lcp/decomp/`.

## Proven so far

- `$16f50` (the action cascade: events, alarm, bladder, thirst, hunger, daily appointments, query queue, secondary
  desire): 1000/1000 with four failing controls, `reversing/lcp/py/gate_toplevel.py 1000 3`.
- `$1747e` (hours awake, two-hour period, personality permutation, weekend swap, uniform draw with no immediate
  repeat): 2000/2000, six failing controls, `py/gate_secondary.py 2000 7`.
- `$17c46` (new person: twelve uniform draws from TOS `Random`, a name from `NAMES`, no serial number): 100/100,
  two failing controls, `py/gate_newperson.py 100 1`.
- The query queue never frees a dropped request's slot: gate control 839/1000, and the natural drive
  `reversing/lcp/queue_leak30.txt` (23 enqueues, 13 obeys, 2 drops, count ends 10).
- `tools/gates.py run lcp`: 3/3 PASS.
- The drive is deterministic: `reversing/lcp/drive.txt` from a fresh 40M-step boot ends `cmp`-identical to `house.snap`.
- Personalities 6 and 0, and 7 and 5, are identical (period table `$2b49e`, read from RAM, used by the 2000/2000 gate).

## Running

Nothing running.

## Open, in priority order

1. The LLM-in-the-house comparison needs the man's needs clocks: how hunger, thirst, bladder, illness and happiness
   rise and fall per game minute (Kroah's stats page gives rules; nothing here proves them). Find the per-minute tick
   (start with `$26914`, which the main loop runs before every decision), model it, gate it with a watch over a long
   natural run of `house.snap` against the model's predicted levels.
2. Game time: how fast the house clock (`$4ca20` hour, minute word unknown) runs against VBLs, and whether it follows
   the guestbook time. Needed to state "per hour" behaviour in real time and to run a long simulation.
3. A new person through a real boot: delete `HYBER` from a copy of the run disk (`tools/add_file_to_disk.py --remove`
   needs a subdirectory check first) and drive the move-in; confirms `$17c46` is the path a fresh disk takes and gives
   a second man for the comparison. `PE2..PE6.LCP` as head types 2..6 is Kroah's mapping, unchecked.
4. The query parser and priority: who computes `$5539a` (base priority + rnd(0,3) + PLEASE + mood, per Kroah), and the
   vocabulary in `WORDS`; then whether enough low-priority drops make him deaf for a session (the leak's end state).
5. Name the action routines dispatched by `$172a6` from their bodies (currently Kroah's names, unchecked), and
   the house-event handlers behind `$1721c`. Secrets: compare the code's control keys (`$18656` handles key codes 1, 2,
   3, 4, 6, `$17`) with the crack's READ.ME list.
6. `HYBER` save path: which routine writes it (the leak drive wrote one disk sector) and when.

## Known traps

- The shipped `LCP.PRG` bombs on TOS 1.00 (odd DATA size): use `disk/tmbird03_even.st`, made by `py/patch_odd.py`.
- Menu choice 2 quits to the desktop; the first double click on `LCP.PRG` after the pointer move does not launch, the
  second does (`drive.txt`).
- `ATARI_TRACE_GEMDOS=1` past the launch writes a huge log (`Cconis` polled constantly).
- The man reaches `$16f50` only once or twice per 30M steps: a `hits`/`bp` budget for a decision must be long.

## Waiting on Dave

- The behaviour model is a fixed-priority cascade with lookup tables, not needs-weighted scoring, and Kroah published
  its structure in 2006 (README "Prior art"). A "generative agents, 1985" post has to frame the 1985 side as a
  rule cascade plus randomness; the new material is the instruction-level proof and the three quirks (no-repeat draw,
  leaking queue, duplicate personalities). Whether that is enough for the post is your call.

## Next session

Open item 1, then 2: find the per-minute needs tick from `$26914` in `scratchpad/lcp/decomp/lcp.c`, gate it, and
measure the game clock. Those two make a long-run simulation (and the LLM comparison) possible. `/resume lcp`.
