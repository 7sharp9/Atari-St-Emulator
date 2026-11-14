# Captain Blood: handoff

Updated 2026-11-14 by an overseer session that promoted two subagents' passes, the rule interpreter and the galaxy (commit `f234aa3`).

## Resume point

- Last commit of this workstream: `f234aa3` captainblood: the rule interpreter as a model, the galaxy.
  `uv run python tools/gates.py run captainblood`: 1/1 PASS (gate `rules`).
- Working data: `M68000/scratchpad/captainblood/` (`disk/ZUUL040.MSA` from the Dropbox `Zuul #40.zip`, `zuul40.st`,
  `files/`, `depacked/`, `zuul_depacked.bin`, 62 snapshots, the first pass's logs and `report.md`). Rebuild:
  `reversing/captainblood/README.md` "Provenance" and "Running it"; anchors in `scratchpad/ANCHORS.md`.
- Start from: `key1_30M.snap` (the bridge at 191/012) for the flight, `u2.snap` (Izwals) or `q16_e.snap` (Croolis)
  for the conversation; all carry a sidecar that remounts `zuul40.st`.
- Uncommitted work left behind: none.

## Proven so far

- Provenance: three sha256 recomputed; the `JEK!` depacker reproduces `depacked/BLOOD.COM` byte for byte from the
  promoted `py/jekdepack.py` (README "Provenance").
- `BLOOD.COM` parses whole: 120 vocabulary records, 16 race records with contiguous offsets, every race's rule list
  to its terminator (Yukas 695, Izwals 554, Croolis 324) (`py/blood_com.py`; README "The conversation data").
- Reply engine `$e45a`: a mouth click runs the rule scan 262 times and the matcher 244, a no-click control 0
  (`py/census_speak.sh`; README "The reply engine").
- From the subagent's first pass, read from its logs and screenshots and not re-run: the boot narrative, the
  milestone drives, five depacked files equal to RAM, the hit-table entries named by clicks.
- The rule interpreter (`rules.md`): `py/rules/cbmodel.py` models `$e45a` and its callees `$e6a2` (match), `$e58a`
  (condition), `$e628` (state action), `$e22e` (compose): 1750/1750 against `callcap` on three seeds, seven broken
  controls 1566 to 1738 of 1750 (`uv run python reversing/captainblood/py/rules/gate.py`; the gate NOPs `bsr $de74`
  at `$e584`). Stream B is three mask bytes per 8 elements: required, omit from the reply, not looked for.
- Ten sentences in the Izwal conversation get the model's predicted reply, 10/10 (`py/rules/drive_pairs.py`): the
  sentence icons are poked into `$dc32`/`$dc34`, the mouth click and the reply are real, the start is the poked route.
- The galaxy (README "Galaxy and terrain"): `$b830` places 128 planets with TOS Random seeded from `_hz_200`, frozen
  at 2160 by the game's own Timer C shutoff `$bec6`; status comes from `BLOOD.COM` state bits, 128/128
  (`py/galaxy/status_check.py`). Ten unpoked arms with different key timing 0/128 planets differ; five arms with the
  seed poked 128/128 positions differ, 0/128 status (`py/galaxy/runarms.sh`, `diffarms.py`). Model 128/128 on six
  seeds, four broken controls 0 or 1 of 128; the y-bound and duplicate rules are read, not discriminated
  (`py/galaxy/galaxy_model.py`). That real hardware varies the seed through load time is inferred.
- `BLOOD.CPT` is the save file: the cockpit load click swaps in its galaxy, 0/128 before and 128/128 after
  (`py/galaxy/cpt_load.sh`); no `_hz_200` value reproduces that galaxy.

## Running

Nothing running.

## Open, in priority order

1. A clean canyon landing: the conversation is reached only with the `$d5c0` poke (`py/goto_planet.sh`). Read the
   flight loop `$10800..$11400` and steer it; proof is the contact setup `$d8c8` reached with no poke, then the speak
   census on that route.
2. The rule model on other races: drive races 3, 4 and 6 (poke `$e3d4`/`$e3d8` to the race's streams, or reach such a
   planet) with `py/rules/drive_pairs.py` against the model; they are decoded from the data only
   (`tables/*_rules.txt`). Then the vocabulary flag bytes (`$40`, `$c0`, `$41`), the state bits beyond 1, 7 and 998,
   and condition-flag bit 5: each a drive that toggles the bit against a same-snapshot control.
3. The 128 icons as a PNG tied to the vocabulary, and scripted sentences per race.
4. The one branch the gate never reached (a held condition followed by an empty action, `$e4fe` then `$e56c`): find
   it in the data with `py/rules/dump_rules.py` or build the state by poke. Model `$e344`, `$e284` and the `$de74`
   redraw so the gate needs no `$e584` NOP.
5. `CLONE` (no opener hit, no name string: find it through the load code in `$d0xx` or a `watch` on its DMA target
   `$55c00`); planet status bit 4 (who reads `$10a74`, which `$10bbc` sets to `$a0` or `$f8`); the save routine
   `$d106` and cockpit entries `$d66a`/`$d6ae` (read, not run); `ethnicol.jar`.
6. Whether real hardware gives a different galaxy per boot (`_hz_200` at `$bec6`): needs a cycle-timed emulator
   (Hatari or MAME); the fixed 3000-step Timer C here cannot show it.

## Known traps

- The menu's cracktro goes silent on GEMDOS after about 3.5M steps: it is polling the ACIA for F1..F3, not hung.
- The game resets the pointer between screens: read `$c6ce`/`$c6d0` from the snapshot before each move (`py/drive.py`).
- An icon click is refused while the alien still has speech pending (`$e3f0` bit 8): click the mouth until it clears.
- `i1.snap` (the census's start) has no scripted drive: it is `u2.snap` after the alien's four speech parts and one
  grid click. Script it before relying on it.
- `bp b26e` never stopped in 60M steps though the trace shows `Supexec($b26e)`; undiagnosed, use step counts.
- This is the French build; the header text is the crack's.
- The rules gate passes a threshold break (coin `$8000`, roll `$f000`) unless a Random draw lands on the threshold:
  `gate.py` solves seeds for those cases. The first matching rule in stream order wins.
- The BLOOD.CPT load button is enabled only on the cockpit screen (click (160,50) from the bridge first). `hits` after
  the click reads 0 for the handler `$d044`: use its return `$d0ea`.
- FDC multi-sector reads over-read neighbouring files: a sector read is not an opened file (`py/galaxy/fdc_files.py`).
- `py/blood_com.py` parses and prints at import, so `py/rules/cbdata.py` is a separate loader.

## Waiting on Dave

- Nothing.

## Next session

`/resume captainblood`. Run `uv run python tools/gates.py run captainblood` (1/1) and
`bash reversing/captainblood/py/census_speak.sh` (262 / 244 against 0) as the controls. Then Open 1 (the canyon
landing), so that the rule model and the driven sentences stand on an unpoked route, and Open 2 (other races).
