# keys.svg: facts and sources

Figure: `gen_keys.py` writes `keys.svg` to `scratchpad/captive/infographics/` (PNG:
`rsvg-convert -z 1.5 keys.svg -o keys.png`; committed as `reversing/captive/infographic_keys.png`). Run from `M68000/`
with `uv run python -I reversing/captive/py/infographics/gen_keys.py`; its printout is kept in
`scratchpad/captive/infographics/gen_keys.out`. It reads `scratchpad/captive/infographics/data/route.json` (override:
`ROUTE_JSON`), written by `uv run python -I reversing/captive/py/mapgen/full/route.py 0 100 -j 10 --json <that file>`
(about 15 minutes on 10 cores; the summary is kept beside it as `route.txt`), and builds Phoopel (D0 = 13, D2 = 0)
from the chained generator. Everything except Phoopel's door, clipboard, panel and code is model output.

Style: a plain diagram style taken from the box art (dark slate, gold light, the red disc with a white up-arrow, white
condensed capitals), at Dave's request, not the house style of the other four Captive figures. Font: Barlow Condensed.

| fact in the figure | source |
|---|---|
| title strip: one number builds every base; locked doors; the code on a clipboard | `mapgen.md` "Call interface and seeds", "Locks and keys" (key object `$5c`/`$5d`, CLIPBOARD, word = code) |
| A: schematic maze, not a real base; the digger numbers cells as it carves; a clipboard only on a cell numbered no higher than its door; cells dug before the door are on the entrance side | `mapgen.md` "Locks and keys" step 7 (G0(K) ≤ G0(D)) and "Why the key is reachable" (the entrance-side argument is labelled inferred there; the census is the evidence) |
| B: 8,617 / 8,617 keys dug no later than their door | `mapgen.md` "Why the key is reachable", census over the 400 gate bases (`full/chain_run.py locks`) |
| B: 5,640 keys behind another lock's door; 0 of 16,357 such dependencies point to a later-dug door | same census ("Every such dependency (16,357) has G0(D_other) < G0(D_this)") |
| B: open the doors in dig order and never get stuck | same section ("Doors can be opened in dig order"); `route.py`: the dig-order plan stuck 0 times over 1,062 finishable bases |
| C: Phoopel, mission 2 target 3, lock 4: door (7,9) kind 2 (flames), clipboard on (7,9), panel W (5,8), prize E (9,12), code `$8520`, label 15099 | `gen_keys.py` printout and assert; `mapgen.md` "Sealed keys" (emulator: `enter13.repl`, `live13.py`, `panel13.py`) |
| C: "the wall of flames was built on top of it" | `mapgen.md` "Why the key is reachable" (D still plain when K is drawn; the door feature then overwrites the key's `$28`) |
| C: 622 of 1,193 open cells only this door leads to; map shows rows 0-14, columns 0-23 (the top floor) | `gen_keys.py` printout; `mapgen.md` "Sealed keys" (`sealed.py`: 622 of 1193) |
| C: 100 of 24,603 keys in missions 1 to 100 sealed | `route.json` (sum of `sealed`, `keyed`); `mapgen.md` "Sealed keys" (`keyondoor.py 0 100`) |
| C: 38 of 1,100 bases cannot be finished without guessing a code; up to 65,536 settings | `route.json` (`clip_finishable` false with a generator side reachable when every door is open); `mapgen.md` "Can such a base be finished?" (11 only kind 2, 256 settings; 27 with kind 3, 65,536) |
| D: opening a door only adds floor, so the fixpoint answers finishability exactly | `route.py` `Base.openable`; `mapgen.md` "Can such a base be finished?" |
| D: bars 1.00x, 1.53x, 9.68x; median over 1,057 of 1,062 finishable bases, 5 at the search limit; A* over the needed locks, median 6 of 31 | `gen_keys.py` printout from `route.json`; `mapgen.md` "Routes" (A* optimal only over routes that open the needed locks) |
| E: panel shows the clipboard's number; two LCG steps of code + base number; undone, 15099 gives `$8520`, the setting that opens Phoopel's door in the emulator | `mapgen.md` "Locks and keys" step 7 (`$12d4e`, proven 301/301) and "Sealed keys" (`panel13.py`); inversion asserted in `gen_keys.py` |
| E: with the label, 1,100 of 1,100 bases can be finished (model) | `route.json` (`label_finishable`) |
| footer: generator port checked 400 of 400 against the emulator | `py/mapgen/full/README.md` (`chain_run.py gate`) |
| footer: prior work, captive.atari.org MapGen (2007) | `mapgen.md` "Why the key is reachable" (the paragraph on it and where it differs) |

What the work found in the docs: `finish.py`'s 27 unfinishable bases assumed every lock other than the sealed ones
openable; with the fixpoint the count is 38 (31 missions with an ordinary target, not 23). `mapgen.md` "Can such a
base be finished?" is corrected.

Not shown, deliberately: the five bases where A* hit its node limit, and the one base (mission 12, target 11) where
the dig-order plan left dig order; both are in `mapgen.md` "Routes".
