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
| Return / Space | `$1c` `$39` | `$006cce` | the interact action (`moveq #21,D0 / jsr $15aaa`, then `$009682`), the keyboard twin of fire; Return also leaves bit 1 of `2519(A5)` set (Space clears it at `$006cc2`), which the icon-choice loop reads at `$009c98` (*read*) |
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

**The interpreter's caller is the ring-304 queue consumer `$00fdbc`** (cadaver.md's open item 1, closed). Queue entries `[opcode.w][object ptr.l][word]` are read from `152(A5)` (count `1154(A5)`); opcode 5 is "touched" (queued by `$00a474` and others). For the object the consumer walks its script blocks, `[len][event | $80 = keep][verb bytes ... $17]` (`len` counts itself; blocks start at template +`$10`, count at +11, or at +`$20`, count at +31, when opcode bit 14 is set); when the opcode equals a block's event byte it runs the gate from the table at `$00fe84` and then executes the verb bytes through the **verb table at `$00ffba`, which has 94 entries**
(its first word `$bc` is its size in bytes; it ends exactly where `$010076` begins; dump `verb_table94.txt`). The "59-entry table at `$010000`" of mechanics.md §23a, §24, §64 and §69 was read from the wrong base: it is the last 59 entries with every target off by `$46`, which explains every "mid-instruction landing" of §64d, and its ids are the true ids minus 35. UNLOCK and LOCK are verbs 55 (`$0104a8`) and 54 (`$01049a`); KILL, UNINV, WAKE, SLEEP are 50, 89, 74, 75
(`$010354`, `$01038a`, `$0103e0`, `$0103f8`); teleport is 37, nested IF is one verb (`$010626`), the level-start verb is 51 (`$010410`), POISON is 90 (`$010f7c`); verb 66 (`$010e38`) writes the `[type][sub][object]` records the overlay's class event handlers consume.

**Proven live** (`lever_script_live.py`, `teleport_live.py`, `level_verb_live.py`, `consumer_live.py`): a touch injected for the lever (id 144) runs the consumer (`$00fe24` 1 hit, gate 1), dispatches four verbs, table indices 10, 14, 30, 32 = script bytes `0a 0e 1e 20` (lever record byte +3 goes 00 -> 01); object id 86 (a LEVER in slot 37, script `0a 85 46 3a 25 22 02 02 00 17`) hits `$010974` and `$00e854` and sets `(A5)+1166` to `$22`; object id 84 (LEVER, slot 60, script `33 00`) runs verb 51: `$010410`, `$00e53c`, `$006890`, `$0068ca` once each, `2524(A5) = 1`, `2518(A5) = $ff`, and after a key the level-1 load (reads 661-664 then 665/132, 797/73, 870/55, 925/12; RAM `$04c65e` then holds level 1's overlay, 2892 of 2892 bytes). Negative control: in a coin walk the consumer runs every frame (49 calls) and no queued event matches a script block. **The overlay is not the interpreter's caller** (it calls only register-argument verb-block entries: services 3, 12, 15; Disk 2 level 4 also 20-22).

**Script census** (`script_census.py`): 174 of the 1000 type-6 objects carry 212 script blocks; events by count 0:39, 3:4, 4:5, 5:44, 7:12, 9:8, 11:6, 12:1, 13:1, 16:82, 18:4, 23:6. Teleport scripts: id 2 BUTTON (slot 34) to room `$25`, id 86 LEVER (slot 37) to room `$22`, id 56 STONE SHELF (slot 38) to room `$25`. **The TUNNEL lever's (id 144) script contains no teleport**, so mechanics.md's LOCK(144) stays a dead end: the walkthrough's room-to-room levers are other objects' scripts.

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
- The lock that takes the escape number 1044 and what the named-copy strings are for; the 94 verbs' operand lengths and names (only verbs 37, 51, 54, 55, 50, 89, 74, 75, 90 and the first 35's table indices are pinned; scripts are read by eye).
- The Disk 2 overlays' two extra header words and negative class-1 record, spell 28 in the Disk 2 builds, services 9, 13, 19, and the real A3/A4 at a spell cast (only `callcap` with inferred registers for the class-gated spells); the projectile-hit paths `$00fa72`/`$00fb60`; list 4's values.
- Which sound ids fire in play: 36 of the 62 have no literal call site (data-driven: the object class table `$00620b`, the movement stream, ring handlers, verb ops).
- Whether XP 60,000 is reachable (the rank table's overrun).
- How the level-start verb `$010410` is dispatched (its table entries 39 and 40 land mid-instruction at `$010426` and `$01043e`) and which script calls it.
