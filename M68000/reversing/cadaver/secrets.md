# Cadaver: secrets, hidden machinery and the algorithms

What the player is not told (keys, the price of a save, the rank table's missing top title, the assert layer, leftover developer text) and
the non-trivial machinery (the level code overlay and its engine export table, then the algorithms: random numbers, sound, the day counter,
loading and protection). Scripts are in `py/secrets/` (table in `py/secrets/README.md`), all started from `scratchpad/cadaver/gameplay_empire.snap`
(CAVERN, day 1, the Empire one-disk crack) and run from `M68000/` with `uv run python reversing/cadaver/py/secrets/<script>`; `py/secrets/repl.py`
sets `ATARI_NOTRACE=1` itself. Statements marked *read* come from code only and were not run; *inferred* is a guess. Addresses are runtime absolute;
`A5 = $018152`, so `nnn(A5)` is `$018152 + nnn`.

## Keys the game reads

Two separate readers sit on the IKBD's current-key cell `2530(A5)` (`$018b34`, written by the custom ACIA handler `$01535a`, README "Keyboard
discipline"): the `$01616c` table that the README's 9th pass drove as a key dispatch (12 action ids, all inert for the *player sprite*; it is in fact the sound request table, below, so those ids were sounds), and the
main loop's own handler at `$006ba2`-`$006d10`, which the 9th pass never looked at because it watched only the player's 70-byte descriptor. The main
loop handler is where the keyboard does anything. Each row below was driven live with a real make, 60,000-step hold and break
(`main_keys.py`: every branch hit exactly once per press, 12 of 12 keys; screens by `snap_render.py`/`render_buffer.py`).

| key | scancode | branch | effect |
|---|---|---|---|
| F1 | `$3b` | `$006d02` -> `$00a9a8` | the map: a parchment scroll "ROOMS ENTERED n" (counter `2118(A5)`, bumped by the room loader `$00e8b8`; proven: `callcap e854` to room 1 writes 1 -> 2, `pause_and_map.py`) with one rectangle per visited room (visited flag = bit 6 of the room record's byte 23), the current room highlighted; the joystick scrolls it, fire leaves it. `f1_map_scroll.png` |
| F2 / F3 / F4 | `$3c` `$3d` `$3e` | `$006ba6`-`$006bc4`, repeated in nine waiting loops (`$009560`, `$0098f6`, `$009d00`, `$00aa88`, `$00b82c`, `$00dfcc`, `$011872`, `$0118c8`, and the main loop's own `$006bac`) | toggle bits 0, 1, 2 of `2499(A5)`; each toggles in every waiting loop too, so they work at any prompt. **F4 proven**: the bit strips left and right from the joystick state whenever up or down is held (`$006ac6`-`$006ae6`, it rewrites the port byte `2529(A5)` itself): held up+right reads `$09` with F4 off and `$01` with it on (`f4_mask.py`, 3 of 3 samples each). F2 (`$006c18`, `$009542`: keypad Enter becomes the confirm key of the icon-choice loop and the main loop ignores it) and F3 (`$009586`, `$009778`: skips the icon panel redraw `$00bbd4` during the icon-choice loop) are *read*, not run |
| P | `$19` | `$006c04` -> `$011834` | pause: waits at `$011842`-`$011892` until fire or any key other than F2-F4. Proven: after P the main loop (`$006ba2`) gets 0 hits in 1M steps and the pause loop 81,144; after X the main loop 41 hits, the pause loop 0 (`pause_and_map.py`) |
| S | `$1f` | `$006bd0` sets bit 3 of `2519(A5)`; `$006a40` -> `$00b61c` | save the game, for gold (next section). `save_unaffordable.png`, `save_price_prompt.png` |
| L | `$26` | `$006bde` sets bit 4; `$006a60` -> `$00b692` | the restore prompt "RESTORE GAME. PLACE A DISK IN DRIVE ONE AND PRESS 0 TO 9 OR ESC" (live, and the round trip works, below) |
| Return / Space | `$1c` `$39` | `$006cce` | opens the panel for the held rucksack item, not the keyboard twin of fire: `$006c28` waits for the key to release first, `$009682` returns at once when the rucksack is empty, otherwise the item is selected (`$009724`) and its icon panel opened (`$009c82`). Space clears bit 1 of `2519(A5)` (`$006cc2`) and goes straight to the icons, Return leaves it set and shows the rucksack grid `$0097b4` first (proven, "The player's action panel" below) |
| Down | `$50` | `$006cb0` | sets bit 0 of `2474(A5)` (cleared at `$006a8a` every frame): "down pressed", the README's crouch/interact gesture |
| H | `$23` | `$006c46` | stashes the currently selected object `1262(A5)` into `2126(A5)` and deselects it (proven: poke 168, press H: `1262 = 0`, `2126 = $00a8`); a second press restores it only if `$011256` finds the id in the type-8 list (*read*: not reached from this snapshot, `2126` is otherwise never written) |
| C | `$2e` | `$006bf2` | `bsr $a810 / jsr $11898`: clears the message window slots at `$00600a` and waits for the key to release (*read*, no visible effect from CAVERN) |
| Esc | `$01` | none in the main loop | only the boot/restore menu reads it (start fresh), plus dispatch id 55 (inert, README 9th pass) |
| Keypad Enter | `$72` | `$006c20`, `$009580` | see F2 |
| 0-9 | `$0b`, `$02`-`$0a` | `$00b850`-`$00b87a` | in the save/restore prompts: key n selects disk slot `(n-1) * $a0`; Esc aborts |

Nothing here is a cheat. No key, name or sequence was found that changes health, gold, XP or items: the only bytes the keys touch are the UI flags
above.

## Saving costs gold

`S` runs `$00b61c`. The price is `max(1186(A5), (level + 1) * 50 - 45)` where `level = 2524(A5)` (a byte, 0 at a new game, stored in the save header and
compared on restore at `$00b916`; the same field the stats scroll prints as LEVEL `2524 + 1`; it is the level directory slot, 0 for the first level). `$00df46` shows "THE GODS DEMAND A PRICE TO SAVE YOUR POSITION OF
n. DO YOU WANT TO PAY. PRESS Y OR N." (strings 60 and 62) when gold `1188(A5)` (a longword) covers it, else "YOU CANNOT OFFER THE GODS ENOUGH TO SAVE A GAME."
(string 61). Y takes the gold at once; the save then raises `1186(A5)` by `6 * (level + 1)` (`$00b664`), so each further save costs more; the raise is undone
(`$00b676`) if the disk prompt is abandoned, **the gold is not refunded**.

- Price shown at levels 0, 1, 4, 9 with 1000 gold: 5, 55, 205, 455; formula 4 of 4 (`save_price.py`). Y: gold 1000 -> 995, 945, 795, 545; ESC at the disk prompt leaves the gold
  there (4 of 4) and the price back at the formula value.
- N leaves gold at 1000 and stores the floor 5 in `1186(A5)`.
- **The round trip works through the game's own disk code**: S, Y, key 1 pays 5 (gold 995, price 11 = 5 + 6), the game formats tracks and writes (prompts "FORMATTING TRACKS", "WRITING GAME
  TO DISK", plain ASCII at `$006406`/`$00642e`, with an English/French twin each), control returns to play; gold poked to 7, L and key 1 bring gold back to 995 and price to 11
  (`save_load_roundtrip.py`, on a scratch copy of the disk; the emulated drive keeps the data, the `.st` file is not written back: `cmp` 0 bytes).
- The save starts with the bytes `"DAC"` and the level (`$44414320` with its low byte replaced by `2524(A5)`, `$00b758`; the restore compares it at `$00b906`), then resource types 3, 4, 5, 8, 6 serialised by `$00c9c2` (restored by `$00c9ee`), then `$564` bytes from `1128(A5)` (gold, price,
  health, XP and the rest of the global state all sit in that block: `$00b758`-`$00b78e`, *read* plus the round trip above). The prompt warns "ALL NON GAME DATA WILL BE LOST": the
  save disk is reformatted.
- This finally explains string 59 "IM AFRAID YOU DIED. THE GODS DEMAND A PRICE TO SAVE YOUR POSITION": dying leads to the same price prompt (*read*: not driven).

## The stats scroll and the rank table

Using a class-7 object (byte `template+22 = 7`; type-6 ids 28, 319 and 420 are the templates with it) opens the scroll at `$00a29c`: HEALTH `1174(A5)` OF `2516(A5)` (current of maximum; a level (re)start sets the
current to two thirds of the maximum, `$006950`-`$00695e`, so the README's and item 10's "2516(A5) day counter" reading is retired: it is maximum health, 100 in this snapshot), GOLD
`1188(A5)`, XP `1192(A5)`, LEVEL `2524 + 1`, COMPLETE n OF 100 (`rooms entered * 25600 / (2510(A5) - word 5 of the overlay header) >> 8`, read), and a rank title.

The rank table is at `(A5)+176` (`$078756`): 20 records of 6 bytes, `[word string index][long XP threshold]`; the title is the first record whose threshold exceeds the XP
(`$00a38a`-`$00a3a0`). Thresholds 1000, 2000, 3000, 4000, 5000, 6500, 8000, 10000, 12000, 14000, 16000, 19000, 22000, 25000, 30000, 35000, 40000, 45000, 50000, 60000 give PEASANT, NOVICE,
INITIATE, ROGUE, TRACKER, PATHFINDER, SCOUT, RANGER, HUNTER, KILLER, BUTCHER, CUT THROAT, ASSASSIN, CHIEF, MASTER, GRAND MASTER, LORD, HIGH LORD, DEMI GOD, GOD (strings 63-82). **Two defects, both
proven**: the table has no terminator, so any XP of 60,000 or more walks into the bytes after it (the ASCII stamp `881990`, below) and reads index `$3838` = 14392, which decodes
to "DOOR"; and string 83, "BITMAP BROTHER", the obvious top rank, is referenced by nothing (no code literal, no record). `rank_table.py` pokes XP and patches a call of the scroll
(`lea <class-7 template>,A2 / jsr $00a29c`) and reads the index at `$00a3a0`: 12 of 12 match the table (0 and 999 PEASANT, 1000 and 1999 NOVICE, 2000 INITIATE, 12345 KILLER, 49999 DEMI GOD,
50000 and 59999 GOD, 60000, 65000 and 1,000,000 index 14392); the rendered scroll at 65000 reads "LEVEL DOOR" (`render_buffer.py`). Whether 60,000 XP is reachable was not checked.

## The text

All the game's prose is one packed table: `(A5)+168` ($075876) word offsets into the 6-bit stream at `(A5)+172` ($076046), decoded through the character map at `$005ac0`
(`py/name_strings.py`, `text_atlas.py` prints every primary message). Indices 390 and up are a repeating `DOOR` then zero padding. Layout by index:

| indices | content |
|---|---|
| 0-62 | interface messages (door, search, potion and weapon descriptions, save and death prompts); 4-12, 19-20, 25, 31, 38, 46, 48, 54-58, 60 have no code literal (`msg_refs.py`): composite pieces chosen by the description builder `$011066`, or unused; 54-58 duplicate the plain-ASCII disk prompts |
| 63-83 | the 20 rank titles and "BITMAP BROTHER" (83, unreferenced) |
| 84-126 | the 27 spell names (84-109, id order `(A5)+108`) and 18 potion names (110-126 plus 31 STAMINA, `(A5)+112`; potion 5's name is a single space) |
| 127-180 | room names: HALL, KITCHEN, BEDROOM, CHAMBER, TUNNEL, CAVERN, CHAPEL, PASSAGE, BARRACK, LIBRARY, GAOL, DUNGEON, STORE, SHRINE, CELLAR, TREASURY, CRYPT, SECRET, KINGS, MAIN, ... (room record word 24 plus byte 26, `$00eb4a`) |
| 181-244 | object names (STONE BAG ... DIARY, BLOCK; LEVER is 200, BOAT 188, PICKAXE 197, SCONCE 224, GIANT RAT 226) |
| 245-388 | what objects say when examined: lore, hints, jokes |
| 389 | the named-copy notice (below) |

**What the lore and hints give away.** The story: Lord Carolus's soul, King Wulf III's treasury, the Chief Alchemist Ragnar, Wrath Helland the dwarf architect, Kazak's golden funerary coin, the
Keeper of the Doors' diary, Yorgan's failed diary (string 343-348: the worm that regenerates, the jumping creatures, "DISCOVERED THE COMBINATION", the dragon). The puzzle hints are plain:
"MOST SKULLS WILL HELP YOU COMBAT THE SPINE CREATURE" (272, the creature mechanics.md 67 found), "THE ESCAPE NUMBER STARTS WITH 1" (273; the word 273 sits at template offsets 54-66 of six type-6 objects, ids 237, 285, 443, 446, 448, 485, *inferred* to be the carriers),
"A FRUITY LITTLE NUMBER FROM THE CORG REGION ... A 1044 IF IM NOT MISTAKEN" (275): the four digit escape number is 1044 (*inferred* from the two hints; the lock that takes it was not found), "THE
CROWN OF THE KINGS WILL ALLOW PASSAGE TO THE WORLD ABOVE" (369), "YOU MAY NOT PASS WITHOUT THE KINGS CROWN" (379), "PURIFICATION IS PERFORMED BY ADDING HOLY WATER TO A BLESSED BOWL" (359), "MY LORD,
ENTER YOUR SECRET ROOM BY THE USUAL MEANS FROM THE PURIFICATORY, BUT THRICE ONLY" (302), "WE HAVE HIDDEN THE GEM BENEATH THE SACKS" (315), "MY LORD, YOUR CURE POTION I HAVE HIDDEN IN THE COMMON
CRYPT, THE STONES BEING THE KEY" (361), "THEY WILL NEVER THINK TO COOL THE FLAMES" (280), "FREE THE SOUL OF KAZAH WITH A GOLDEN COIN" (267, "KAZAH" here and "KAZAK" elsewhere).

**Leftover developer and production text** (all in the string table, none shown by any code literal):
- 376, directly after the flask's "A REFRESHING SMELL ISSUES FORTH": "THINGS NOT COMPLETE ARE ... ENHANCED SOUND FOR 1MEG, TITLE AND INBETWEEN SECTION SCREENS." A to-do note left in a flask description; the
  release has no enhanced sound path found so far (see the sound section).
- 380: "CADAVER, COPYRIGHT 1990 THE BITMAP BROTHERS. JOHN NORLEDGE SHOW COPY 2." and 389: "PLEASE DO NOT MAKE ANY COPIES OF THIS DISK. EACH COPY IS SPECIALLY MADE FOR THE NAMED PERSON. IF YOU NEED
  ANOTHER COPY, OR YOU NEED HELP, CONTACT STEVE AT BITMAP OFFICE ON LONDON 071 702 3643 OR 4." Together these read as the named-copy notice of a press or show master (*inferred*: the crack's source
  disk carried it); nothing in the code compares the name.
- 372: "THE BOTTLE IS EMBOSSED WITH THE LETTERS N.I.K.E." (an in-joke: 'N.I.K.E.' is unexplained).
- The tag `881990` + NUL is the level directory's header (next section), held in RAM at `$0787ce` (right after the rank table) and `$028c00`; the five words after it read as a build date and time.
- Typos shipped as is: POISION (strings 30, 45), SOMTHING, WARRIOUR, DISPELL, DOSNT, SEERING, PURIFICTION, FUNGHI; the French prompts are garbled in places ("DANS LE LECTEUR" prints as DANE LE LEITEUR, "NIVEAUX" as NIUEAUX, "OU SUR ESC" as OU SURESS), cause unknown.
- Only English and French text exists (plain-ASCII prompt pairs at `$006280`-`$0067a0`); "3 DEUTSCH" on the language screen, which is a bitmap, has no German text behind it on this disk (0 hits
  for SPIEL, LADEN, DISKETTE, SPEICHER). What choice 3 selects was not tested.

## The assert layer

The engine checks itself: `$011788` clears the top of the screen, prints a message at line 0 and "CONTACT STEVE OR MIKE AT HQ" (`$0117d0`) at line 10 and spins forever in `bra $0117c4`. It has
**67 call sites** (`assert_sites.py`; each preceded by `lea <message>,A0`, the messages are the plain ASCII block `$0172c8`-`$017951`). Forced live by patching a `jsr $011788` over the instruction at the
PC: the screen shows the contact line, the main loop gets 0 hits and the spin loop 196,092 of 200,000 (`fatal_screen.py`, `fatal_error_screen.png`). The messages are a map of what the programmers expected to go wrong:
the event stack (`$007152`, `$00744c`), doors and rooms (`DOOR ERROR`, `BOTH ROOMS BLOCKED`, `INIT ROOM ERROR`, `LOAD LEVEL ERR`, `CANT SAVE GAME`), the heap and the sort lists (`EXCEEDED MAXIMUM HEAP SIZE`,
`CANT FIND A SPACE CSORT`, `NO ROOM IN SORT LIST`, `EXCEEDED COLLISION CHECK LIST`), the rucksack (`NO SPACE IN RUCK`, `OBJECT NOT IN RUCKSACK`, `SEVEN OR OVER ICONS`), creatures
(`TOO MANY CREATURES IN ROOM`, `NOT FOUND CREATURE TO DELETE`) and one `... NON-EXISTANT OBJECT` per object verb (KILLING, UNINV, WAKING, SLEEPING, GOANI, STOPANI, LOCKING, UNLOCKING, MOVEING,
GOMOVE, STOPMOVE, GOACTI, UNLOCK/UNTRAP/CLEAR CHEST, DIRTY POTION, ...): the verb block's own names, which §64's dispatch map used.

Three are *unfinished features* the release would crash on if ever reached (*read*, none hit in any run):
`LIMB CODE NOT WRITTEN` (`$00bffa`, `$00c01c`, inside the window/sprite compositor `$00bfb0`: limb codes 1 and 2 are implemented, 0 and 3 or more are fatal),
`SET ACTION NOT WRITTEN` (`$010438`; the message of the verb at `$010410`, which is really the level-start verb: operands 0-9 store operand + 1 into the level byte `2524(A5)`, set `2518(A5) = $ff` and `2525(A5) = 1` and `jmp $006890`; driving it loaded the one-disk image's second level, next sections; only operands above 9 reach the message), and `ELSE SHOULDNT BE CALLED` (`$0106b4`, a verb slot that the script's own IF skipper
should have consumed).

## The level code overlay and its engine export table

Each level carries **native 68000 code**. The loader (`$00b5a8`-`$00b5f4`) depacks pair 0 of the level's directory record (`252(A5) + 16 + 20 * level`) and copies it to the buffer at `2534(A5)` (`$04c65e`; the field is static data, no code writes it), then sets `392(A5)` to the engine export table
(`move.l #$6082,392(A5)` at `$00b5ec`). The one-disk overlays are `$c0c` (level 0) and `$b4c` (level 1) bytes, `$04c65e`-`$04d26a` for level 0; everything above that in the old listings was stale RAM (the loader's raw-read buffer `44(A5)` = `$04d65e`). `extract_overlay.py`'s Python LZHUF gives 3084 of 3084 bytes equal to RAM;
the game's own `$0154b0` read of sectors 401-405 and `$0118ec` expand reproduce it (2560 of 2560 and 3088 of 3088 bytes). Seven overlays are decoded (two on the one-disk image, five on the two-disk Level disk, whose overlays have two more header words each); the game logic is shared: 17 of 18 potion routine heads and 29 of 31 spell heads are identical in all 7 decoded overlays.

**Header** (big-endian words from the base): +0 `$50` record 0, the level-init hook (called through `$00e298` with D0 = 0 from `$00b5e6`; a bare `rts` in both one-disk levels); +2 table 1, **potion effects** (18 entries, index = potion id); +4 table 2, **spell effects** (31 entries, ids 0-30); +6 table 3, **timer-expiry handlers** (52 slots, live ids 0-7 and 32-40; the others point at the table itself and never run); +8 list 4, 17 `(key, value)` word pairs ending `$ffff`
(the save serializer `$00e53c`/`$00e554` and the level-change verb use it; level 0's pairs are (82,726), (460,487), (141,814), (140,564), (282,607), (87,812), (461,608), (27,656), (161,669), (256,815), (304,790), (116,584), (450,816), (12,596), (482,680), (5,101), (132,813); *inferred*: key = object id in this level, value = object id in the next level; id 5 is DIARY in CAVERN); +10 the constant 2, the completion-percentage offset (`$00a346`: rooms entered * 100 / (`2510(A5)` = 72 - 2)). Words +12 to +39 are seven unused `(ffff, 0000)` records; from +40, records 10-19 are **creature classes 1-10**: word one the per-frame behaviour routine, word two the class's event table. Class modules are length-word prefixed.

**Dispatch sites** (each proven live; scripts `timers_live.py`, `classes_live.py`, `events_live.py`, `flags_live.py`, `potions_callcap.py` in the agent directory):

| site | role | proof |
|---|---|---|
| `$00904e` | timer tick (17-frame prescaler `2460(A5)`; active list `2412(A5)`, count `2307(A5)`, countdown `2308(A5)+id`, reload `2360(A5)+id`; a non-zero countdown after the handler re-arms it) | all 17 live ids: handler 1 hit, dispatch 1 hit, slot cleared: 17 of 17 |
| `$00e25c`-`$00e28c` | per-frame creature loop over `396(A5)` (filled by export service 22): runs record (class byte `1(A2)`) + 9 through `$00e298` | classes 1-10: 5 hits in 120,000 steps each, 10 of 10; class 0 none |
| `$00e218`-`$00e24e` | event list `1266(A5)` (count `1264(A5)`), records `[type][sub][object ptr]`, routine = word `2(A1, 4*(type+9))` then entry `sub` | events (4,0), (4,1), (7,0), (10,0): 4 of 4 |
| `$00a638` | potion use, into table 1 | `callcap`: 18 of 18 return with the expected deltas |
| `$00f0d4` | spell cast, into table 2 | real casts below |
| `$00fa72`, `$00fb60` | projectile-hit paths into table 2 | not driven |

Class behaviours, read at call level only (*inferred*): class 1 a hopping chaser (jump arc table `$4d1b2`), 2 a shooter with a cooldown (`9(A2)`/`10(A2)`), 4 a turret (event 0 picks one of 3 facings, event 1 fires), 6 a burst-speed chaser, 10's event a lightning trap (white flash plus 20 damage unless MAGIC SHIELD is set); classes 7 and 10 carry a bare `rts` behaviour. The FREEZE flag `2342(A5)` gates the creature pass (poked: class-2 hits 10 to 0) and `2467(A5)` (SLOW) halves it (10 to 5). The timer countdown byte doubles as the engine's flag: `2340`, `2342`, `2345`, `2346`, `2347` are read by movement, animation and steering code.

**Spells (table 2), each read from its body.** "Real cast" means the game's own fire path (`$006faa`, `$00f02e`, `$00f0e4`) with a scroll poked together and the overlay entry hit; other rows were driven by `callcap` with the register convention read off the bodies (A2 = scroll instance, spell id +0, power +1; A1 = target; A4 = victim template; A3 = victim data; *inferred*, not seen at a real call).

| id | spell | routine | effect | status |
|---|---|---|---|---|
| 0 | MAGIC MISSILE | `$4cd94` | victim must be class 3: HP -= attacker's power (instance +1), queues a kill (op `$17`) on underflow, white flash | implemented: HP 10 -> 7; HP 2 -> `$ff` + one kill |
| 1 | MASSACRE | `$4cde0` | full-screen effect (service 6), then kills for up to power creatures of `396(A5)` | implemented: 2 kills queued |
| 2 | FREEZE | `$4ce36` | timer 34 (duration = power); sets `2342(A5)` | real cast: `2342 = $0a` |
| 3, 17, 23, 24, 27, 29 | READ LANGUAGE, TALK WITH DEAD, SLEEP, DISPELL MAGIC, (27), (29) | `$4ce44` | grey flash (service 10) only | stubs |
| 4 | MAP | `$4ce4c` | `2466(A5) = $81`; the main loop then draws the map (`$00a9a8`) in all-rooms mode | real cast: hits `$00f0e4`, `$04ce4c`; F1 shows one room, MAP the whole world graph (`map_f1.png`, `map_spell.png`) |
| 5 | MIND BLAST | `$4ce54` | service 6, then HP -= power on each listed creature, kill on underflow | implemented: 10 -> 6, 26 -> 22 |
| 6 | TRANSPORTER | `$4ceac` | bare `rts` | **no-op** |
| 7 | UNLOCK CHEST | `$4ceae` | class 8, bits 0 and 6 of `4(A3)` clear: clears the lock word and bit 1, touch (service 14) | implemented |
| 8 | UNLOCK DOOR | `$4ceea` | door bit 5 of `7(A4)` clear: clears `2(A4)` and bit 6, message 1 | implemented; refused when bit 5 is set |
| 9 | DESTROY | `$4cf08` | service 15 on the id at `4(A1)`, grey flash | implemented: removal list `1386(A5)` + 1 |
| 10 | BLESS WEAPON | `$4cf18` | adds power to the linked object's instance +1 (no cap), message `$20`; if `2(A3) != 0` message `$21` then `divu #0` (vector 5 = TOS `rte`: an assertion marker); bit-7 classes: `1(A3)` += power, cap `$ff` | implemented |
| 11 | SLOW CREATURE | `$4cf74` | `2467(A5) = 1`, timer 36 | real cast |
| 12 | DUPLICATE | `$4cf80` | bare `rts` | **no-op** |
| 13, 14 | BLESS MAGIC, BLESS POTION | `$4cf82`/`$4cf88` | class 1 or 2: `1(A3)` += power, cap `$ff` (wrong class: message `$2f`) | implemented: `$64` -> `$6e`, `$fa` -> `$ff` |
| 15 | DISPELL TRAP | `$4cfb2` | chest with `5(A3) != 0`: cleared, message `$34` | implemented |
| 16 | LOCK DOOR | `$4cfd4` | `2(A4) = $ffff`, bit 6, sound 18 | implemented |
| 18 | CONFUSION | `$4cff4` | timer 37; `2345(A5)` = random-direction flag in the steering routine `$4cab4` | real cast |
| 19 | PURIFY POTION | `$4cffa` | class 2: clears bit 2 of `3(A3)` (dirty), message `$24` | implemented |
| 20, 21 | READ MAGIC, LEARN POTION | `$4d01a`/`$4d03e` | class 1 (2): clears bits 0, 1, 7 of `3(A3)`, flash | implemented |
| 22 | TURN MONSTER | `$4d04a` | timer 38; `2346(A5)` reverses steering (flee) | real cast |
| 25, 26 | ENCHANT LIQUID, POLTERGIEST | `$4ce4a` | bare `rts` | **no-ops** |
| 28 | (unnamed) | `$4d050` | gate: class 1 and -power >= `(A3)`, else message `$2f`; a real creature-damage effect in the Disk 2 builds | gate here |
| 30 | (unnamed) | `$4ce3c` | white flash | stub |

So of the 27 named spells, **four do nothing** (TRANSPORTER, DUPLICATE, ENCHANT LIQUID, POLTERGIEST) and **six only flash** (READ LANGUAGE, TALK WITH DEAD, SLEEP, DISPELL MAGIC, and unnamed ids 27, 29: the last two are outside the name table); the other 17 do something. "Flash-first" spells cannot run to the end under `callcap` (the flashes wait on VBL with interrupts masked), so their effect code before the flash is what the delta shows.

**Potions (table 1, index = potion id, dispatch `$a638`):** STAMINA heals by `1(A1)`; CURE heals to half of max only when HP < 50 (20 -> 50 seen); SUICIDE (17) calls service 3 with `$8300` then waits in the game-over loop; SUPER FAST, GIANT JUMP, ALCOHOL, IMMORTAL, STRENGTH start timers 35, 33, 32, 39, 40; POISON sets `2434`; SHOT, FIRE, ICE and MAGIC SHIELD set bits 0-3 of `2436`, TOTAL SHIELD `$7f`; CURE POISON clears `2434`; WATER only prints; the blank potion 5 and SLOW are bare `rts`.
**Timers (table 3):** 0 poison end and 1 poison tick (self re-arming, started by verb 90), 2-5 clear shield bit n, 6 clears all shields, 7 increments `2299(A5)`, 32-40 the ends of ALCOHOL, GIANT JUMP, FREEZE, SUPER FAST, SLOW, CONFUSION, TURN, IMMORTAL, STRENGTH.

**The export table** (23 entries at `$006082` in this build, each entered through `$04caaa` with `D6 = 4 * n`; the two-disk build's table is `$005eee` with 29 entries, installed at `$00b822`; names from the bodies, checked with `callcap` where safe):

| n | address | service | n | address | service |
|---|---|---|---|---|---|
| 0 | `$c5a8` | RESOLVE(type D0, index D1) -> A0 | 12 | `$10d38` | START TIMER(D1 id, D0 duration) |
| 1 | `$1083e` | SPAWN (id from `(A1)+`, type-9 slot, spawn list `1466(A5)`) | 13 | `$c576` | RESOLVE type 2, 17-bit offset |
| 2 | `$c542` | RESOLVE-BY-SIGN(D1) | 14 | `$a494` | TOUCH/USE OBJECT |
| 3 | `$10c8c` | HP CHANGE(D0 signed): clamp to `2516(A5)`, death at <= 0, no-op when immortal | 15 | `$1007e` | DESTROY OBJECT(D3 id) |
| 4 | `$11356` | WAIT FRAME | 16 | `$11544` | **RANDOM(D1..D2)** |
| 5 | `$152e6` | RESTORE PALETTE (`$5a9c`) | 17 | `$f1ee` | LAUNCH PROJECTILE(A1, A2, D7 direction) |
| 6 | `$7804` | FULL-SCREEN EFFECT | 18 | `$158f8` | PLAY SOUND(D0) |
| 7 | `$153d2` | WHITE FLASH | 19 | `$b184` | REFRESH TOUCHED OBJECT |
| 8 | `$10974` | TELEPORT (room, x, y, facing from `(A1)+`; script verb 37) | 20 | `$101ae` | HIDE OBJECT(A0) |
| 9 | `$107e2` | PLACE OBJECT (*inferred*) | 21 | `$100b0` | SHOW OBJECT (id from `(A1)+`) |
| 10 | `$153c4` | GREY FLASH | 22 | `$e13e` | REGISTER CREATURE(D1): `396(A5)`, max 6 |
| 11 | `$a9a8` | MAP SCREEN | | | |

Services 1, 8, 9, 13, 19 were named from their bodies and not driven; the two-disk table adds 23 (wait for buttons released), 24-25 (set palette), 26 (status screen), 27 (fade), 28 (graphics helper). **No overlay calls service 8**: the teleport is reached only by object scripts (verb 37). Representative routines as pseudocode:

```
timer 1 ($4d0e6, poison tick):   D0 = 2434(A5); if D0 { 2309(A5) = $ff; svc3 hp_change(-D0) }      // re-armed from reload 2361
spell 0 MAGIC MISSILE ($4cd94):  v = live record of A4; if class(v) != 3 goto end
                                 hp = A4.inst[0]; if A4.inst[6].bit0 goto end (invulnerable)
                                 hp -= atk.inst[1]; if borrow: queue_kill(A4)
                          end:   svc7 white_flash()
potion 1 SUPER FAST ($4cc9e):    2279 = 2280 = 2; svc12 start_timer(35, 1(A1))
event class 4 sub 1 ($4c7c0):    D7 = 9(A2); ...; $4c8d8: 348(A5) = A0; resolve id 2(A2); svc17 launch_projectile(D7); svc18 play_sound(35)
event class 10 sub 0 ($4c856):   svc7 white_flash(); if 2436.bit3 { msg $31 } else svc3 hp_change(-20)
```

## Object scripts: who runs the verb interpreter

### How the script system fits together

The game has three separate mechanisms that look like scripting, and only one is a script language for game logic. The 17-opcode bytecode at `$15c70` is the sound sequencer (below, "The sound engine"). Creature behaviour, spells, potions and timer handlers are native 68000 code in the level overlay, entered through its header tables and the engine export table ("The level code overlay"). The object verb scripts are the third: a small event-driven language that carries the puzzle layer (levers, the treasury gate, gold piles, hazards, teleporters, the level-1 load, the message text). The scripts do not implement rules such as combat or spells; they call the same engine services the overlay does, and reach the overlay's creature-class handlers only by writing events into the queue below.

A script is data on a type-6 object template. The template holds one or two lists of blocks; a block names the event it answers and holds a straight-line body of verbs (174 of the 1000 level-0 objects carry one, 220 of level 1). Nothing polls objects and there is no per-object interpreter state. Engine code, timer expiries and the player's own commands push events, `[opcode][object ptr][word]`, onto one 200-entry ring queue at `304(A5)`; the consumer `$00fdbc` drains it every frame. For each entry it takes the target object's block list and looks for a block whose event byte equals the low byte of the opcode (bit 14 of the opcode selects the second list, bit 15 adds a fourth longword to the entry). A matching block first runs its event's gate, which reads operand bytes from the script and compares them with what caused the event (for example the id of the object that touched it), and only then executes its verbs through the 94-entry table at `$00ffba`.

A block runs to completion inside one consumer call: there are no loops, calls or yields (the message verb fades, prints and waits inside its handler, which is the only pause seen). All state that survives between events lives outside the script: the object's state bits, the type-4 flags (doors and levers), the script variables at `2282(A5)`, the type-8 list (what the player holds), gold, XP and health, and the timers. Conditions are not expressions: each condition verb adds one to a counter that a run clears on failure, and a structured `IF ... [ELSE ...]` tests the counter. A block without the keep bit rewrites its own event byte to `$ff` after its first run, which is how a one-shot lever stays used.

Scripts influence each other only through the queue. KILL queues event 23 for the target, verb 9 queues event 19, PUT IN RUCK (verb 35) queues event 0, and verb 66 writes `[type][sub][object]` records into the list `1266(A5)` that the overlay's creature-class event tables consume (`$00e218`). The path a lever takes is therefore: the player's operate icon (icon 7) queues event 5 for it (live, table below), the consumer finds its block, the gate passes, the verbs toggle its state bit, play a sound and teleport (verb 37 into export service 8), and the room change happens inside that one call (from the consumer on, proven live for objects 2, 86 and 144).

**Who pushes events** (`py/secrets/overlay/queue_producers.py`: a static scan of the whole image, 48 push sites, 25 distinct events; the player-action rows were then driven live with natural joystick and key input, `overlay/action/action_survey.py`, 3 of 3 fresh runs each; the other rows are *inferred* from the producer bodies):

| event | producers | reading |
|---|---|---|
| 0 | `$00a184` in icon 2 TAKE (`$00a136`); verb 35 (`$010816`) | the object is taken into the rucksack. Live: coin 412, pickaxe 168, diary 5. The push follows `$00c30e` (unlink from the room) and `$00c42a` (append to the type-8 list); the object's own event-0 block then runs (the coin's: `GOLD += 7`, delete self) |
| 16 | `$00a418` in `$00a3d0` (icon `$b`, EXAMINE), taken when the template's byte 3 bit 5 is set; otherwise a generic banner and no push | examine. Live: coin 412, pickaxe 168, boat 257 (their blocks run); the barrel has no bit 5 and pushes nothing |
| 5 | `$00a486` (the shared path `$00a474`, reached from icon 8 READ `$00a292` and icon 7 `$00a448`), `$00a5d2` (icon 9, `$00a5c0`), `$00a59c` (icon 3, `$00a494`, follows a toggle of state bit 0 and sound `$38`), `$00a7ce` (icon `$e`, `$00a7b4`) | the object's own action icon: read a book, operate a lever, use a barrel. Live: BOOK 488 and TOME 510 (icon 8), TUNNEL lever 144 (icon 7: consumer `$00fe24` 1 hit, `$00fe5a` 2 hits), barrel 60 (icon 9, no block). Icons 3 and `$e` need a subclass-5 chest or a template with byte 29 = `$12`, not reachable from CAVERN: *read* |
| 27 | `$00a72e` in icon `$d`, SELECT (`$00a70e`); `1262(A5)` is written at `$00a73a` right after | the held rucksack item is selected. Live: Space with the pickaxe: event 27 for 168, `1262(A5)` = `$00a8` |
| 18 | `$00a6f4` in icon `$c` (`$00a682`), after a free-slot check (`$00a702` shows message 27 when there is none) | *the held item applied to or put into the object in front*, not a pick-up (that is event 0). The word is the item id. Reached only with the class byte poked to `$b` or 8 (no such object in CAVERN or TUNNEL): with class 8 and a free instance slot `$00a6a6` writes the item id into the container's first instance word and the item leaves the rucksack |
| 26 | `$00a7a4` in icon `$f` (`$00a782`) | an item given to a class-`$c` object. Reached only with the class byte poked to `$c`: the item leaves the type-8 list |
| 9, 7 | `$0095c0` and `$0095d8` in `$009440`, every frame that builds the icon list for the object in front; event 9 also at `$008a34` and `$008a68` in the movement collision test, six sites in `$00edb8`-`$00f396` and one in the main-loop key handler (`$006dc6`), unread | proximity. Live: while the hero faces an object both are pushed every frame (12 of 12 frames at the coin, 13 of 13 at the lever, 0 in open floor, 3 runs each); these are the level-0 event-7 scripts and the hazards' event-9 gate |
| 23 | `$00fb24`, verb 50 (`$01036c`), overlay code (`$04c89a`, `$04cdd2`, `$04ce24`, `$04cea0`) | an object or creature is killed |
| 19 | verb 9 (`$010c66`), queued for the ROOM record | script-raised room event |
| 20 | the room countdown of verb 42 (`$4014`, `$0090dc`) | room event on expiry |
| 28 | `$00e8a6` in the room loader `$00e854`, guarded by `bset #6,23(A0)` (`$00e898`), with the rooms-entered counter `2118(A5)` | **first entry into a room**, queued for that room (`$401c`). Live (`room_events_live.py entry`, rooms 4 and 28 entered by injected teleports): `$00e8a6` 1, 1, 0, 0 over four entries; room 28's event-28 block ran verb 36 three times on the first entry and never again; `2118(A5)` moved 1 to 2 to 3 to 3 |
| 6 | `$00eae4` (after `movea.l 164(A5),A1`, `$00eace`) | **every room entry**, queued for the current room (`$4006`). Live: 1, 1, 1, 1 over the same four entries; room 28's keep block (verb 21) ran 1, 0, 1, 0 times (room 4 has none); room 37's non-keep block paid 26 XP on the first entry (0 to 26) and nothing on the second, the consumer's gate hitting 2 then 1 |
| 14 | `$0090aa` in the timer service (`$009070`-`$0090e8`) | **room tick**: `2458(A5)` and `2459(A5)` are loaded from room byte 2 at entry (`$00e88c`), `$00908e` counts `2459` down once per timer pass and at 0 reloads it and queues `$400e`. Live (`tick`, CAVERN, byte 2 = 15): 34 passes, 2 pushes and verb 36 twice in 14,000,000 steps |
| 15, 17 | `$0092b4`, `$0092da` in the region test `$009160`-`$0092e6` (loop `$0090ec`-`$00915a`, taken when room byte 23 bit 1 is set) | **an object overlaps region D7 (1 to 4) of the room's region list**; D7 is the gate byte, event 15 when the overlapping record's word `4(A1)` is 0 (inferred: the hero), else 17 (`$c00f`, `$c011`), only for rooms with byte 23 bit 4. Structure proven statically (`room_regions.py`: 64 of 64 gates in 1..N) and the overlap driven live in CAVERN (`room_regions_live.py`, "Room scripts" below): event 15 for the hero by natural input (3 pushes, 3 health), event 17 for a poked object (1 push, 1 PLACE); an injected event 15 also ran room 4's and room 28's TELEPORT blocks. The same test queues event 10 for the object (`$009286`), which no block answers |
| 24 | `$00f0a0` in the cast of the selected item (`$00f030`, `1262(A5)`) | a spell is cast in the current room, word = the spell id at `(A2)`; queues event 25 for the item at `$00f0c8`. **Live** (`cast_sleep_live.py`): a real SLEEP cast in level 1 room 1 pushes event 24 once (`$00f0a0`), the consumer runs the room's block (XP 0 to 26, object 659's record byte 3 0 to 1, three creature records queued at `1266(A5)`), and the control without fire reads 0 on all of them; the gate values match the spell table (`2` FREEZE in level 1 room 45, `$17` SLEEP in six rooms) |
| 1, 4, 10-13, 25 | `$00a114` and `$00fa62`, `$00f328`, `$009286`, `$00f69c`, `$00f9a2`, `$00b0f0`, `$00f0c8` | not read (no room block and only a few object blocks answer them) |
| 8 | `$00733c`, `$00df14`, `$00e196`, `$04cc52` | not a script event: the name-banner request (mechanics.md §18, `$00ffa4`) |

The object blocks of both levels answer events 0, 3, 4, 5, 7, 9, 11, 12, 13, 16, 18, 21, 23 and 27; the room blocks answer 6, 14, 15, 17, 19, 20, 24 and 28. **Events 3 and 21 have no producer.** `overlay/action/event_3_21_static.py` scans 11 listings (the resident image, both level overlays, and every disk-1 and Disk 2 overlay `.lst`): every push writes an immediate opcode (48 sites in CAVERN, 47 in level 1, the overlays only 5, 8 and 23) and there is no computed-opcode push, so the events pushed are exactly 0, 1, 4-20 and 23-28. The blocks for event 3 (the hazards 114, 115, 117, 120) and event 21 (one level-1 block) are therefore *inferred* dead script content, unless the ring is written by a route that is not a `movea.l 304(A5),A0` sequence.

### The player's action panel (driven live)

The inputs reach the events above through one panel (`panel_coin.png`: the icon panel with the silver coin in front of the hero). **Joystick-1 fire (state bit 7) next to an object**: the main loop's movement code `$006e44` reaches `$00737a`, which probes one step ahead along the facing vector (table `$5bea`); `$008870` finds the object and `$009440` builds the icon list at `$5ff6` for it; `$00954a` sends bit 7 of `2243` to `$0095ea` and the icon-choice loop `$009c82`, which returns the chosen icon id, and `bsr $00a08c` dispatches through the word table at `$00a0ac` with A1 = the object's type-6 record and A2 = its class template. The loop first waits for the joystick to release (`$0118ac`), so fire must be released and pressed again to confirm; in the object panel the cancel box is skipped by right and left, Space cancels (`$00a134`), and moving the cursor needs a pulse of at least one loop pass (about 12,500 steps). **Space or Return**: `$006c28` calls `$011898` first, which waits for the key to *release*, so the action runs on the break and a key held forever does nothing; then `$006cce` (`moveq #21`, sound) and `$009682`, which returns at once when the rucksack count `2438(A5)` is 0 (live: `$009682` hit, `$009724` not) and otherwise selects the held item (`$009724`), builds its icons (`$009f02`) and runs `$009c82`. Space clears bit 1 of `2519(A5)` so the item's icon panel opens directly; Return leaves it set, so the rucksack grid `$0097b4` comes first and fire in the grid confirms the item. Down (`2474(A5)` bit 0) is only a flag, not a panel key.

Icon handlers (`$00a0ac`, live where marked): 1 `$00a1e0` drop; 2 `$00a136` TAKE (event 0); 3 `$00a494`; 4 `$00a43c`; 5 `$00a1c6`; 6 `$00a134` cancel; 7 `$00a448` (operate, event 5); 8 `$00a292` (read: event 5 through `$00a474`, or the stats window for a class-7 diary); 9 `$00a5c0` (event 5); `$a` `$00a66a` (pushes nothing); `$b` `$00a3d0` EXAMINE (event 16); `$c` `$00a682` (event 18); `$d` `$00a70e` SELECT (event 27); `$e` `$00a7b4`; `$f` `$00a782` (event 26). The icons an object offers come from the table `$005c1c` indexed by class-template byte 23 (subclass 1 gives 4, 2 gives 9, 4 gives 7, 5 gives 3, 6 gives 8) plus fixed ones: the coin and pickaxe show 2, `$a`, `$b`; a book or tome 8; the lever 7 and `$b`; the barrel 9, `$a`, `$b`; the boat only `$b`. Icon `$c` shows for class `$b`, or class 8 with instance flags 4 and 0; icon `$f` for class `$c`; `overlay/action/class_census.py` puts class 8 on 13 placed objects in other rooms (ids 83, 224, 72, 35, 475, 478, 483 and more) and class `$c` on id 70.

**What a pick-up writes** (`overlay/action/pickup_write.py`, a `watch` on the pickaxe): icon 2 runs `$00a136`, `bsr $00c30e` (unlink from the room, a shared list shift that touches the same bytes first), `bsr $00c42a` and then the event-0 push. `$00c42a` puts the record `[object id][template +6, the class-template id]` at the next 4-byte slot of the type-8 data (`$00c4cc move.w D3,(A3)`, `$00c4d4 move.w 6(A0),2(A3)`: the pickaxe gives `(168, $20)` at `$07550a`, the coin `(412, 54)`, the diary `(5, $78)`), rewrites the 64 index words at `$04c536` (`$00c4fe`-`$00c516`) and adds one to `2438(A5)` (`$00c4da`). The type-8 descriptor is `96(A5) + 8*$12` = `$04a4f6`. The coin's event-0 block deletes it again at once through `$00c3d4`, which is why gold rises by 7 and the count returns to 0. Fire with an item selected and nothing in front is a drop or throw (`$006f48`, `$00a19e`, `$00a1ea`, `$00f44a`, `$00c3d4`: count 1 to 0, selection cleared).

**Negative controls**, each with a signal that the input was read (`negatives.py`): fire with nothing in front hits `$006e70`, `$006f28`, `$006f62`, `$00737a` and never `$009c82`; Return and Space with an empty rucksack hit `$006cce` and `$009682` and stop; Down next to the coin hits `$006cb0` and never opens the panel; Space in the object panel cancels through `$00a134`. **Not run naturally**: events 18 and 26 (the class byte of the TUNNEL lever's live record, `$059910` + 22, was poked to `$b`, `$c` or 8, everything else natural input; `poke_classes.py`, `poke_class8.py`), and icons 3 and `$e`. Walking to a class-8 chest (id 83, 224) would remove the poke.

**The regalia walk** (`overlay/action/regalia_walk.py full`; two runs with byte-identical snapshots and logs). The four regalia and the BUTTON that asks for them all sit in the south-west cluster, far from CAVERN (world rows 49 to 59 against CAVERN's 18 to 28): room 33 (`$21`) holds the objects 26 ("IT SEEMS WELL WROUGHT"), 16 (the breastplate of WULF III), 32 ("RINGED WITH A THIN CIRCLET OF GOLD") and 28 (the shield "OF THE KING"), plus two decoys with their own examine text, 25 (a helm "OF A LORD") and 29 (the heraldry "OF LORD CAROLUS"), the large object 31 (examine only), 432 and 499; room 34 (`$22`) holds the BUTTON. Only the entry is injected (a scratch `37 21 4 4 0` written over LEVER 86's block, so the BUTTON's own script stays intact); everything after is joystick input.  **Floor regalia**: a breadth-first search over walk-to-stall holds whose goal test is the fire probe (opens `$009c82` when an object is in front; the result is its id and icon list). From the state after taking 32, `DUL` reaches 28, `UR` 16 and `RUL` 26, each offered icon 2, and each TAKE (open the panel, icon 2, fire) runs `$00a136`, `$00c42a`, `$00a184` once and raises the rucksack count `2438(A5)` by one. The decoys 25 and 29 and object 499 offer icon 2 too, so the choice of four among six is the puzzle.  **The circlet (32) is reached by a jump.** It rests on top of the large object 31: placement table `56(A5)` (stride `$46`, rectangle at +0, z top/bottom at +4/+5) gives 31 a z span of 0 to 17 over x 44-55, y 8-31 and 32 a z span of 18 to 31 over x 47-50, y 20-22, and the collision scan `$008870` lists an object only when its z span meets the hero's `[D2, D2+h-1]`, so a hero on the floor never overlaps 32 and the fire probe facing 31 returns 31 (the earlier walk searches all did). Holding fire with nothing in front starts a jump instead of a probe: with fire held and an object in front, `$006e64` reaches the probe `$00737a`; with none, `$006f80` sets the move state `2266(A5)` to 5 (*read*, not hit-counted) and the per-frame update at `$0070da` adds the step to the hero's x, y and z (the z-writer, `watch` on `$03833c`, live: `$0070e8`/`$0070ec`, base 5, 10, 14, 18, ... to a peak of 34 over about 50,000 steps, then back down; the arc starts about 55,000 steps after the fire press and keeps running after fire is released). From the stall against 31 (x lead 43) walk left 60,000 steps, hold fire+right for 300,000 steps and then right alone: the hero crosses 31's edge at z base 22 to 34, lands on 31 at z base 18 (top 47, x 49-55) and `U` stalls at y 9-15 with 32 in front: the probe returns 32 with icons 2, 10, 11, 6, and TAKE leaves type-8 record (32, 22) (`jump_onto_31`; the same jump from the stall itself only opens the panel for 31, because fire with 31 in front is the probe). Taking 32 first and the others after gives rucksack records (28,21), (16,16), (26,20) on top. Climbing 31 by walking is not possible: `$006e90`-`$006eb0` offers the step-up only when bit 3 of the blocker's template byte 12 is set (31's is 0; no object in room 33 has it).  **The BUTTON, natural**: from room 33's state after the four takes, `LDLUR` (`D` into room 32 and `L` into room 34 as before) puts the BUTTON in front with icons 4, 11, 6; icon 4 is `$00a43c` and reaches the shared push `$00a486` (event 5); the consumer then runs the four verb-34 tests (all pass, with no poke now), verb 58, sound `$3a` (verb 70), the teleport (verb 37, `$00e854` once) and four verb-41 placements, the hero enters room 37 (`$25`) and its event-6 block pays 26 XP (0 to 26): the whole path from input to room change to reward with real joystick input except the one injected entry.

**The interpreter's caller is the ring-304 queue consumer `$00fdbc`** (cadaver.md's open item 1, closed). Queue entries `[opcode.w][object ptr.l][word]` are read from `152(A5)` (count `1154(A5)`); the injected event of the live proofs is opcode 5 (see the table above for what queues it in play). For the object the consumer walks its script blocks, `[len][event | $80 = keep][verb bytes ... $17]` (`len` counts itself; blocks start at template +`$10`, count at +11, or at +`$20`, count at +31, when opcode bit 14 is set); when the opcode equals a block's event byte it runs the gate from the table at `$00fe84` and then executes the verb bytes through the **verb table at `$00ffba`, which has 94 entries**
(its first word `$bc` is its size in bytes; it ends exactly where `$010076` begins; dump `verb_table94.txt`). The "59-entry table at `$010000`" of mechanics.md §23a, §24, §64 and §69 was read from the wrong base: it is the last 59 entries with every target off by `$46`, which explains every "mid-instruction landing" of §64d, and its ids are the true ids minus 35. UNLOCK and LOCK are verbs 55 (`$0104a8`) and 54 (`$01049a`); KILL, UNINV, WAKE, SLEEP are 50, 89, 74, 75
(`$010354`, `$01038a`, `$0103e0`, `$0103f8`); teleport is 37, nested IF is one verb (`$010626`), the level-start verb is 51 (`$010410`), POISON is 90 (`$010f7c`); verb 66 (`$010e38`) writes the `[type][sub][object]` records the overlay's class event handlers consume.

**Proven live** (`lever_script_live.py`, `teleport_live.py`, `level_verb_live.py`, `consumer_live.py`): a touch injected for the lever (id 144) runs the consumer (`$00fe24` 1 hit, gate 1), dispatches four verbs, table indices 10, 14, 30, 32 = script bytes `0a 0e 1e 20` (lever record byte +3 goes 00 -> 01); object id 86 (a LEVER in slot 37, script `0a 85 46 3a 25 22 02 02 00 17`) hits `$010974` and `$00e854` and sets `(A5)+1166` to `$22`; object id 84 (LEVER, slot 60, script `33 00`) runs verb 51: `$010410`, `$00e53c`, `$006890`, `$0068ca` once each, `2524(A5) = 1`, `2518(A5) = $ff`, and after a key the level-1 load (reads 661-664 then 665/132, 797/73, 870/55, 925/12; RAM `$04c65e` then holds level 1's overlay, 2892 of 2892 bytes). Negative control: in a coin walk the consumer runs every frame (49 calls) and no queued event matches a script block. **The overlay is not the interpreter's caller** (it calls only register-argument verb-block entries: services 3, 12, 15; Disk 2 level 4 also 20-22).

**Script census** (`script_census.py`, `verb_decode.py`): level 0 (the CAVERN snapshot) has 174 of the 1000 type-6 objects with 212 script blocks, events by count 0:39, 3:4, 4:5, 5:44, 7:12, 9:8, 11:6, 12:1, 13:1, 16:82, 18:4, 23:6; level 1 (`level1_loaded.snap`, from `level2_load.py`) has 220 objects with 264 blocks, events 0:36, 4:15, 5:40, 7:3, 9:65, 11:3, 12:9, 13:14, 16:52, 18:15, 21:1, 23:10, 27:1. Teleport scripts of level 0: id 2 BUTTON (slot 34) to room `$25`, id 86 LEVER (slot 37) to room `$22`, id 56 STONE SHELF (slot 38) to room `$25`, id 129 to room `$2e`. **The TUNNEL lever's (id 144) script contains no teleport** (it toggles its own state bit and type-4 flag `$33`), so mechanics.md's LOCK(144) stays a dead end: the walkthrough's room-to-room levers are other objects' scripts. The event numbers are the ring-304 opcodes; only 5 has been driven live (by injecting it), and what the game queues for each event is read from the producers (table under "How the script system fits together"), not run.

### The script language

Every block is `[len][event | $80][gate bytes][verb bytes ...][$17]`, and every `len` is even (all 212 + 264 object blocks and all 59 + 90 room blocks): a block whose content through the `$17` has an odd length is followed by one pad byte, never executed. On object blocks the pad happens to be `$17` (11 level-0 blocks, 20 in level 1), which is why `verb_decode.collect()` demands a `$17` at `len - 1`; in room blocks it is uninitialised (`$40`, `$02`, `$c1`, `$50` ...), so room blocks are walked by `len` and checked by parity (`room_blocks.py`). The consumer stops at the first `$17` (verb 23). Without bit 7 the consumer overwrites the event byte with `$ff` after the first run (`$00fe3e`), so the block never matches again (130 of the 212 level-0 object blocks have the keep bit); verb 29 does the same to the running block. No object block uses the second list at +`$20`; the room records use only that list ("Room scripts" below).

**Gate bytes.** The event's precondition routine (table `$00fe84`, 29 entries, events 0-28) reads its operands from the script before the verbs run, and compares them with the word `1156(A5)` or byte `1157(A5)` of the queue entry (the id or code of what touched, hit or used the object): one byte for events 1, 12, 13, 15, 17, 19, 20, 24; two bytes for 4, 9, 10, 18, 26; none for the rest (events 2 and 8 always reject). Examples: object 113 (event 4) gates on id `$0067`; the contact scripts (event 9) gate on `00 00` or `ff ff`.

**Conditions and IF.** The consumer clears the counter `2270(A5)` before each block. A condition verb (the COND rows) adds 1 to it when true and clears it when false, so a run of N conditions leaves N only if every one was true. The IF verbs test it: 14 runs its part when the counter is non-zero, 48 when it is zero, 58 n when it equals n, 59 n when it differs. Layout `[verb][n (58, 59)][len][verbs ... $16]` and optionally `[$0f][len][verbs ... $16]` for the else part; `len` counts itself, the part not taken is skipped by it, and IFs nest without limit (id 56 nests four). A `$0f` reached as a verb asserts (`ELSE SHOULDNT BE CALLED`). Object 2's four-item test is `34 10, 34 20, 34 1c, 34 1a, 58 4 [...]`.

**Operands.** Object ids are big-endian words; `$ffff` (printed `actor`) stands for the running object. Verbs 62 to 64 address any byte of the `(A5)` block: the first word is the offset, bit 15 set means a one-byte value and clear a word value. Verbs 40 and 64 compare with op 0 `>`, 1 `<`, 2 `==` and anything else `!=`. The `MESSAGE` and `DESCRIBE` words index the packed text table (`text_atlas.py`); the gold and XP counters are the longwords `1188(A5)` and `1192(A5)`, health `1174(A5)` of the maximum `2516(A5)`, the script variables the bytes from `2282(A5)`, timers table 3 above.

**Proof.** `verb_decode.py` parses every block of both levels with the lengths below and each one consumes exactly its `len`, ends on the terminator and agrees with every IF and ELSE length byte: 212 of 212 in level 0 and 264 of 264 in level 1 (61 of the 94 verbs occur). `verb_lengths_callcap.py` calls 92 of the 94 handlers under `callcap` on a scratch script and reads A1's advance (99 checks with the IF true and false runs and the word and byte forms of 62 to 64: 99 of 99); the other two are verb 15 (asserts by design) and verb 51 (jumps into the level loader; its one byte is tiled by the level-0 block `33 00`). `verb_effects_callcap.py` measures the effects of the gold and XP verbs (5, 6, 13, 85, 86), 38, 39, 45, 62, 63, 79 and 81 (21 checks) and the comparison ops of 40 and 64 (24 checks): 45 of 45. The names are read from the handler bodies and from the author's own assert strings (`GOANI A NONANI OBJECT`, `PUT IN RUCK RTN. RUCK FULL`, `KILLING A NON-EXISTANT CRE`, `UNTRAP CHEST NON-X OBJECT`, `DIRTY POTION NON-X OBJECT`, ...); the effects of about 65 verbs are proven live by `overlay/verbs2/verb_effects2.py` (212 checks, 0 bad: callcap memory deltas on scratch scripts, then the same verb inside the live game through the consumer, either from a level script's own event or a scratch script written over an event-5 block; the injection appends at the write pointer `304(A5)`, advances it by 8 and adds one to `1154(A5)`, because an entry written at `152(A5)` alone is overwritten by the game's own pushes in level 1). Not measured: verb 56 (box condition), 90 (POISON), verb 44's branch for a template with class bit 7 set, verb 41's collision search and its "CANT FIND A SPACE" asserts; verbs 84 and 91 have no use in either level (callcap only). The meaning of the anim byte states (`$fe`, `$ff`, 0) and the mover states (0, 1, 4) is not identified, only the transitions. `treasury_gate_live.py` runs object 2's whole script under the real consumer: with the type-8 list empty or holding only 16, 32 and 28 the four COND verbs (34), the IF (58) and the ELSE message (28) run and nothing teleports; with 16, 32, 28 and 26 in the list the same four tests, the sound (70), the teleport (37, room `0000` -> `0025`) and four PLACE verbs (41) run and the message does not (3 of 3 runs match the decode, the nested skip included).

**Two corrections.** Verbs 5 and 85 read their operand and then never add it: `$0102e0` and `$0102d4` load the sound id into D0 (`move.w #$1a,D0` or `#$24`) before `add.l D0,1192(A5)`, and the sound routine `$0158f8` returns D0 unchanged. Verb 5 therefore adds 26 XP for any operand (0, 1, 10, 200 all measured), verb 85 adds 26 for a positive word, and a negative word adds `$ffff0024`, which the game clamps to 0 (XP 100 becomes 0). The gold-pile verb is 6 (gold n, XP n/4). A single-byte "n XP" verb does not exist.

**Verb table** (`$00ffba`; operand layout as read by the handler, `obj:2` an object id word, `word:2` a word, `b` a byte; the last column counts uses in the level-0 and level-1 scripts):

| verb | handler | operand bytes | effect | uses (L0 / L1) |
|---|---|---|---|---|
| 0 | `$010076` | obj:2 | DELETE object, in two steps: now `1164(A5)` = id, the id goes onto the pending list `1386(A5)` and out of its room's type-5 list (room record +29 and +27 or +28 drop by one); on the next frame service the type-6 record is freed | 6 / 30 |
| 1 | `$0100b0` | obj:2 | SHOW object: clear bit 7 of record +3 (set bit 3 instead if its room is not the current one); no-op if not hidden | 29 / 25 |
| 2 | `$0101c2` | - | DELETE the current object (verb 0 on the record `348(A5)` points at) | 55 / 63 |
| 3 | `$0101d0` | obj:2 | GOANI: needs template +12 bit 2 (else assert); acts only when the anim byte is `$fe`: it becomes 0, ext +3 += 1 | 0 / 33 |
| 4 | `$01026c` | obj:2 | STOPANI: anim byte := `$ff`, record +15 bit 0 set | 0 / 1 |
| 5 | `$0102cc` | b | XP += 26 (operand read and ignored) | 7 / 13 |
| 6 | `$010304` | b | GOLD += n, XP += n/4 | 36 / 31 |
| 7 | `$01031e` | word:2 | REGISTER creature id (list 396(A5), max 6) | 0 / 1 |
| 8 | `$01032c` | word:2 | UNREGISTER creature id (asserts if absent) | 6 / 10 |
| 9 | `$010c4e` | b | queue `[$4013][164(A5) = the room record][n]`: event 19 on the ROOM's second script list | 0 / 10 |
| 10 | `$0104e2` | b | CLEAR FLAG n (type-4 record +2 := 0; nothing if already 0), sound `$12` if the flag is in the room record's list, else `$2a` | 9 / 11 |
| 11 | `$010554` | obj:2 | GOMOVE: mover byte (`rec+rec[13]`) := 0 (if it was 4, the next byte += 1) | 1 / 25 |
| 12 | `$0105b4` | obj:2 | STOPMOVE: mover byte := 1 | 1 / 2 |
| 13 | `$0105f2` | b | GOLD -= n | 0 / 0 |
| 14 | `$010626` | len | IF (2270 != 0) | 21 / 37 |
| 15 | `$0106a8` | - | ELSE marker (executing it asserts) | 10 / 18 |
| 16 | `$0106bc` | obj:2 | COND obj state bit 0 set | 3 / 13 |
| 17 | `$0106d6` | obj:2 | obj state bit 0 = 1 | 3 / 6 |
| 18 | `$0106e2` | obj:2 | obj state bit 0 = 0 | 16 / 4 |
| 19 | `$0106ee` | obj:2 | COND obj state bit 1 set | 0 / 3 |
| 20 | `$010702` | obj:2 | obj state bit 1 = 1 | 0 / 3 |
| 21 | `$01070e` | obj:2 | obj state bit 1 = 0 | 0 / 1 |
| 22 | `$01124e` | - | END of IF/ELSE part ($16) | 33 / 67 |
| 23 | `$01124e` | - | END of script ($17) | 212 / 264 |
| 24 | `$01071a` | obj:2 | obj state bit 0 ^= 1 | 0 / 1 |
| 25 | `$010728` | obj:2 | obj state bit 1 ^= 1 | 0 / 0 |
| 26 | `$0101a8` | obj:2 | HIDE object: bit 7 of record +3 set | 3 / 6 |
| 27 | `$010520` | b word:2 | SET FLAG n = word (type-4 record +2; nothing if equal), sound as verb 10 | 1 / 0 |
| 28 | `$011230` | word:2 | MESSAGE n (fade, text, wait) | 42 / 33 |
| 29 | `$01074e` | - | mark this block spent (event byte = $ff) | 1 / 4 |
| 30 | `$010756` | - | COND current obj state bit 0 set | 4 / 21 |
| 31 | `$01076c` | - | current obj state bit 0 = 0 | 2 / 1 |
| 32 | `$010778` | - | current obj state bit 0 = 1 | 7 / 10 |
| 33 | `$010784` | - | current obj state bit 0 ^= 1 | 1 / 6 |
| 34 | `$01079c` | word:2 | COND object id in the type-8 list | 9 / 3 |
| 35 | `$0107ca` | obj:2 | PUT IN RUCK: type-8 record `[id][template idx]` appended (`2438(A5)` += 1, capacity `2148(A5)` = 32), removed from its room list, `1164(A5)` = id, ring entry `[0000][record ptr]`; asserts if full or absent | 0 / 0 |
| 36 | `$0108ce` | obj:2 b b b b | CREATE a clone of o at (x, y, z, facing): a spawn entry on `1466(A5)`, a type-9 copy of the record, drained by the frame service `$00e38c` into a new type-6 record; the position is a request handed to the free-space search | 7 / 10 |
| 37 | `$010974` | b b b b | TELEPORT room, x, y, z | 4 / 13 |
| 38 | `$010be2` | b b | VAR n = v (bytes at 2282(A5)) | 4 / 2 |
| 39 | `$010bf0` | b b | VAR n += v | 7 / 9 |
| 40 | `$010c00` | b b b | COND VAR n op v (op 0 >, 1 <, 2 ==, 3+ !=) | 9 / 5 |
| 41 | `$010aaa` | obj:2 b b b b | PLACE object in room r at (x, y, z): another room writes x, y, z exactly, sets bit 3 of +3, `+10` = r and moves the id between the two rooms' type-5 lists; room 0 or `$fe` = this room (position adjusted, `+10` = 0); class 3 asserts | 8 / 1 |
| 42 | `$010c74` | b b | arm a room countdown: `2462(A5)` = a, `2461(A5)` = b ticks; the tick service `$009094` decrements b and at 0 sets `2462` := `$ff` and queues `$4014` (event 20 on the room record) with a | 1 / 0 |
| 43 | `$0107ae` | obj:2 b | COND object in room n ($fe = this room) | 0 / 0 |
| 44 | `$01083e` | obj:2 obj:2 b b | CREATE a clone of o2 at o1's position (spawn entry as verb 36, D6 from table `$5d2c[slot]`) | 1 / 0 |
| 45 | `$010c84` | word:2 | HEALTH += signed word (0 or less: death) | 14 / 48 |
| 46 | `$0100ae` | - | no-op | 0 / 0 |
| 47 | `$010d16` | obj:2 | COND object exists | 0 / 0 |
| 48 | `$010606` | len | IF NOT (2270 == 0) | 1 / 11 |
| 49 | `$010d32` | b b | ARM TIMER n = v ticks | 7 / 5 |
| 50 | `$010354` | obj:2 | KILL creature (queue event 23) | 1 / 3 |
| 51 | `$010410` | b | START LEVEL n+1 (n <= 9) | 1 / 0 |
| 52 | `$01044a` | word:2 | no-op (reads a word) | 0 / 0 |
| 53 | `$010454` | obj:2 | REVEAL NAME (clear hidden-name bits) | 0 / 0 |
| 54 | `$01049a` | obj:2 | LOCK | 0 / 2 |
| 55 | `$0104a8` | obj:2 | UNLOCK | 1 / 4 |
| 56 | `$010d5c` | obj:2 b b b b b b b | COND object in box (room; x0 x1 y0 y1 z0 z1) | 0 / 0 |
| 57 | `$010dd0` | word:2 | COND selected object 1262(A5) == id | 0 / 0 |
| 58 | `$01061a` | n len | IF (2270 == n) | 1 / 1 |
| 59 | `$01060e` | n len | IF (2270 != n) | 0 / 0 |
| 60 | `$010df2` | price:2 msg:2 | BUY prompt: false if gold `1188(A5)` < price; else prints message msg with the price and waits for a key: Y (`$15`) takes the gold and is true, N (`$31`) declines | 0 / 1 |
| 61 | `$010de0` | b | COND FLAG n non-zero | 0 / 0 |
| 62 | `$010b6a` | off, value (word; byte if off bit 15) | SET (A5)+off = value (word, or byte if off bit 15) | 0 / 0 |
| 63 | `$010b90` | off, value (word; byte if off bit 15) | ADD (A5)+off += value | 0 / 0 |
| 64 | `$010bb6` | off, value, op | COND (A5)+off op value (ops as verb 40) | 0 / 0 |
| 65 | `$010e0c` | obj:2 b | byte +1 of the object's first sub-block (`rec+rec[12]`) += signed n, clamped 0..255 | 0 / 0 |
| 66 | `$010e38` | obj:2 b | queue `[class (sub-block byte +1)][operand][record ptr]` on the list at `308(A5)` (`1264(A5)` += 1); `$00e24e` calls the class handler (class 10: the fire, -20 health) | 1 / 0 |
| 67 | `$010e5c` | obj:2 | GOACTI (object state bit 6 of +15 = 0) | 0 / 1 |
| 68 | `$010e7c` | obj:2 | STOPACTI (bit 6 = 1) | 0 / 1 |
| 69 | `$010e9c` | obj:2 b b b | MOVE: set the +3,+4,+5 bytes of the object record | 0 / 1 |
| 70 | `$010ec8` | b | PLAY SOUND n | 5 / 19 |
| 71 | `$010ed4` | - | no-op | 0 / 0 |
| 72 | `$010ffa` | word:2 | DESCRIBE: examine text n with the object details | 80 / 53 |
| 73 | `$010a7c` | obj:2 obj:2 | MOVE o2 to the position and room of o1 (o1 is untouched; a free spot is found in the current room) | 7 / 4 |
| 74 | `$0103e0` | obj:2 | WAKE creature | 0 / 0 |
| 75 | `$0103f8` | obj:2 | SLEEP creature | 0 / 0 |
| 76 | `$010d26` | b | COND shield bit n of 2436(A5) | 1 / 4 |
| 77 | `$010ee2` | obj:2 | UNLOCK CHEST | 0 / 0 |
| 78 | `$010f06` | obj:2 | UNTRAP CHEST | 0 / 0 |
| 79 | `$010f2a` | b b | RANDOM lo..hi -> 2520(A5) | 0 / 0 |
| 80 | `$010f3c` | b | COND 2520(A5) == n | 0 / 0 |
| 81 | `$010c3e` | b | 2520(A5) = VAR n | 0 / 0 |
| 82 | `$010f4a` | b | delete type-8 list entries whose template idx (word +2) == n | 0 / 0 |
| 83 | `$010f78` | b | no-op (reads a byte) | 0 / 0 |
| 84 | `$0108b6` | obj:2 obj:2 b b b b | CREATE a clone of o2 at o1's (x+dx, y+dy, z, facing); D6 left 0 | 0 / 0 |
| 85 | `$0102c0` | word:2 | word > 0: XP += 26; word < 0: XP = 0 | 0 / 2 |
| 86 | `$0102fa` | word:2 | GOLD += word, XP += word/4 | 0 / 1 |
| 87 | `$010ed6` | b | STOP SOUND n: `$015ae0` clears the queued word of the sound table `$0162a2` whose high byte is n | 0 / 6 |
| 88 | `$010790` | b | COND n == byte `2489(A5)` (written by the tick code at `$0092c0`, cleared at `$0090e8`; not a timer table) | 0 / 0 |
| 89 | `$01038a` | obj:2 | UNINV (clear bit 0 of +6) | 0 / 0 |
| 90 | `$010f7c` | b b b | POISON strength, duration, interval | 0 / 0 |
| 91 | `$010f9e` | b | COND low byte of the current object's template idx == n | 0 / 0 |
| 92 | `$010fb2` | obj:2 | CLEAR CHEST | 0 / 0 |
| 93 | `$010fd4` | obj:2 | DIRTY POTION | 0 / 0 |

**What the scripts do** (`scripts_level0.txt`, `scripts_level1.txt` in `scratchpad/cadaver/secrets_out/`, from `verb_decode.py --dump`, with the message text). Level 0, read from the decode:
- The treasury (proven live, `treasury_gate_live.py`, and with natural input in "The regalia walk" above): id 2 BUTTON (touched) tests that objects 16, 32, 28 and 26 are in the type-8 list, then plays sound `$3a`, teleports to room `$25` and places those four objects in room `$21` at (16,16,0); otherwise message 246 "ONLY THE KING MAY ENTER HIS TREASURY". Its examine text (event 16) is message 245, "THIS BUTTON ALLOWS ACCESS TO THE INNER TREASURY". Id 56 STONE SHELF runs the same four tests nested and teleports to `$25` with no message; id 16 is the WULF III breastplate (message 247). Id 486 gates on object 53 (message 379, "YOU MAY NOT PASS WITHOUT THE KINGS CROWN"; with it, flag `$29` is cleared and message 378 is shown).
- Levers: id 86 (sound `$3a`, teleport room `$22` (2,2,0), proven live); id 84 runs `33 00`, the level-1 start (proven live); id 129 toggles its state bit, adds 1 to script variable 7 and teleports to room `$2e`, and on the other toggle shows objects 256, 27 and 161 by the counter value 0, 1, 2 and prints "THE TREASURY IS EXHAUSTED" when it is above 2.
- Gold and XP: 36 uses of verb 6 (3 to 200 gold, XP n/4) each followed by verb 2 (delete self), ids 55, 119, 124, 131, 163, 267-270, 333, 346-349, 353-362, 412, 491 and the dragon's booty 501-508 (200, 200, then six of 50), which id 500 reveals with verb 1 and "THE DRAGON STEAMS, BUBBLES AND SMELLS, BUT AT LEAST YOU FIND HIS BOOTY". The verb 5 blocks (ids 27, 161, 256) add 26 XP.
- Hazards (event 9, gate `00 00`): health -7 (id 237), -15 (285), -5 (443), -1 (446), -25 (451), -50 (483); the fire (485) tests shield bit 1 (`76 1`): "THE FIRE CAUSED YOU NO HARM", else -20, then kills itself. Ids 114, 115, 117 and 120 cost 2 health on event 3, and their event-11 script counts in variable 0 and shows object 116 on the fourth, then resets it.
- Restoratives: ids 213 and 214 "THE WATER TASTES GOOD" (+2 health), id 392 "THE LIQUID SEEMS TO RESTORE YOU" (+10, then examine text tells full or empty by its state bit); ids 12, 141 and 256 arm timers 3, 2 and 5 (`49 3 28` and the like; the timers whose end clears a shield bit), ids 139 and 142 arm timers 0 and 1 (the poison pair). "THE URN SMASHES" (ids 452, 453) moves the urn to its broken twin (verb 73).
- 80 of the 212 blocks use verb 72 (an event-16 examine text) and verb 28 (a message) occurs 42 times.

Level 1 uses 13 teleports (rooms `$0c`, `$22`, `$34`, `$46`, `$52`, `$55`, `$5b`, chained by messages such as "THE SKULLS WILL ACTIVATE THE TELEPORTERS", "CHOOSE ONLY ONE TELEPORTER, AND CHOOSE WITH GREAT CARE", "THE EVIL TELEPORTER IS FRAGILE") and 48 health changes, and the verbs 3, 4, 7, 9, 19, 20, 21, 24, 54, 60, 67, 68, 69, 85, 86 and 87 occur only in level 1 (GOANI, STOPANI, REGISTER, the state-bit-1 verbs, LOCK, GOACTI, STOPACTI, MOVE, the `$df46` condition), verbs 27, 42, 44, 51 and 66 only in level 0.

### Room scripts

A room is a type-3 record (100 index slots, 72 populated in level 0, 97 in level 1) and carries its own scripts, run by the same consumer with bit 14 set in the opcode (`room_blocks.py`, `room_regions.py`; dumps `room_scripts_level0.txt`, `room_scripts_level1.txt`). Its layout, each point a match count over every room of both levels:

| offset | content | proof |
|---|---|---|
| 0 | offset of the region list = the end of the script blocks | 72 of 72 and 97 of 97 |
| 23 | flags: bit 6 visited (first-entry latch), bit 1 region loop on, bit 4 region events on | rooms with a region list have bits 1 and 4 set, 11 of 11 and 24 of 24 |
| 29 | object count minus one (the type-5 list is a separate resource) | see mechanics.md §37d |
| 31 | number of script blocks | 59 blocks in 30 rooms (level 0), 90 in 51 (level 1), every block `len` even and every one decoding with the object grammar to its first `$17` |
| `$20` | the blocks, back to back | they tile the record up to byte 0 in every room |
| byte 0 | the region list: a count byte N, a zero byte, N six-byte records `(x_lo, y_lo, x_hi, y_hi, z_lo, z_hi)` (inclusive overlap with the mover's box `[trail, lead]`, `$009160`; CAVERN's are `30 30 4e 4e 00 01`, `00 40 14 4e 00 01`, `0e 28 15 3f 00 01`) | tail = 2 + 6N in all 35 rooms that have one; all 27 (level 0) and 37 (level 1) event-15/17 gate bytes lie in 1..N; only one region of one room (level 1's 22) has no 15/17 block |

The eight events a room answers and what queues them are in the producer table above: 28 on the first entry, 6 on every entry, 14 from the room's periodic timer, 15 and 17 when an object overlaps region 1 to 4, 24 for a cast spell, 19 and 20 from verbs 9 and 42. Gate bytes: none for 6, 14 and 28, one byte for 15, 17, 19, 20 and 24 (region number, region number, verb 9's argument, verb 42's argument, spell id).

**What they do** (read from the decode; the producers of 6, 28, 14, 15 and 24 are live, 17 with a poked object, the rest is read):
- **First-visit blocks (28)** are spawners and rewards: rooms 20, 28, 38, 39 and 40 create object templates `#449` and `#444` (`36` CREATE at fixed x, y, z, facing `$fe` = this room; room 28 makes three, proven), rooms 36 and 49 (and level 1's 9 and 91) add 26 XP (verb 5 ignores its operand).
- **Entry blocks (6)** create the room's resident objects each time (`#446` in rooms 3 and 63, `#443` in 18, `#447` three times in 52), pay XP once (rooms 37 and 60, non-keep), and hold small state machines: room 15's counter (`VAR 8 += 1` per entry, then `SHOW` of object 414, 424 to 431 and 131 for counts 1 to 10) is a ten-visit reveal; room 30 says "THE CREATURE IS SLEEPING." while object 237 sleeps.
- **Tick blocks (14)** are periodic events: CAVERN creates `#467` at fixed coordinates every 15 timer passes, room 2 `#465`, room 21 three `#448`; room 7 counts and rolls verb 79 (0 to 2) to create one of `#279`, `#411`, `#278`; room 30 wakes creature 237 with "THE CREATURE AWAKES AND IS VERY VERY ANGRY."; level 1's captors talk on the tick (room 11's 122-byte block, the largest in either level: "WHY DONT YOU GIVE UP, YOU HAVE FAILED IN YOUR QUEST", "HERE, HAVE SOME GOLD"; room 46's 84-byte block: "AHH, A FRIEND. IVE NOT HAD SOMONE TO CHAT TO FOR AGES").
- **Region blocks (15 and 17), driven live in CAVERN** (`room_regions_live.py`): walking Down, Right, Down, Right from `gameplay_empire.snap` brings the hero's x lead to 48, the first step inside region 1 (x 48..78, y 48..78, z 0..1); from there every step queues event 15 (`$0092b4`, 3 pushes in the 30 windows of 5,000 steps) and the block's `45 ffff` takes one health each (67 to 64: pushes equal health lost). The record layout is confirmed at three low bounds by labelled pokes of the hero's bbox (the push comes on the first step the lead reaches the bound, with D7 = 2 at y lead 64, D7 = 3 at x lead 14, D7 = 1 at y lead 48). An object other than the hero (object 14, poked into region 1) queues event 17 once (`$0092da`), the block runs verb 41 PLACE once and the object leaves the room (rectangle 255,255,255,255); health is unchanged and the control run reads 0. The scan visits every placement entry whose flag byte (entry + 49) has bit 0 set, so a static object inside a region would push every pass (none of CAVERN's 22 does). They come in pairs on the same region: the hero's event 15 and every other object's event 17. Room 4 sends both to room 28 (`PLACE actor` room `$1c` at (`$2e`, `$19`, 2) for objects, `TELEPORT` to `$1c` (8, 3, `$50`) for the hero; proven for the hero) and room 28's region sends the hero back to room 4 (proven); CAVERN's three regions place objects in room `$39` and cost the hero 1 health (`45 ffff`); room 21 and room 27 are the drop: "LOOKS LIKE A LONG WAY DOWN." above, "THE FALL DAMAGES YOU" (health -10) or "YOU LOWER YOURSELF DOWN THE ROPE" below, by the state of object 271; room 27's region also deletes objects with template index `$29` or `$42` and counts them in variable 4, which rooms 48 and 49 test. In level 1 room 88's region runs verb 51 (start level) after a state test and room 14's four regions all run GOANI.
- **Spell blocks (24)** (room 1's driven live, `cast_sleep_live.py`: the cast's scroll is a labelled poke of a room object's body, the entry into room 1 an injected `37 01 4 7 0`, everything after the game's own cast path): level 1's rooms 1, 7, 21, 22, 27 and 91 answer spell `$17`, SLEEP, which the engine's spell table leaves as a grey-flash stub (above): no object block answers event 24, so these room scripts are what give the spell a game effect (verb 66 queues creature-class records, verb 17 sets an object's state bit, room 1 and 7 add XP); room 45 answers spell 2 with "A FREEZE SPELL ONLY WORKS ON LIVING CREATURES, BUT A GOOD TRY".
- **Events 19 and 20**: level 1's room 80 (event 19, keep) counts verb-9 calls in variable 4 and reveals, at 4, 8 and 10, animations of object 476 and, at 10, "NOW THATS WHAT I CALL A GAME PLAYER" and object 609; rooms 82 and 88 answer the countdown of verb 42 (room 88 with gate `$0a`).
- Level 1 gates by what the hero carries: room 87's entry block says "LORD CAROLUS ALLOWS NO MAGIC OR WEAPONS IN HIS ROOM" and deletes six kinds of type-8 entries (verb 82), room 89's "THE KEEPER OF THE TOKENS MAY PASS" tests a variable, and room 17's region (event 15) tests the type-8 list (verb 34) and answers "YOU ARE NOT A CAPTAIN, AND CANNOT ENTER".

The room blocks use 35 (level 0) and 43 (level 1) distinct verbs. Verbs 43, 47, 74, 79, 80, 81, 82 and 91, which the verb table above shows with 0 / 0 uses (its columns count object scripts only), occur in room blocks; the 25 verbs no block of either level uses are 13, 25, 35, 46, 52, 53, 56, 57, 59, 61-65, 71, 75, 77, 78, 83, 84, 88-90, 92 and 93.

## Loading, the expander and the level directory

Every level resource on disk is packed, and **the game has its own expander**: `$0118ec`, an LZSS + adaptive Huffman coder of the LHA `-lh1-`/LZHUF family (entry `$0118ec`, start `$0119c4`, dictionary `$011a4e`, decode char `$011a8a`, decode position
`$011b20`, tree update `$011b5e`, rebuild `$011c10`; 4096-byte window, 60-byte lookahead, minimum match 3, 314 symbols, position code from the standard `d_code`/`d_len` tables at `$011cce`/`$011dce`, 256 of 256 bytes equal to the textbook tables;
the dictionary starts LHA style, MSB-first bit reader). A block is a 4-byte big-endian expanded length then the bit stream. **This retires the "no depacker found" statements** of mechanics.md §28c, §51c, §52 and §56. `lzh_proof_callcap.py` pokes each of the one-disk image's 8 packed blocks into
free RAM and calls the game's own `$0118ec` under `callcap`: 8 of 8 match the Python decoder `cad_lzh.py` bit for bit (3088, 116950, 58252, 8096, 2896, 125840, 61132, 7639 bytes, 383,893 of 383,893). "EXPANDING DATA" is message 8 of the 12-message
ASCII table at `$006250`, shown at `$00bae2` before the expander runs; `$00ba50` does the raw sector read and dispatches on the destination pointer (negative: read only, zero: verify the header, positive: expand).

**The level directory** starts with the 6-byte tag `881990` and five words (12, 9, 1990, 21, 14 on the one-disk image; 24, 9, 1990, 12, 2 on the two-disk Level disk): day, month, year, hour, minute of a build stamp (*inferred* from the values). A flat list of
`(start sector, sector count)` pairs follows; a level record is 5 pairs (stride 20, `mulu #$14` at `$00bac8`), each block lzh or raw (resource 2 is raw; resource 0 is the level's native code overlay, next section). The one-disk image has the directory at sector 400 and
**two populated levels, not one**: slot 0 is sectors 401-660, slot 1 sectors 661-936, the remaining records are `(937, 0)`. mechanics.md §51's "no second level's worth of data" is wrong. The two-disk Level disk has 5 levels (35 blocks, directory at sector 7,
`disk2_levels.py`; all 30 packed blocks decode), matching the ZIPPY text's "five levels". A level load runs the expander 4 times and the raw read `$00ba2e` 5 times (live `hits`).

**The second level loads and plays.** `level2_load.py` patches the snapshot to run the level-start verb `$010410` with operand 0 (PC patched, A1 at a zero byte), presses space at "PLACE LEVELS DISK", runs about 24M steps: 4 expander hits, 5 raw reads, `2524(A5) = 1`, maximum
health `2516(A5)` = 200 (level 1: 100), and the screen is a sandstone temple room with a hanging chain and a red floor circle (`level2_loaded.png`, never seen before). The Empire `[t]` dump of Disk 2 looks damaged in levels 3 and 5: 31 sectors differ from the Replicants dump (660-669,
700-709, 1415, 1431, 1456-57, 1472-73, 1480, 1498-99, the boot sector and 1580) and the affected blocks stop consuming their stream early (L2 res1 61,984 of 70,140 bytes against 69,750 in Replicants; L4 res5 42% against 94%, healthy blocks use over 99%); prefer the Replicants Disk 2 for those levels
(cause *inferred*: dump error or protection damage).

**Protection in the one-disk image: none live.** The boot sector (checksum `$1234`) loads track 79 (sectors 1580-1586) and jumps to it (padding "*PETIT CURIEUX!*"); that loader reads the cracktro stage (sectors 20-28) and then 200 sectors from linear sector 30 (`stage3.bin`, the game image,
which sets A5 = `$018152` and jumps to `$0067e6`). Nothing reads an MFP timer, there is no FDC read-address or read-track command (the FDC code uses restore `$03`, seek `$13`, read sector `$80`, write sector `$a0`, write track `$f0`, force interrupt `$d0`), and the only on-disk check is the
`881990` tag used as a format sanity check at `$00baae`/`$00bab8` (failure retries the read). The write-track routine serves the save disk. Dead code: `$00baf2`-`$00bb20` parses an LHA-style header and nothing calls it.

**The tile-stack unpacker** (graphics.md §5b, `$00add0`-`$00ae8c`), as an algorithm (`tile_stack_rle.py`; 320 of 320 bytes of the live table at `2914(A5)` for CAVERN and for TUNNEL): the room's byte stream starts with the stack depth D7 (0 ends the room); the group at `$00ae64` is one byte `b`
and two counts: for `b != 0` its low nibble is written as the attribute of the first `count0` cells of plane 0 (even bytes) and its high nibble likewise for plane 1 with `count1` (a zero nibble skips the plane, its count byte is still consumed), for `b == 0` nothing is filled; then W columns of D7 tile bytes
go into the odd bytes of plane 0 (column stride 16) and H columns into plane 1 (`+$a0`), W and H being room record bytes +4 and +5 (CAVERN W=10 H=7 uses 104 of 122 stream bytes; TUNNEL W=3 H=4, 37 of 42). No xor or rotate decrypt loop exists anywhere (the `eor` hits are masks or data).

## The sound engine (and what `ai.md` called the entity script interpreter)

`$015c70` `EntityScriptDispatch`, the "action scripts" and the "3 action slots" of ai.md §1-5 are a **three-voice YM2149 sequencer**: the slots are the three PSG voices, the scripts are music and effect bytecode, and `$01616c` is not a key dispatch table but the
62-entry **sound request table**, indexed by sound id (`$0158f6` is a last-sound-id byte, not an IKBD dispatch). ai.md §5's "TickScale is the tempo" guess was right. The transcription `cad_sound.py` matches the game frame for frame: **62 of 62 sounds, 400 VBLs each (24,800 frames of 11 register values), equal to the real `$ff8800`/`$ff8802` write stream**
(`snd_proof.py`, `snd_proof_all.log`), and six multi-event scenarios (priority, round robin with all voices busy, two-voice over a busy voice, queue/stop/re-pick, all 12 queued ids): 38 of 38 events and 1,680 of 1,680 frames (`snd_scenarios.py`).

| item | address | content |
|---|---|---|
| VBL hook | `$0158dc` | runs the tick only while `$0158da == 0`; the FDC code sets it (`$01565e`), so sound stops during disk I/O |
| PlaySound(D0 = id) | `$0158f8` | 43 call sites, 26 literal ids; StopSound `$015aec`/`$015ae0`, RepickQueued `$015b3e`, StartSet `$015aaa`, StartEntry `$015a7e`, InstallAction `$015bf4` |
| request table | `$01616c` | 62 records of 5 bytes `[prio/bit7][voices][a][b][c]`: 41 effects (round robin over free voices, `$0162cd`/`$0162cc`), 12 queued (bit 7: sustained, looping; pending list `$0162a2`), 9 three-voice priority (ids 17, 21-23, 28, 32, 33, 36, 53; 21-23 are silence sets) |
| set table | `$0167aa` | 3 bytes per id: the fixed voice position used by the re-pick |
| action pointer table | `$0163aa` | 256 longs: slot 0 null, 1-116 real scripts (`$016864`-`$016fe4`, 1,920 bytes), 117-255 the filler |
| envelope presets, noise envelopes | `$016fe5`, `$01729d` | 58 records of 12 bytes (51 used), 7 records of 6 |
| note table | `$0160ac` | 96 equal-tempered periods (entry 12 = C1, 32.7 Hz; 48 = middle C; 0-10 duplicate the low octave; periods below `$800` are doubled by the `lsr` fold at `$015de2`) |

Bytecode: literals below `$80` are notes; 17 opcodes `$80`-`$90` (jump table `$015cb6`): volume, mixer bits shifted by voice, restart, duration, yield, tempo (scale = 3000 / (byte * 4); the used values `$96`, `$bc`, `$fa` give 5, 3, 3 VBLs per unit), duration sum, envelope preset (a 12-byte record copied to voice fields 34-45), noise base,
noise envelope, loop flags, idle, stage / call another action (`$8c`/`$8d`), transpose, loop start and loop test (`$8f`/`$90`, the body runs count + 1 times). Per VBL and voice: a countdown, then the script fetch when it reaches zero, then two software envelopes (amplitude and pitch: two delay phases, then repeat-and-step) added into 50(A4) and 14(A4),
the noise period from the ring at `$016372`, and the flush of registers 0-10 (`$015e5e`-`$015ea2`). Registers 11-13 are never written, so the hardware envelope is unused, and R7 gets bit 6 forced on every flush. The longest sound is id 28, 1,201 VBLs (24 s), the death jingle played at `$010cd8` when health is zero or less.
The object class table at `$00620b` (indexed by `29(A4)`) yields ids 57, 16, 51, 52 and feeds the two sustained-contact slots `2491(A5)` and `2495(A5)`; the movement stream, three ring handlers and the verbs' play/stop ops (`$010ecc`, `$010eda`) supply the rest. The "action 101 animation-only" script of mechanics.md §22 is sound 30's script.

## The day

`DAY n` on the status bar is wall-clock time, nothing more. The VBL ISR (`$01528e`-`$0152d2`) counts `2171(A5)` down from `2172(A5)` (50): at zero it does `2169++` (seconds); at 60 it clears it and does `2168++` (minutes); at 30 it sets `2170(A5) = 1`, does `2166(A5)++` (the day byte), clears `2168` and does `2167++`. One day is 50 * 60 * 30 =
90,000 VBLs, about 30 minutes at 50 Hz. Proven: from `2171 = 50, 2169 = 58, 2168 = 29` the wrap arrives after exactly 100 VBL entries; poking `2168 = 29, 2169 = 59, 2171 = 1` makes `2166` go 0 to 1 (`day_counter_proof.py`). The only reader of `2166` is `$00ebca` (the bar text, string 29 + `2166 + 1`); `2167` is never read; nothing in any level overlay touches either.
The flag `2170` has two consumers: the main loop (`$006b2a`) redraws the bar and clears it, or the timer service (`$009006`, every 17th call) queues the banner "A DAY PASSES ..." (string 28) and sets `2170 = $ff`, after which the bar text stays stale until the next status refresh (seen unchanged for 6M steps). No room, monster or light changes with the day: `hits 40M` on the room loader and the level-restart entry gave 0 idle.
This retires cadaver.md's item 10 (`2516(A5)` is maximum health, `$0069ba` is the room load of the level-restart routine `$0067fc`).

## Random numbers

One generator, export service 16: **`$011544` `RANDOM(D1..D2)`**, a 16-bit linear congruential generator built from shifts (no `mul`, which is why a scan of the `mulu`/`muls`/`divu` sites found nothing). The seed is the word `1134(A5)` (`$0185c0`, `$14f6` in the snapshot; nothing writes it but the generator and the F1 map's save/restore pair `$00a9b4`/`$00aa16`):
`s' = 4 * (((s & $ff) << 8 | $0a) - s) + s + 1` mod 2^16 (1 if 0), then `n = D2 - D1 + 1`, `d = $ffff / n + 1`, result `D1 + s' / d` (16-bit `divu`). `$011580` is the same step without a range (no caller); `rng.py` pokes 40 seeds and two ranges and compares the game's D0 from `callcap $011544`: 40 of 40. Callers: `$00bd1e`, `$00bd42` (main image), verb `$010f32` (script), and the overlays: class 1's hop (range 0-2, `$04c7a8`) and the steering routine `$04cab4`'s random mode (range 0-7, `$04cac8`), so creature movement and whatever the two main-image sites do run on the seed's own history: it is never re-seeded from a clock, timer, video counter or key (no hardware entropy is read anywhere: no MFP timer data register, no `$ff8205/7/9`, no PSG read, the IKBD only in its ISR), so a run replays exactly given the same input timing (*inferred* from that; not replayed). Free-running counters (`$00568e` VBL wait, `$00624e` pacing, `2471(A5)`) feed nothing.
The deliberate `moveq #0,D0 / divu D0,D0` crash (`$0117c6`, and one copy in each overlay) is vector 5, the TOS handler. Also found: `$0115a2`, a rotating-sum checksum over a buffer (`add`, `rol.w`; no direct caller).

## Dead and unreferenced content

- Rank title 83 "BITMAP BROTHER" and the rank table's missing terminator (above).
- Spells and potions that no room places. The static census (`item_census.py`: every room's object id list, every type-6 template with class byte 1 or 2) finds 14 spell scrolls and 4 potions in the 72
  rooms: MAGIC MISSILE (room slot 69, three scrolls of 150, 200 and 20 charges), MASSACRE (slots 8, 58, 59), MAP (slot 24, two), SLOW CREATURE (46), BLESS POTION (71), READ MAGIC (40), LEARN POTION (25),
  and two ids outside the table (49 in slot 23, 58 in slot 25); potions STAMINA (37), GIANT JUMP (25) and two ids outside the table (25 in slot 15, 19 in slot 64). Twenty of the 27 spells and sixteen of the 18
  potions are never placed by the static lists, including IMMORTAL, STRENGTH and SUICIDE. This is a lower bound: scripts can create objects (`CREATE`), and slot 69 and 71 are not ordinary rooms
  (mechanics.md 67: slot 69 reads 102 loader writes for 28 ids, slot 71's list has no terminator), so the MAGIC MISSILE scrolls there are probably the player's starting kit.
- Potion 5 has the one-space name at string 114.
- Spells: TRANSPORTER, DUPLICATE, ENCHANT LIQUID and POLTERGIEST are bare `rts`; READ LANGUAGE, TALK WITH DEAD, SLEEP, DISPELL MAGIC and ids 27, 29 only flash (overlay section). Potion 5 and SLOW are bare `rts`; WATER only prints.
- Two main-image routines have no direct caller: `$011580` (the RNG step without a range) and `$0115a2` (a rotating checksum).
- Sound scripts: 24 of the 116 action scripts are defined and referenced by no request, set or `$8c`: `$02, $09, $0a, $25-$27, $2e, $35-$37, $3b, $45, $46, $4b, $4e, $4f, $52-$58, $5e`.
- The `enhanced sound for 1MEG` note (above) has no counterpart: no second sound path exists.
- Export service 8 (the teleport) is called by no overlay (none of the 7 decoded contains `moveq #32,D6`); only object scripts reach it, through verb 37.

## Open

- What the class bytes of type-6 templates mean beyond 1, 2, 4, 7, 8 and bit 7 (the histogram in `item_census.py` has about 80 distinct values) and which objects carry which hint.
- F2 and F3's exact effects in the icon-choice loop, C's effect, H's restore half, and the dying path's price prompt: read, not run.
- The lock that takes the escape number 1044 and what the named-copy strings are for.
- The Disk 2 overlays' two extra header words and negative class-1 record, spell 28 in the Disk 2 builds, services 9, 13, 19, and the real A3/A4 at a spell cast (only `callcap` with inferred registers for the class-gated spells); the projectile-hit paths `$00fa72`/`$00fb60`; list 4's values.
- Which sound ids fire in play: 36 of the 62 have no literal call site (data-driven: the object class table `$00620b`, the movement stream, ring handlers, verb ops).
- Whether XP 60,000 is reachable (the rank table's overrun).
- Verbs not measured (see "Proof" under the script language): 56, 90, verb 44's class-bit-7 branch, verb 41's collision search; what the anim-byte states (`$fe`, `$ff`, 0) and mover states (0, 1, 4) mean beyond the transitions; the class handlers reached through verb 66 other than class 10 (a bad sub jumps to garbage). The Disk 2 levels' scripts are not decoded.
- Room scripts ("Room scripts" above): events 15 and 24 are driven live and 17 with a poked object; the scroll of the SLEEP cast and the entry into room 1 are injected (no scroll or spell source was walked to), event 17 by a natural mover and the regions' upper and z bounds are *read*; byte 23's other bits (0, 2, 3, 5, 7) are not decoded; the Disk 2 levels' rooms are not decoded.
- Events 18 and 26 and icons 3, 4, `$e` were reached only with a poked class byte or not at all; walk to a class-8 chest (ids 83, 224) and a class-`$c` object (id 70) to drive them naturally. The producers of events 1, 4, 10-13 and 25 are still unread. Events 3 and 21 have no producer in any listing (inferred dead script content). Which object ids the type-8 list tests (34) name: the treasury's four are 16, 32, 28, 26, and a pick-up writes `[id][class-template id]`; whether all four can be picked up by walking is not driven.
