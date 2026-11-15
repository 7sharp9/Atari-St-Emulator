# crudebuster_hitboxes_and_ai.html: facts and sources

Figure: `py/build.py` writes `crudebuster_hitboxes_and_ai.html` from `py/page.html`, `page.js`, `style.css`, the box captures in
`assets/` (made by `py/overlay.py`), `natural.json`, `enemies1/py/brain_probs.py` (decision chart) and `enemies1/py/cdamage.py`
(damage chart). Run from `reversing/crudebuster/infographic`: `uv run python py/build.py` (needs the decrypted program image
`scratchpad/crudebuster/rom/cbuster_main.bin` and the linear listing `brain_probs.py` reads; no MAME run).
Doc abbreviations: P = `player/player.md`, E1 = `enemies1/enemies1.md`, E2 = `enemies2/enemies2.md`, N = `player/natural.md`,
A = `architecture.md`, W = `world/world.md`, R = `README.md`.

This table lists the facts added for readers who do not know the game; the facts the page already carried keep the sources
named in its footer.

| fact on the page | source |
|---|---|
| Data East 1990 arcade game, US title Two Crude (clone `twocrude`), set `cbuster` World, MAME 0.289 is emulator and oracle | R first paragraph |
| attract text `NEW YORK A.D.2010` | A "Attract loop"; W section 1 frame table |
| six levels 0-5, spawns from a level script as the screen scrolls | A "The levels", "Level scripts" |
| three buttons: attack, jump, grab / throw; priority attack > grab > jump | P "Decisions in one page", section 3 |
| 68000 main CPU; program encrypted in ROM, decrypted by MAME at load; addresses are of the decrypted image | R first paragraph; A header |
| one logic frame per VBL, 58 Hz in play | P header |
| y grows downward | P section 3 move table note |
| enemy record 64 bytes (`$40`), 16 pool A records, at most five script enemies alive at once | A "Objects" table and throttle gate |
| start of life 56 health = seven bar cells of 8 | P "Decisions in one page", +19 |
| bosses 16 to 48 health; ordinary enemies a few points (types 0-2: 2, type 4: 1, type 3: 8) | `BOSSES` in `build.py`; P 8 (g); E1 3.2 |
| attack box only while the attack flag (+28) is set | P +28, section 4 move table note |
| enemy body box from `$6b000[type][state]` + position | P section 4 `$f82e` |
| hit enemy: -1 health, state 1 stun 15 frames, state 2 at 0 health; spark at the near edge; score to the player that hit | P section 4 (`$22c56`, `$f938`, `$248bc`); E1 2.2, 2.3 |
| six copies of the overlap chain, all the same; they serve player attack, contact, melee, projectile, pick-up | P section 4 "Hit-test geometry" (`$f8ca`, `$f69a`, `$fb9c`, `$1001a`, `$e80e`, `$e9bc`) |
| contact is a trade: player -1, enemy -1, points to the player; a 2-health thug died after two touches | E1 2.3 (`expF_contact.py`, 62 events) |
| no friendly fire: no player-versus-player attack path; three-hit chain over P2 left P2 unchanged | P section 5 (`py/gate_2p.py`) |
| chain lengths 12, 24, 42 frames | P move table |
| brain steps: random target skipping inactive or downed players | P section 4 `$22b48`; P section 5 |
| table A: enemy y in (py - `$20`, py + `$60`]; B more than `$60` below; C above | E1 2.6 |
| facing hysteresis `$10`, `$30` in B and C | E1 2.6 |
| case A indexed by the player's pose and variant (copies of +24, +25); standing = pose 0 variant 0; a jab keeps pose 0 with variant 1 or 2 | E1 2.6; `brain_probs.py` docstring |
| leaves wait for the animation end, then equal-chance choice (`random & 3`) | E1 2.6 |
| random generator reseeded `$7fff8001` at every level start | E1 2.1 (read) |
| for the four types every cell with more than one outcome waits for the animation end; single-outcome cells fire at once | `brain_probs.py 3 5 9 11` output: 50 cells "on anim end", none of them 100%; 142 cells "at once", all 100% |
| bruiser (type 3, 8 health) below 32 px: idle 50%, grab attempt 25%, shuffle attack (state f) 25%; squeeze 4 per hit | E1 2.6, 3.2; `brain_probs.py 3` |
| damage: hit objects of 44 types, one value per difficulty; difficulty is a DIP switch | E1 2.4; P section 4 damage formulas |
| 320 frames blinking after join, respawn, continue; `$14` = 20 after getting up | P +54 |
| no extra life from score or items (read) | P "Decisions in one page", section 4 "No extra lives" |
| the bot is `natbot.lua` in MAME, rewrites the health cell (and blink timer), attacks only when the first jab box overlaps the target's body box | N header and first rule |

## Notes

- **The committed page was built from an older `brain_probs.py`.** Commit 5cdce0b5 changed the case A index from the
  player's action and sub-action to the player's pose and variant, and the standing row from action 8 to pose 0. Rebuilding
  changes two columns of the bruiser (distances 0 to 31 px) from "idle 100%, at once" to "idle 50%, grab attempt 25%,
  state f 25%, on animation end", which now agrees with E1 2.6. All other columns are unchanged. The prose sentence "the
  target's current action and sub-action pick the leaf" was changed to "pose and its variant" to match E1 2.6.
- **Tooltip state numbers were printed in decimal with a `$`.** `brain_probs.summarise` returns states as ints; `build.py`
  printed them with `"$%s"`, so state `$f` showed as "$15" and `$a` as "$10". Fixed to `"$%x"`. The legend and the
  doc use hex.
- The chart label "table A, player idle" was changed to "table A, you standing" (the row is pose 0, variant 0).
- The lanes diagram's canvas cut off the table C label (above the top edge) and drew the table B band under the ruler;
  the canvas is now taller and the bands sit above the ruler. No numbers changed.
- **Played-through section (refreshed from `player/natural.md` "Results" and the rules table).** Level 1 is cleared at frame 13,582 by
  the current bot (14,262 with the version before the `heli` rule), level 2 is cleared at frame 22,811, the level 2 column at
  x 2291 is passed by a jump (`hop` mode, x 2291 to 2329) and the level 4 column at x 1779 is not (taller than the 48 px
  jump). `natural.json` and the page text were rewritten from those rows; rows are cited below.
- The armoured cyborg's "12% each" is E1's 12.5% rounded. The page calls its four far-range states (d, e, f, `$10`) "jump and special states"; E1 4.1 says states d, e, f, `$10` are its long beam (hit object C4, reach 80 px). The page wording was left; the new takeaway says only "special states".
- The bruiser's state `$10` is "recover, 32 frames" (E1 3.2), but `build.py` groups every state from `b` up as "attack or
  special", so it is coloured as an attack in the chart. Left as is; the legend says "type-specific".

## Clarity pass: sources for the added or reworded sentences

| sentence on the page | source |
|---|---|
| subtitle "an arcade game, studied by running it in the MAME emulator" | R first paragraph (MAME is emulator and oracle) |
| Setup: "the other games in this series are for the Atari ST, a home computer"; "reverse-engineering the game while it ran in an emulator"; "a 68000 disassembler" | GLOSSARY.md "Atari ST", "oracle"; R first paragraph; old Setup sentence |
| key line; evidence words proven / observed / inferred and their definitions | clarity-pass conventions. Mapping used: old "measured" with a rule-against-game match count (397 tests, 71 hits, 0 disagreements; 2,628 melee tests, 13 hits, 0 disagreements; 83 of 83 health decrements) is "proven"; other "measured" is "observed"; "read" and "decoded" are "inferred"; "open" is unchanged |
| frame 2097 caption "overlaps the jab box (848 to 888)" | correction: body box 876 to 891 against jab box 848 to 888 overlaps, it is not inside (891 > 888); numbers are the old caption's |
| "a short-lived rectangle (a hit object) is built for one frame" | the old "a one-frame hit object is built" and the How-to-read of "What a hit costs" |
| "if the enemy is on your level, the target's current pose and its variant pick the leaf"; "same level"; "jump to your level / drop" | the old "in the same lane" and table A definition (E1 2.6: table A = between 32 px above and 96 px below you) |
| takeaway "The moves differ mainly in height and in timing, not in reach" | the old takeaway (same facts, lesson first) |
| "The one health pickup restores 8 and only works below 48 health" | the old bullet without "pool A object" |
| Played-through intro "Levels 1 and 2 are cleared ... The final bot is not monotonic" | N "Results" (levels 1 and 2 rows; "it is **not monotonic**") |
| Level 1 row: clear flag at 13,582 in every run of the current bot; 14,262 with the version before the heli rule; 33 of 33; heli mode, seven entries between 7,538 and 9,556; leader arena opens 760 frames earlier; roller dead by 6000, leader arena by 11020, leader dead by 13340, flag 256 frames after the leader's death; lock walls jabbed away at 943 and 3448 | N "Results" row 1; N rules table "Lock walls break under jabs" (level 1 at frames 943 and 3448). The old row's frames 5998, 11773, 14006 and 2244, 2940, 3131 belonged to the 14,262 version or are not in N and were dropped |
| Level 0 row | N "Results" row 0 (not run further, 6000 frames) |
| Level 2 row: cleared at 22,811 (23,145 in a replay from the post-helicopter state); heli parts jabbed down, 14,500 to 16,700 frames; column at x $900 hopped; conveyor block crossed by repeated hops; fights at $93a to $9c5; final boss killed in boss mode; 55 of 59 entries seen | N "Results" row 2; rules table "A tile column...", "The level 2 raised block is a conveyor", "The level 2 final boss is fought in the air" |
| Level 3 row | N "Results" row 3 (loops in the ladder search at x 500 to 535; boss at $600; ledge at $801) |
| Level 4 row: ladder found at frame 13879; halts at x 1779 in front of a wall tile that a jump does not clear; enemy type 53 waits below; 75,850 points at frame 27,100 | N "Results" row 4; rules table "A tile column..." (the jump test at x 1779) |
| Level 5 row: ladder up at x 990 at frame 9895; final block scroll $e21, 88,700 points at frame 45,000; final version stuck in the first fight (x 641); final boss never met | N "Results" row 5 (the old row said frame 30460; N says 45,000) |
| bullet "A jump clears the level 2 column ...; it does not clear the level 4 column, which is taller than the 48 px jump" now "observed" | N rules table row "A tile column in the floor row stops a walking player; a jump gets over it" |
| takeaway "a jump got over the level 2 wall but not the level 4 one" | same row |
