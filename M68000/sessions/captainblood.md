# Captain Blood: handoff

Updated by an overseer session that promoted a subagent's canyon-flight pass (`git log -- reversing/captainblood`).

## Resume point

- Last commit of this workstream: the canyon-flight promotion (`git log -1 -- reversing/captainblood`).
  `uv run python tools/gates.py run captainblood`: 2/2 PASS (gates `rules`, `canyon`).
- Working data: `M68000/scratchpad/captainblood/` (`disk/ZUUL040.MSA` from the Dropbox `Zuul #40.zip`, `zuul40.st`,
  `files/`, `depacked/`, `zuul_depacked.bin`, 62 snapshots, the first pass's logs and `report.md`). Rebuild:
  `reversing/captainblood/README.md` "Provenance" and "Running it"; anchors in `scratchpad/ANCHORS.md`.
- Start from: `key1_30M.snap` (the bridge at 191/012) for the flight, `u2.snap` (Izwals) or `q16_e.snap` (Croolis)
  for the conversation; all carry a sidecar that remounts `zuul40.st`.
- Uncommitted work left behind: none. The canyon subagent's working dir is `scratchpad/overseer/blood_canyon/`
  (`report.md`, probes `t*.py`, `fly.py`/`fly3.py`).

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
- The canyon flight (README "Canyon flight"): `$10686` sets up, `trap #15` runs `$10b8a` (loop `$10bde..$10d40`),
  `$d8c0` then goes to the contact setup `$d8c8` unless `$10642` is negative (cockpit `$db16`). ESC held through a
  flight tick reaches `$d8c8` and the conversation table `$d5e4` with no poke, a no-key control 0 (and `$db16` 1);
  ESC as the game's own landing key is inferred. A no-input flight ends shot down (`$10d42`), not on terrain: a
  terrain hit is a non-fatal bump. Collision `$10c24`: bump when `((T[o]+T[o+1])>>1)+1` > altitude `$10a66`, 52/52 on
  poked altitudes (controls 0, 7, 12 of 52). Gate `canyon` (`py/canyon/gate.py`). A mouse-only flight (`py/canyon/fly2.py`)
  reaches the pad and the ravine unpoked but does not pass it; `$110f6 = $ffff` (labelled) from there lands.

## Running

Nothing running.

## Open, in priority order

1. The speak census on the unpoked ESC route (`py/canyon/routes.py esc` reaches the `$d5e4` conversation), so the
   rule model and the driven sentences stand on an unpoked start. Then a steered ravine pass to `$110f6` < 0 by mouse
   only: track the slot centre 2 to 3 rows ahead with a controller that allows for `$10a0a`'s 13-row cumulative ramp
   (a P gain of 3 oscillated), or poke the slot drift `$110fc` to 0 as a labelled step. Check ESC against the manual
   and `hits` `$11568` for other keys (branch `$10cfe`).
2. The canyon generator: model the row generator `$11348` (midpoint displacement via `$113ca`/`$113fa`) and the PRNG
   `$11014` (`x*$3171-1` on `$1109e`) against `callcap` (read only so far), then the ravine wall and slot geometry.
   Whether the 3M-step bump wait (Timer A flag `$11a94`) is the emulator's fixed-step timer.
3. The rule model on other races: drive races 3, 4 and 6 (poke `$e3d4`/`$e3d8` to the race's streams, or reach such a
   planet) with `py/rules/drive_pairs.py` against the model; they are decoded from the data only
   (`tables/*_rules.txt`). Then the vocabulary flag bytes (`$40`, `$c0`, `$41`), the state bits beyond 1, 7 and 998,
   and condition-flag bit 5: each a drive that toggles the bit against a same-snapshot control.
4. The 128 icons as a PNG tied to the vocabulary, and scripted sentences per race.
5. The one branch the gate never reached (a held condition followed by an empty action, `$e4fe` then `$e56c`): find
   it in the data with `py/rules/dump_rules.py` or build the state by poke. Model `$e344`, `$e284` and the `$de74`
   redraw so the gate needs no `$e584` NOP.
6. `CLONE` (no opener hit, no name string: find it through the load code in `$d0xx` or a `watch` on its DMA target
   `$55c00`); planet status bit 4 (who reads `$10a74`, which `$10bbc` sets to `$a0` or `$f8`); the save routine
   `$d106` and cockpit entries `$d66a`/`$d6ae` (read, not run); `ethnicol.jar`.
7. Whether real hardware gives a different galaxy per boot (`_hz_200` at `$bec6`): needs a cycle-timed emulator
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

`/resume captainblood`. Run `uv run python tools/gates.py run captainblood` (2/2) and
`bash reversing/captainblood/py/census_speak.sh` (262 / 244 against 0) as the controls. Then Open 2 (the fractal
canyon generator as a model), the most interesting unmodelled piece, or Open 1's speak census on the ESC route.
