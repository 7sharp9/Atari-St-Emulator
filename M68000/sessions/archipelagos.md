# Archipelagos: handoff

Updated 2026-11-16 by the session that checked the island census live (ended at commit `509cf91`).

## Resume point

- Last commit of this workstream: `509cf91` archipelagos: census.py --edges reproduces the stamp-start edge distances.
- Working data: `M68000/scratchpad/archipelagos/` (`disk/TMB058.MSA` from the Dropbox `The Medway Boys #58.zip`,
  `tmb58.st`, the drive's snapshots, `isl/`, `gen/`, `pic/`, `creature/`, `census/`, `census_live/`). Rebuild:
  `tools/msa2st.py` on the MSA, then `bash reversing/archipelagos/py/run_drive.sh` (about 55 s; README "Running
  it"); anchors in `scratchpad/ANCHORS.md`. `census_live/` (entry snapshots, `gate.log`, `results.json`) is
  output that `py/gate_census_live.py` rewrites.
- Start from: `m2.snap` (first-person gameplay, PC `$1c53e`) for anything in play; `n2.snap` (map screen) to build
  an island above 100; `n0.snap` (code-word screen) for N up to 100 (poke at `$1b142`). Both loader pokes applied.
- Uncommitted work left behind: none. `uv run python tools/gates.py run archipelagos`: 2/2 PASS (islands 134 s,
  creature 14 s); `--dry-run` 0 MISSING, 0/2 gates declare no inputs.

## Proven so far

- Disk layout (Archipelagos+, Trophy Soccer, FCopy; fake BPB) and the cold-boot drive with two labelled loader
  pokes: README "Disk layout", "The emulator gap and the two pokes", `py/run_drive.sh`.
- Island builder `$15a20` model 65536/65536 on five islands, RNG `s = 5s + 1` 11792/11792, `$16166` parameters 9/9:
  README "The island generator", "Island number" (gate `islands`).
- Picture islands 5, 10, ..., 100 are 128 x 128 one-bit masks read from the disk (game track T = cylinder T, side 1):
  15, 25, 85 at 65536/65536 and 2048/2048; disk blocks 21/21 on 6 and 99: README "Picture islands",
  `py/gate_pictures.py`.
- Census over N = 1..9,999 is a model result (`py/census.py`). Its three findings are now checked live
  (`py/gate_census_live.py`, in gate `islands`). No builder write outside the map on 11/11 islands, only its stack
  pushes. The edge control makes 361 out-of-map writes, the first 71 equal to the model's in order. N/N+64 blocks
  agree in 20/21 words (only `$1698a`) on 4 pairs, and their maps differ. The model matches 42/42 live maps:
  README "Over all island numbers".
- The creature step `$1a4e0`: 300/300 poked, 2/2 natural and 40/40 poked watch events: README "The creature and
  its blood" (gate `creature`).

## Running

Nothing running. The two `stserver.dll` processes from 00:55 and 09:04 are MCP servers this session did not start.

## Open, in priority order

1. The emulator gap (README "The emulator gap and the two pokes"): loaders read 12 sectors of a 10-sector track and
   need a Force Interrupt status `$80`. An emulator change for the emulator workstream; proof: the unpoked drive
   reaches the title and its `m2.snap` equals the poked one.
2. The other seven object kinds (`$1db2a..$1db36`, handlers at `$1c99a`; `$1c7e8` spawns the creature): call each
   handler under `callcap` or `hits`, then name trees, pods and the necromancer from the game's own text.
3. The creature's unknowns: its effect on arrival (let it arrive from `m2.snap`, diff against a control); why the
   loop rebuilt an island after the 40th poked event (`bp` the first non-return, read `$1d0cc`); the reader of
   `$1dbbe` and the sprite draw (read watch on `$1db7e`/`$1dbbe`); the proximity sound `$13b2e` (inferred).
4. The noisy text on the code-word and map screens: `hits` on the glyph routine `$18c68` and a dump of its font
   source; possibly a third failed load.
5. The code word (`$1bdda..$1bf32`), and how the map screen sets N in play, so an island above 100 is reached
   without a poke. What grows with N in play besides the island (census: the island itself does not, past 101).

## Known traps

- `tools/extract_disk.py` lists the wrong files for this disk (fake single-sided BPB): only `ARCH.BOY` extracts.
- A `disassemble.py --all` listing loses sync in the early code; take routine bodies from a trace or `callcap`.
- A `bp` at `$70000` or `$6001e` set after the 60,000-step key hold never hits: the loader has run. Use a step count.
- Digits typed after the title are a code-word check that forces island 1, not an island choice.
- `$78000` holds no font at game start.
- A `callcap` of `$1a4e0` straight from `m2.snap` has a garbage A1: run to the natural entry first
  (`creature_model.capture_entry()`).
- A map-screen poke of `$1d566` only reaches N > 100; N up to 100 is poked at the `$1b142` entry from `n0.snap`.
- `stserver` `watch_add` returns `{id}` and `watch_events` returns a list of `{id, dropped, events}`; the default
  `max_events` is 10000, and one build writes up to about 480,000 events in the two watched ranges: set
  `max_events` and read `dropped` (`gate_census_live.py`, `watch_run`).
- A `re:` expect in `gates.toml` needs a TOML literal string (`'...'`): `\$` in a basic string is a parse error;
  write an apostrophe as `.` inside it.
- The edge control corrupts the stack and code and halts the game (double bus fault): it never reaches `$15b8e`.

## Waiting on Dave

- Whether to fix the FDC gap in the emulator (Open 1).
- Proposed: a `StServer.events(id)` helper in `tools/stclient.py` returning the flat event list and the dropped
  count, and a line in `tools/gates.py`'s docstring on literal strings for `re:` patterns. Both are shared
  tools, so they are left as proposals.

## Next session

`/resume archipelagos`. Run `uv run python tools/gates.py run archipelagos` (2/2) as the control. Then Open 2 (the
other object kinds), which names what else lives on the island, or Open 3's arrival test. Open 1 only through the
emulator workstream.
