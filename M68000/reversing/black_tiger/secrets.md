# Black Tiger: secrets, hidden content, dead code

Addresses are runtime absolute. Start snapshot `play_start.snap` (level index 0) unless stated.
Scripts and the gate (`run_all.py`, 9 drives each run twice, snapshots identical 9/9) are in `py/secrets/` (see its README); images in `img/secrets/` (table at the end).

## Table

| # | secret / feature | exact trigger | effect | proof | status |
|---|---|---|---|---|---|
| 1 | Built-in level skip | `kbd ff 85`, hold, `kbd 47` (ClrHome make), `kbd c7`, `kbd ff 00`; then per level `kbd 1c` / `kbd 9c` | sets flag `$17826` (`$c6de`); each Return does level=(level+1)&7 and re-enters `$c50e` (`$c706`); any other key clears the flag (`$c6fc`) | A/B from play_start, 3M steps: armed `$17846`=1, `$17826`=1; no-joystick control 0/0; no-ClrHome and joystick-0 (`kbd fe 85`) controls 0/0; `run_all.py levelskip*` twice identical | PROVEN |
| 2 | Pause | `kbd 19`/`kbd 99` (P); again to resume | frame body `$c900` stops, loop `$cac4` polls; time block `$1eed8..$1eede` saved at entry and restored at exit, so paused time is refunded; all other keys ignored while paused | 600k steps: `$c900` 0 hits, `$cac4` 10209 hits; control `$c900` 10, `$cac4` 0; second P: `$c900` 10 again | PROVEN |
| 3 | Door IN (map kind `$1b`, invisible) | hero within 8 px in x and y of the cell, e.g. poke `w 1f014 075801d0` (level 1, (1880,464)) | record consumed (`clr.w (A0)` `$d06c`), hero moved to anchor B (`$1eff6/8`, marker `$3e`: level 1 (272,240)), screen cleared, text "WELCOME TO DUNGEON" (`$1732b`, only reader `$d094`), 75-frame delay, `$17842 |= 2`, palette B (`$25fac`) loaded; TIME refunded to its entry value | hero (272,240) after 150k steps; `$17842`=2 and palette words 1..3 `0100 0200 0410` vs A `0103 0124 0225` after 3.65M; screenshot `doorin_a.png` shows the text, `doorin_b.png` the dungeon; twice identical | PROVEN (poke labelled) |
| 4 | Door OUT (kind `$1c`, invisible) | hero within 8 px, `w 1f014 03e80080` (level 1 (1000,128)) | `$17842 &= 1`, hero to anchor A `$1eff2/4` (the last checkpoint), palette A restored, 75-frame delay, time refunded | from the dungeon snapshot: hero (1848,464) = checkpoint just left of the door-in, `$17842`=0, palette A | PROVEN (poke labelled) |
| 5 | Checkpoint (kind `$1f`, invisible) | hero within 32 px in x and 0..80 px above the cell | anchor A `$1eff2/4` := cell; hero respawns/returns there (`$c850`) | poke (1400,294): `$1eff2/4` = (1400,304); control unchanged (192,720) | PROVEN |
| 6 | The dungeon is a separate chamber | doors `$1b/$1c`, anchor B `$3e`, levels 1..6 only (files 0..5); levels 7 and 8 have no doors and no `$3e` | upper-left chamber of each map with its own palette B (differs from A only in T0 and T6 tile files) holding old men, bonus items | `anchors.py`, `map_L*.png`; the earlier "palette B trigger unknown" is this door | PROVEN (contents per level: see special_items.txt) |
| 7 | Ending | beat the level 8 boss; poke `w 1eeb8 00010000` at level index 7 with `$1f020`=0 | `$c65a` cmpi #7 -> `$c718`: BT5 picture, 3 text pages ("BRAVE BLACK TIGER...", "YOU HAVE RETURNED PEACE...", "THANK YOU BLACK TIGER..."), then "Conversion by: Clipper Computer Products" (`$17543`, only reader `$c7c6`), level reset, attract | `drive_ending.txt`, `end_texts.png`, bp hits at `$c752 $c778 $c79e $c7c4 $c7e6 $c4c4` in order; twice identical | PROVEN (poke labelled) |
| 8 | Replicants trainer | press T (scancode `$14`) at the menu; here `w c658 60144e71` forces it | patches inner-image words: start zenny `$c8` -> `$3800` (14336), start lives `5` -> `$3e8` (1000) (final game addresses `$c4cc`, `$c4f4`; stub addresses minus `$22c`) | trainer_T_start.snap: `$1f002`=`$3800`, `$1f00c`=`$03e8`; normal start `$c8`/5. NOT unlimited; Continue (`$c620`) still resets lives to 5 | PROVEN |
| 9 | Spinning Skull (type 5) immortal | hit it | hp 100 is reached normally, but at the end of the dying animation `$e488 cmpi.b #5,(A3); beq $e50e` restores the previous state (`14(A3)`), skips score `$1775c` and the record clear | live, skull poked awake (hp 0): at `$e47e` with A3=`$1f0d0` 4 steps lead to `$e50e` twice; record still type 5; a normal actor (A3=`$1f330`) takes the score path | PROVEN |
| 10 | No cheat sequence, no debug key, no extra life | -- | see "Negatives" | whole-image scans | PROVEN negative |
| 11 | Unreferenced hint "To increase your earnings seek hidden symbols" | none | pointer `$17a82` has no reader (11 other string pointers `$17a5a..$17a8a` are read at known addresses); an old man was meant to say it | grep of all `$17a..` operands in the code area, 4-byte literal scan | STATIC-ONLY |
| 12 | "Black Tiger 1 Feb 90" | none | string at `$17316` (preceded by `#`) has no reference anywhere in the text segment: build stamp, never displayed | `strrefs.py` | STATIC-ONLY |
| 13 | Credits | names Richard J Lilley, Sarah, Teoman, Kate, Graham | they are the default hi-score table (`$17603`, scores 40000/30000/20000/10000/5000 at `$1765a`), drawn on the attract hi-score page `$102ea`; "Conversion by" only in the ending | code + strings | PROVEN (static) |
| 14 | Dead code | -- | `$f24a` (palette/counters reset, uses trap services 2 and 14), `$f434` (clear map objects), `$f51c`, `$f532..$f688` protection, `$105ba`, `$105e4` wrappers, single `bra` stubs `$fb8e`, `$fdec` | `reach.py`: 114 of 4306 instructions unreached by direct flow or any text-segment literal | STATIC-ONLY |

## Input census (all keyboard/joystick consumers)

Keyboard readers are trap #3 service 10 (`$af70`: Bconstat/Bconin(2), scancode in the low word), 21 (`$af92`: Crawcin, `& $7f`), and GEMDOS Crawio (`$c828` flush loop).
Direct ACIA reads exist only in the cracktro (`$a562`, cmp #$39) and the trainer stub (`$c658`, `$c662`). Nothing in the game proper reads `$fffc02`.

- `$c6b0` main loop, one key per frame: `$19` pause (`$caac`); `$47` then service 12 compared with `$85` sets `$17826`; with the flag set `$1c` skips a level, any other key clears it.
- `$cac8` pause loop: only `$19`.
- `$c818` (`$c814`) wait any key after `$c820` drains Crawio: used by the new-game/game-over path (`$c800`).
- `$ec74` blocking key: continue prompt `$c60a` (`and #$df`, `cmp #$59`: Y/y continues; anything else ends; the live drive uses `kbd 15`), disk prompts `$cb64` (any key), name entry `$104ce`.
- Name entry `$10386`: ASCII `$20..$7a`, max 16 chars, Backspace `$8`, Return `$d` ends. No typed word is compared with anything.
- `$f44a` shop/menu input (`$f460`): keyboard Esc `$01` and Insert `$52`, Up `$48`, Down `$50`, Left `$4b`, Right `$4d`, or joystick (fire gives `$52`). The only keyboard alternative to the joystick in the game.
- Joystick: service 12 `$b0d2` returns word `$c2fc` = joystick 0 high byte, joystick 1 low byte (`$a624`); the game uses only the low byte (`and.w #$80/$f/$c`, `cmp.b #$85`). Fire on joystick 1 ends the title, hi-score page and attract demo (`$eb3c`, `$eb7c`, `$ebc4`). Joystick 0 is read nowhere. Up+left+fire `$85` is the only special pattern; table `$17670` has 12 valid entries, the left+right rows (c..f) read overlapping bytes of the class table `$176ac` (dy 30396 etc.): reachable only with a physically impossible stick state.
- Mouse: packet handler `$a5fa` and service 28 exist; COMMAND.PRG never calls service 28. Services never called from the code area: 0 is called (`clr.w D0`), uncalled are 6, 7, 16..19, 22..24, 26..31.

## Hidden/odd content found in the data

- Map kinds `$1b..$20` are never drawn (`$d4e4..$d510` skip the sprite): doors, traps, checkpoint, exit are invisible triggers. Kinds `$11..$16` all use BTOBJ picture entry 17 (offset `$bec`, the old man / shop man figure); kinds `$17..$1b` map to BTOBJ entries 23..27 = one tiny 16x5 picture (`$38`), and kinds `$17..$1a` go to the item handler with sub-handler 0 (no effect): no level places them (marker census per file: `$17..$1a` never occur).
- Item sub-handler `$d372` (`$1f008++`, potion) is selected by no kind: `$177bd[kind]` never yields 4. Potions come only from the shop (`$fb7e`).
- Old-man table `$17b06` = [`$fcea` +100 zenny, `$fd28` time, `$fd6a` advice "Spinning Skull can't be destroyed", `$fd28` time again, `$fdb2` +1 vitality unit] for kinds `$12..$16`; the second advice text is never shown (row 11).
- Urn outcome table `$17784` (`rng(4*level+16)`, level 0..7: indices 0..43): entries 44.. (`7 x6`, `0 1 1`, then `$11 $10 $10 $11 $11`: shop man and smart-bomb drops) are unreachable at levels 1..8. Reachable outcomes: kinds 0,4,5,6,7,`$e`,`$f` and villains `$81 $86 $8f $91`.
- Level markers: actor types 1 (files 3, 7), 4 (file 2), 8 (file 3) occur in maps although the AI agent called them unassigned; their handlers exist (`$dc46` table).
- Level 7/8 maps (files 6, 7) contain no door, no `$3e` anchor.
- Level-8 shop man: `$d1ae` stores the record pointer in `$17828` only when level index is 7; `$c5a6` re-creates him after a death (the level-8 shop man survives dying).
- Deliberate hardware quirk: `cmp #$14` is T; any other key at the trainer menu loops forever (real 6850 keeps the last byte; emulator does not).

## Negatives (what was searched)

- Cheat words / key sequences: every keyboard consumer above read to its next control flow; only P, ClrHome and Return compare against scancodes in play, Y in the continue prompt, `$20..$7a` printable in name entry. No function key, Help, Undo, Insert (other than the menu), Delete or keypad code is compared anywhere in `$c470..$10786` (grep for `cmp.b/cmpi` against key constants after each trap service 10/21 call: 6 sites, all read). No word is checked in the hi-score name entry.
- Extra life: writers of `$1f00c` are `$c4f2` (:=5), `$c5d8` (-1), `$c620` (:=5 on continue) and nothing else; no `$1eebc` score threshold test other than hi-score insertion `$1039a`. Confirmed no extra-life rule.
- Debug aids: none found in the game. The only dev-looking items are the copy-protection routine (dead), the build string and the unused hint.
- Copy protection: `$f52e` returns 0 (`moveq #0,D0; rts`), `$f532..$f688` has no caller; stored at `$f68e`, tested at `$c506`.

## Images (`img/secrets/`)

| file | shows |
|---|---|
| `doorin_a.png` | "WELCOME TO DUNGEON" screen after the door-in poke |
| `doorin_b.png` | the level-1 dungeon chamber with palette B |
| `end_texts.png` | ending text pages 1..4 (page 4 overdraws page 3: "Conversion by" is drawn without clearing) |
| `map_L0.png` .. `map_L7.png` | half-size level renders with the invisible markers boxed: door-in red, door-out green, anchor B yellow, anchor A white, anchor C pink, checkpoint cyan, exit magenta, traps blue, chest brown, shop man and old men orange |

## Open questions

- What the dungeon holds per level beyond the items in `special_items.txt` (actors inside the chamber not listed); kinds `$1d` (falling P type 6) and `$1e` (P type 2 shooter) are read from code, not driven.
- Which kind maps to `$17a82` hint was probably an old man of a fourth kind; not recoverable.
- `$17824` (set by kind `$10`) is decremented in `$d4ae` but its effect on screen was not traced.
- Level 8 boss end-of-game path was driven by poke, not by killing the boss.

## Contradicted statements in the other reports

- Brief/MERGE: "palette B in T0/T6 with an unknown trigger": it is door `$1b`, restored by `$1c`.
- Mechanics: "$1f checkpoint" correct; "$1b/$1c doors in/out" correct but they are invisible and teleport within the level (dungeon chamber), not to a new level.
- Mechanics: "$12..$16 old men (+100 zenny, +30 s, advice, +30 s, vitality)" matches `$17b06`.
- Brief: trainer "unlmt life+money" is 1000 lives and 14336 zenny at game start only.

## Not exercised

- Kinds `$1d` and `$1e` driven live; the contents of each level's dungeon chamber beyond `special_items.txt`.
- The ending by killing the level 8 boss (poke used); the disk-swap prompts after a boss.
- The Continue prompt Y/N and the name entry were read from code here (driven by the systems agent's `drive_gameover_hiscore.txt`).
- The shop keyboard alternative (`$f44a`: cursor keys, Insert, Esc) was not driven.
- Real-hardware ACIA behaviour at the trainer menu.
