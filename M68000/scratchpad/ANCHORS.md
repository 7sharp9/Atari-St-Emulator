# scratchpad anchors

An index of the `.snap`/`.ram`/`.st` states under `scratchpad/` that a
NOTES.md or a RESUME block has already called out as worth reusing across
passes - not a catalogue of every throwaway per-pass snapshot. If you're
looking for "the settled-world state the 96th-99th passes used" or similar,
start here instead of grepping filenames and old NOTES.md prose.

`scratchpad/` is gitignored (see `.gitignore`'s `M68000/scratchpad/*` +
`!M68000/scratchpad/ANCHORS.md`); this file is explicitly un-ignored so it
survives a commit even though the anchor binaries themselves don't. If an
anchor listed here is missing on a fresh checkout, regenerate it via the
"how to reach it" column, or ask whoever last touched the pass that made it.

| Anchor | State it captures | Made by | Depended on by |
|---|---|---|---|
| `pm69.st` (+ copy at `pm97/pm69.st`) | The raw PowerMonger boot disk image - mission 1, turn 0, nothing played. The root of every other anchor's lineage: every `.snap` below was reached by booting this disk and driving it forward with `run.ps1 window` / the REPL. | 69th pass | Any fresh investigation that needs to replay from turn 0; `run.ps1 window scratchpad/pm69.st` |
| `pm67_ok_pre.snap`/`.ram` | An early, pre-settlement in-game state a few passes before the natural mode-`$7c` corpus was found. | 67th pass | `pm97_map0`'s own lineage (driven forward ~80M steps from here) |
| `pm73_fight.snap`/`.ram` (top-level) | A live 2-army melee in progress (mode `$32` engaged, both sides trading blows) - the "no mode-$32 record" gap the 95th pass's memo flagged, fixed by driving this forward. | 73rd pass (driven further by 95th) | `scratchpad/pm98/repro93.py`, `repro94.py` (comparison set) |
| `pm95/pm73_melee.snap`/`.ram` | `pm73_fight` driven further into full melee - the actual mode-`$32` differential-test anchor (distinct from the top-level `pm73_fight.snap`). | 95th pass | `scratchpad/pm98/repro95.py` (413/413 - the melee/combat gate) |
| `pm74_late.snap` | A later-game state used as a fourth comparison point alongside `pm88_f1`/`pm78_settle`/`pm73_fight` (mission-1-only confirmation, etc.). | 74th pass | `scratchpad/pm98/repro93.py`, `repro94.py` (comparison set) |
| `pm78_settle.snap`/`.ram` (top-level) | A settled-world state with live `$68` formation-follower / settlement records - the base the synthesised mode-`$7c` corpus was built over. | 78th pass | `scratchpad/pm98/repro93.py`, `repro94.py` (comparison set) |
| `pm96/pm78_settle.snap`/`.ram` | Same anchor, copied forward into the 96th pass's own working dir alongside its synthesised corpus script. | 78th pass (copied 96th) | `scratchpad/pm98/repro96.py` (85/85 - the synthesised mode-`$7c` gate) |
| `pm88_f1.snap`/`.ram` (top-level) | An early-game state (frame ~1) used as a baseline/regression comparison point across the dwell-upkeep and movement-mode proofs. | 88th pass | `scratchpad/pm98/repro93.py` (675/675 gate), `repro94.py` (1335/1335 gate) |
| `pm97/pm97_preplay.snap`/`.ram` | `pm67_ok_pre` driven ~80M steps forward with `word[$57fd0]` poked to 0 (forces the mode-`$7c` settlement-heartbeat branch live) - the deterministic pre-play point `pm97_map0` was captured from. Two independent drives from here reproduce byte-identical RAM/snapshots. | 97th pass | `pm97_map0`'s own lineage |
| `pm97/pm97_map0.snap`/`.ram` | **The natural mode-`$7c` anchor.** ~80M-steps-settled: 12 settlements, 19 natural `$7c` markers, 8 live herd ops / 68 markers / ~40 shepherded animals, a live 3-way territory situation. The single most-reused anchor in the corpus. | 97th pass | `scratchpad/pm98/repro97.py` (99/99), `pm99/diff_pm99.py`'s own lineage, `pm113/diff_4342.py` (herd servicer), `pm115/diff_4bc8.py` + `diff_4bc8_kind2.py` (contact reconcile), worked examples in `tools/pm_fsm_ref.py` and `tools/disassemble.py`'s docstring |
| `pm97/pm97_map1.snap`/`.ram` | `pm97_map0` driven further to the one natural state with a *grouped* record hitting the flag-bit-4 group-teardown sub-path - needed because `pm97_map0` itself never naturally exercises it. | 97th/99th pass | `pm99/diff_pm99.py` (1847/1847 - the group-teardown gate) |
| `pm120/k60_iso.snap`/`.ram` | **A second land.** Land 60 (`$580a0 = $68f`, `$5809c = $299a`) built for real through the briefing-OK path, settled 30M steps and stopped at the frame driver `$f898`: camera (45,74), yaw `$f0`, zoom 4, season word 4. 62 settlement-building records, 135 men, new `byte6` 20/22/32. `detcheck 2M` clean. Needs the 120th Timer A and zero-divide fixes. | 120th pass (`pm67_ok_pre` + the poke in `reversing/powermonger/README.md` "Driving a later land"; commands in `pm120/scr_k60.cmds`) | `port/assets_k60/` export, `pm120/k60_iso.json` (order_test input; its own screen is the previous tick's frame: score against the next `$f898` snapshot, SPEC §6 "Scoring a capture") |
| `pm121/k<k>.snap` (33 lands, `k` 0-142) and `k5_s0`/`k5_s3` | Lands built through the briefing-OK poke and settled 30M steps at `$f898` (`k5_s0`/`k5_s3`: land 5 in winter / autumn via `byte[$58146]`). Land 5 has 13 fresh kills (byte6 12), a goods pile, pigeons and a flock at settle. | 121st (`pm121/build_land.sh <k> [steps] [season]`) | the land census (SPEC §6 "Every category"), the season check, every capture below |
| `pm121/run/<land>_s1..s4.snap` (lands 5, 60, 0, 25; `k5w` = land 5 winter) | The same lands run forward in four 50M-step stretches with no pokes; the snapshot after each stretch. Deterministic (re-runs reproduce every hit count). | 121st (`pm121/runland.sh`, `hits` census in `run/<land>.txt`) | ai.md "Natural runs on later lands"; `pm121/diff_1623c.py` corpus (`pm121/corpus_1623c/`) |
| `pm121/flip/k60_flip_pre.snap`/`_post.snap` | Land 60 at the garrison defection that follows a `$550e` revolt: pre = at `$25d6` (step 4,509,837 of `run/k60_s3.snap`), post = at its return `$5c7e`. The revolt itself is at step 4,509,545. | 121st | economy.md §3 (how a settlement changes hands) |
| `pm121/cap/<view>_<i>.snap`/`.ram`/`.json` | Runs of consecutive `$f898` frames over the new categories (dead men, flock, pigeon, leader's base, goods, winter snow, autumn rain, a fight with an arrow, boats, a building going up). Score state i against frame i+1. | 121st (`pm121/capture.sh`, `dump_frame.py`) | `pm121/score.fsx`, `pm121/allpairs.txt` (27 pairs, all 100.00%) |
