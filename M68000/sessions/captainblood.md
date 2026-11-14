# Captain Blood: handoff

Updated 2026-11-14 by an overseer session that promoted a subagent's first look (commit `a724ded`).

## Resume point

- Last commit of this workstream: `a724ded` captainblood: first look.
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

## Running

Nothing running.

## Open, in priority order

1. A clean canyon landing: the conversation is reached only with the `$d5c0` poke (`py/goto_planet.sh`). Read the
   flight loop `$10800..$11400` and steer it; proof is the contact setup `$d8c8` reached with no poke, then the speak
   census on that route.
2. The rule language: a Python model of `$e6a2` (match), `$e58a` (condition), `$e628` (state action) and `$e22e`
   (compose), gated against `callcap` of `$e45a` over sentences and state bits, with a broken-model control. Then
   stream B, the vocabulary flag bytes, and the race rule on races 3, 4 and 6.
3. The 128 icons as a PNG tied to the vocabulary, and scripted sentences per race.
4. The duplicates (`CLONE`, `BLOOD.CPT` unread), planet status bit 4, `ethnicol.jar`.
5. Whether the galaxy (XBIOS Random at `$b830`) is the same on every boot.

## Known traps

- The menu's cracktro goes silent on GEMDOS after about 3.5M steps: it is polling the ACIA for F1..F3, not hung.
- The game resets the pointer between screens: read `$c6ce`/`$c6d0` from the snapshot before each move (`py/drive.py`).
- An icon click is refused while the alien still has speech pending (`$e3f0` bit 8): click the mouth until it clears.
- `i1.snap` (the census's start) has no scripted drive: it is `u2.snap` after the alien's four speech parts and one
  grid click. Script it before relying on it.
- `bp b26e` never stopped in 60M steps though the trace shows `Supexec($b26e)`; undiagnosed, use step counts.
- This is the French build; the header text is the crack's.

## Waiting on Dave

- Nothing.

## Next session

`/resume captainblood`. Run `bash reversing/captainblood/py/census_speak.sh` as the control (262 / 244 against 0).
Then Open 1 (the canyon landing), so that everything after it stands on an unpoked route, and Open 2 (the rule
model), which is the reason for the workstream.
