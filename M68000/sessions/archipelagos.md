# Archipelagos: handoff

Updated by an overseer session that promoted a subagent's creature-step model (`git log -- reversing/archipelagos`).

## Resume point

- Last commit of this workstream: the creature-step promotion (`git log -1 -- reversing/archipelagos`).
- Working data: `M68000/scratchpad/archipelagos/` (`disk/TMB058.MSA` from the Dropbox `The Medway Boys #58.zip`,
  `tmb58.st`, the drive's snapshots, `isl/`, `gen/`, `creature/`). Rebuild: `tools/msa2st.py` on the MSA, then
  `bash reversing/archipelagos/py/run_drive.sh` (about 55 s; README "Running it"); anchors in `scratchpad/ANCHORS.md`.
- Start from: `m2.snap` (first-person gameplay, PC `$1c53e`) for anything in play; `n2.snap` (the archipelago map
  screen) to build another island; `n0.snap` (the code-word screen). All have both loader pokes applied.
- Uncommitted work left behind: none. `uv run python tools/gates.py run archipelagos`: 2/2 PASS (islands, creature).
- The subagent working directories are `scratchpad/overseer/tmb58/` (first look) and `scratchpad/overseer/arch_blood/`
  (creature step; `report.md` there).

## Proven so far

- The disk holds Archipelagos+ (and Trophy Soccer, a third game, FCopy), not Virus; the boot sector's BPB is fake and
  the files sit at raw track and sector (README "Disk layout").
- Cold boot to gameplay in one process with two labelled pokes that NOP the loaders' status test
  (`ww 7047a 4e71`, `ww 7047c 4e71`; `ww 13578 4e71`, `ww 1357a 4e71`): `py/run_drive.sh`; its snapshots are
  `cmp`-identical to the chained originals.
- The island builder `$15a20` as a model: the 256x256 map at `$3000` matches 65536/65536 cells on five islands
  (island 1 from disk, two poked parameter blocks, N = 150 and N = 4321 with the island number poked), control
  (RNG step + 1) 58982 to 64370 (`bash reversing/archipelagos/py/run_gate.sh`, gate `islands`; README "The island
  generator").
- `$16166` computes the parameter block from the island number: 9/9 fields for N = 150 and 4321, control 2/9
  (`py/gate_params.sh`). Islands 1 to 100 load their block from disk and 101 up are computed (`$1b33a`,
  `cmpi.w #$64`): read from code, driven only with N poked.
- The generator `$16622` is `s = 5s + 1` mod 65536: 11792/11792 successive seeds, control 0
  (`uv run python reversing/archipelagos/py/gate_rng.py`).
- The moving object is a creature (kind 8 of eight object kinds, count `$1db28`, block `$1db3e`/`$1db7e`/`$1dbbe`);
  the red "blood" is its footprint. Its step `$1a4e0`: phase +2 per call, a step every 168 calls; toward the player
  by (diff >> k) for k = 3, 4, 5, direct cell then eight neighbours, with the x difference clobbered in D4 from the
  second round; footprint on the new cell and its four neighbours. `py/creature/gate_creature.py 300` 300/300 on
  poked states (controls 12 to 184/300); the watch-log gate has 2/2 natural events (which the controls also pass)
  and 40/40 poked (gate `creature`; README "The creature and its blood"). Poking the footprint cells back removes the
  red patch (one same-snapshot pair).

## Running

Nothing running.

## Open, in priority order

1. The emulator gap (README "The emulator gap and the two pokes"): both loaders ask for 12 sectors of a 10-sector
   track and rely on a Force Interrupt ending the read with status `$80`; the emulator returns Record Not Found and
   never sets the motor-on bit. An emulator change, so it belongs to the emulator workstream and its regression net.
   Proof of a fix: the drive without the two pokes reaches the title, and its `m2.snap` equals the poked one.
2. The noisy text on the code-word and map screens (the credits are readable with poke 2): `hits` on the glyph
   routine `$18c68` there and a dump of the font source it reads. It may be a third failed load.
3. The creature's remaining unknowns: what it does to the player on arrival (let it arrive from `m2.snap`, about 5
   steps, and diff against a control); why the game left the loop and rebuilt an island after the 40th poked event
   (`bp` the first non-return, read `$1d0cc` and its caller); what reads the envelope `$1dbbe` and draws the sprite
   (poking `$1db7e` shows an unidentified black pillar: a read `watch` on `$1db7e`/`$1dbbe` or `hits` over the draw
   routines); the proximity sound `$13b2e` with `[$1b994 + dist]` (inferred: `hits` with the creature within 15).
4. The other seven object kinds (`$1db2a..$1db36`, handlers at `$1c99a`; `$1c7e8` is the creature spawn): call each
   handler under `callcap` or `hits`, then match trees, pods and the necromancer from the game's own text. The
   special-island table `$16a58` and its picture-based build path.
5. What the code word is (`$1bdda..$1bf32`), and how the map screen sets the island number in play, so an island
   above 100 is reached without a poke.

## Known traps

- `tools/extract_disk.py` lists the wrong files for this disk (fake single-sided BPB): only `ARCH.BOY` extracts
  correctly.
- A `disassemble.py --all` listing loses sync in the game's early code (dead instructions between live ones): take
  routine bodies from a live trace or `callcap`.
- A `bp` at `$70000` or `$6001e` never hits when set after the 60,000-step key hold: the loader has already run. Use
  a step count.
- Typing digits at the screen after the title does not choose an island: it is a code-word check that then forces
  island 1.
- `$78000` holds no font at game start (an earlier reading said it did).
- A `callcap` of `$1a4e0` straight from `m2.snap` has a garbage A1: the creature gate first runs to the natural entry
  (`creature_model.capture_entry()`, A1 = `$b000`). The natural step rate is about one per 16M steps, so a natural
  census is thin; the gates poke the phase to `$14e` (labelled).

## Waiting on Dave

- Whether to fix the FDC gap in the emulator (Open 1). It also blocks nothing else known, though Carrier Command's
  unreferenced Read Track helper `$2119e` sticks in a forced call and may be related.

## Next session

`/resume archipelagos`. Run `uv run python tools/gates.py run archipelagos` (2/2) as the control. Then Open 4 (the
other object kinds), which names what else lives on the island, or Open 3's arrival test for the creature's effect.
Open 1 only through the emulator workstream.
