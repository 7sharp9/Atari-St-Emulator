# finalfight_hit_detection.html: facts and sources

Figure: `py/build.py` writes `finalfight_hit_detection.html` from `py/page.html`, `page.js`, `style.css`, `py/frames.py`
(boxes of the two landing frames from `scratchpad/finalfight/gfx/dump/<tag>_ram.bin` and the ROM
`scratchpad/finalfight/ff_main.bin`), the screenshots in `assets/` and `../py/player/ffchar.py` (blow tables). Run from
`reversing/finalfight/infographic`: `uv run python py/build.py` (no MAME run). Gates: `py/boxes_gate.py`, `py/lanes_gate.py`.
Doc abbreviations: F = `frame.md`, P = `player.md`, T = `twoplayer.md`, AI = `ai.md`, H = `hardware.md`, R = `README.md`.

This table lists the facts added for readers who do not know the game; the facts the page already carried keep the sources
named in its last section and footer.

| fact on the page | source |
|---|---|
| Capcom 1989, CPS1 board; set `ffightuc` (USA), MAME 0.289 is emulator and oracle, the F# core is not involved | R first paragraph |
| one or two players; characters Guy, Cody, Haggar | P "Characters and inputs"; T |
| spawns come from a stage script that waits for the camera to pass a trigger | F "Stage script executor" |
| Up and Down move the fighter in depth: Up raises both y (+10) and the ground line (+14) | T "Guy, Cody and Haggar" (ground line axis, 6 of 6 runs) |
| y runs upward on screen (screen y = 240 - (y - camera y)) | `frames.py` docstring, from the object-list builder `$16910` (F, page "How this was checked") |
| on the ground y equals the ground line; in the air they differ | F record table +14; `boxes_gate.py` (airborne test `+14 != +10`) |
| 68000 at 10 MHz; screen about 59.63 Hz; visible area 384 x 224 (64..447 by 16..239) | H "Which set, which config" |
| players, fighters, bosses are `$c0` = 192-byte records; pools: 2 players, 13 fighters (tag 2), 8 bosses (tag 4), 16 props (tag `$a`) | F "The object pools" |
| enemy names are the game's HUD text | F "Fighter identity" |
| 127 saved work-RAM dumps, each with a screenshot | page ledger; `py/gfx/README.md` (`gfxdump.lua` dumps work RAM and a screenshot) |
| reach list: (x - player x + `$80`) <= `$100` unsigned | F "Hit resolution" |
| lane: ground-line gap from -12 to +9, +-24 in the special | F "Hit resolution" |
| overlap test: add s, one unsigned compare with 2s, y only after x | F "Hit resolution" (`$7932`) |
| widget: the overlap checks show "not run" when not queued or x failed | `py/page.js` (`gate()` calls) |
| at most 21 entries per list; only player lists exist | F "Hit resolution" |
| damage numbers in the reach cells and Cody table are read at rank 4 | `ffchar.damage_row_value(ch, off, rank=4)` |
| rank rises by 1 every 600 frames, falls on player events, indexes health, defence class and damage column | AI "The difficulty rank" |
| defence class scaling: 10 became 8 for classes 4 and 6 | F "Damage dispatch" (`$79d8`) |
| Cody maximum health 144 (`$90`), Bred 28 (`$1c`) | F record table +24/+28 |
| chain counter limit 8, 6, 4 = 5, 4, 3 hits (limit / 2 + 1) | P per-character table ("8 (5 hits)", "6 (4 hits)", "4 (3 hits)"); P move set "limit 6 gives 4 hits"; computed in `build.py` |
| Guy's chain damage 6, Haggar's 18; jab animation 12 and 22 frames | T "Guy, Cody and Haggar" table |
| a hit from the other player starts its own counter (+148, 100 frames) | P +148; T |

## Notes

- **Mislabelled chain limit (fixed).** The reach section's row headings read "chain limit 8 hits" (Guy), "6 hits"
  (Cody), "4 hits" (Haggar). The `$be92` value is a combo-counter limit that grows by 2 per hit; P and T give 5, 4 and
  3 hits. The heading now reads "chain counter limit 8 (5 hits)" and so on; the 8, 6, 4 are unchanged.
- The existing intro says the depth slot is 21 pixels deep (12 + 9). The lane test is inclusive at both ends
  (`-12 <= g <= 9`, `frames.py`, `lanes_gate.py`), which is 22 integer ground-line values. Left as is; it is a width,
  not a count.
- The page's "127 saved frames" and `py/gfx/README.md`'s "107 distinct gfx RAM dumps" are different sets (the README's
  107 are distinct dumps for the graphics census); the gates count the files in `gfx/dump` at run time and the page's
  numbers come from those runs. Both gates were re-run for this pass: 127 dumps, attack 51 of 52, hurt 212 of 213, absent 216 of 216 and 55 of 55, windows 115 of 115 and 26 of 26, as on the page.
- No doc and figure number disagreed for this page.

## Clarity pass: sources for the added or reworded sentences

| sentence on the page | source |
|---|---|
| dek "a brawler with depth ... near enough along the street, at the right depth and at the right height" | the page's lead paragraph (three questions: near enough along the street, same depth, right height) |
| Setup "the other games in this series are for the Atari ST, a home computer"; "reverse-engineering the game while it ran in an emulator"; "a 68000 disassembler" | GLOSSARY.md "Atari ST", "oracle"; R first paragraph |
| key line; "inferred" / "observed" / "proven" in the terms, tags and tables | clarity-pass conventions. Mapping: "read in the ROM", "ROM" become "inferred"; "seen live" becomes "observed"; "saved frames" counts and "gate, 51 of 52" become "proven" in the term, "observed in saved frames" where only a sighting is claimed |
| "(the game's working memory)" for work RAM | GLOSSARY.md; the old term row |
| caption "(BRED) and the blow (blow id 1, field +22), and both fighters freeze for a hit-stop of 6 frames" | the old caption (+60 = BRED, +22 = 1, hit-stop 6); step 6 "freezes both fighters for 6 frames" |
| check table rows "near enough along the street? (reach list)", "at the right depth? (depth lane)", "boxes overlap in x/y?" | the old row names and the four steps of "Is it a hit?" |
| "On impact both fighters freeze for a few frames, the hit-stop" | step 6 (6 frames on both fighters) |
| "A prop (a breakable object)" | terms row "fighter, boss, prop" (breakable props such as drums and phone booths) |
| "rank 4, the game's running difficulty level, explained under the damage tables below" | the rank definition in "How to read the tables" |
| takeaway "Keep the expensive part, testing pairs, bounded by cheap filters: here it is bounded by the lists ..." | the old takeaway |
| script names moved from the ledger rows to the Source line; "a script that plays the game with the players' health held at full by writing it into memory" | the old rows and the old "stage bot ... survival poke" sentence |
