# Cadaver: handoff

Updated 2026-09-30 by the 80th-pass session (two parallel agents: the player-action panel driven live, and the "read, not run" object-script verbs measured), on top of the 79th-pass architecture write-up. Commits: see `git log` for `cadaver: 80th pass`.

## Resume point

- Last work commit: `795d62d` cadaver: 80th pass (docs, `overlay/action/`, `overlay/verbs2/`); the handoff and a one-line `CLAUDE.md` lesson are the commits after it.
- Read `reversing/cadaver/secrets.md` first: "Object scripts", "How the script system fits together" (the producer table is now live-proven for events 0, 5, 16, 27, 9, 7), the new subsection "The player's action panel (driven live)" (input chain, icon table `$00a0ac`, what a pick-up writes, controls), then "The script language" (verb table, corrected for verbs 0-4, 9-12, 26, 27, 35, 36, 41, 42, 44, 60, 61, 65, 66, 73, 82, 84, 87, 88, 91).
- Scripts: `reversing/cadaver/py/secrets/overlay/` (table in `py/secrets/README.md`); new this pass `overlay/verbs2/verb_effects2.py` (212 checks, 0 bad, about 40 s) and `overlay/action/action_survey.py` and siblings (each row 3 of 3). All run from `M68000/` against `scratchpad/cadaver/gameplay_empire.snap` (CAVERN, level 0) or `scratchpad/cadaver/level1_loaded.snap`; the action scripts build their own start snapshots (`sv_*.snap`) under `scratchpad/cadaver/secrets_out/action/` on first use. Decoded scripts: `scratchpad/cadaver/secrets_out/scripts_level0.txt`, `scripts_level1.txt`; indexed in `scratchpad/ANCHORS.md`.
- No emulator source changed, so no rebuild or regression-net run is needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in `secrets.md`)

Earlier passes (77th-79th): main-loop keys, gold-priced saves, rank table overrun, assert layer, level code overlay and export table, the consumer `$00fdbc` and the 94-entry verb table at `$00ffba`, the verb grammar (476 of 476 blocks tile exactly), the LZHUF expander, the sound sequencer, day clock, RNG, the three-mechanism architecture, `queue_producers.py` (48 push sites, 25 events).

80th, action panel (`overlay/action/`, natural joystick and key input, 3 of 3 fresh runs per row):
- Fire next to an object opens the icon panel `$009c82`, dispatch `$00a08c` -> table `$00a0ac` (15 icons resolved). Space/Return acts on the *held* rucksack item, on the key's release, and does nothing with an empty rucksack.
- Events: 0 = TAKE (icon 2, `$00a184`; coin 412, pickaxe 168, diary 5), 16 = examine (`$00a418`), 5 = the object's own action icon (read icon 8: books 488, 510; operate icon 7: lever 144; icon 9: barrel 60), 27 = select (`1262(A5)` written at `$00a73a`), 9 and 7 = proximity every frame next to an object (12/12, 13/13, 0 in the open). Corrections: event 18 is "held item applied to or put into the object in front" (icon `$c`), not pick-up; the Return/Space "twin of fire" row was wrong.
- A pick-up writes `[object id][class-template id]` at `$00c4cc`/`$00c4d4`, the index words `$00c4fe`-`$00c516` and `2438(A5)` at `$00c4da` (type-8 descriptor `$04a4f6`).
- Events 3 and 21 have no producer in 11 listings (resident image, both level overlays, 9 overlay listings; 0 computed-opcode pushes): inferred dead script content.
- Events 18 and 26 only with a *poked* class byte (synthetic): 18 for word `$a8`, `$00a6a6` writes the item id into the container; 26 removes the item.

80th, verbs (`overlay/verbs2/`, 212 checks, 0 bad, callcap plus live through the consumer): DELETE is two-step (pending list, freed next frame); SHOW/HIDE bit 7 of record +3; CREATE family spawns a clone through the list `1466(A5)` drained by `$00e38c`; PLACE, PUT IN RUCK (35), flag verbs, sound stop (87), BUY prompt (60), room countdown (42), verb 66 queue to `$00e24e`. Name corrections: 73 moves o2 to o1, 87 is STOP SOUND, 60 is BUY, 42 arms a room countdown. New finding: room records carry a second block list at +`$20` (level 1's room 80 has an event-19 block that a real `09 00` runs); verbs 9 and 42 queue events 19 and 20 for the room.

## Open, in priority order

1. **Decode the room-record script blocks.** `verb_decode.py` covers only type-6 objects; rooms carry blocks at +`$20` (count at +31) answering events 19 and 20 (and possibly more) in both levels. Extend the decoder to walk every room record's lists, self-check that each block tiles to its `len`, then list what they do. This may name the last producers' consumers and is static work with a tight proof.
2. **Drive the natural puzzle end to end**: walk to the four regalia (ids 16, 32, 28, 26), pick each up with icon 2 (confirm the type-8 records), then reach object 2's BUTTON and take the treasury teleport with real joystick input, no pokes. Then walk to lever 86 (room `$22`) and lever 84 (level 1) the same way. Proves which regalia are pickable and closes the loop from input to room change.
3. **Events 18, 26 and icons 3, 4, `$e` naturally**: walk to a class-8 chest (ids 83, 224 and others in other rooms) and the class-`$c` object (id 70, room slot 64); a subclass-5 chest gives icon 3 (`$00a494`/`$00a59c`, event 5).
4. **Reach the rest of the game**: walk level 1 from `level1_loaded.snap` through its 13 teleport scripts (rooms `$0c $22 $34 $46 $52 $55 $5b`).
5. **The Disk 2 builds**: decode the Disk 2 levels' scripts (needs a snapshot per level from `level2_load.py`; the 33 verbs neither level uses may occur there); overlays with two extra header words, a negative class-1 record, service table `$005eee` (29 entries), spell 28 as a damage effect.
6. **Still read, not run**: verbs 56 and 90, verb 44's class-bit-7 branch, verb 41's collision search; the anim-byte and mover states' meaning; the class handlers reached through verb 66 other than class 10; the events the timer service and engine code queue (1, 4, 6, 10-15, 17, 24, 25, 28).
7. Older loose ends in `secrets.md` "Open": F2/F3 effects, the escape-number lock (1044), class bytes of type-6 templates (about 80 distinct values), which sound ids fire in play, `$0115a2`, whether XP 60,000 is reachable; the room-census oddities of mechanics.md §67, STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

## Known traps

- The push-site readings of the 79th pass were *inferred* and two were wrong when driven (event 18 "pick-up", event 0 shared with a timer): name an event from a live drive, not from the producer body. Event 5 comes from three different icons.
- Inject queue entries at the write pointer `304(A5)`: advance it by 8 and add one to `1154(A5)`. Writing at `152(A5)` alone (as `treasury_gate_live.py` and the older live proofs do) works in quiet level 0 but the game's own pushes overwrite it in level 1 (consumer hit count 0).
- The REPL prints at most 4096 lines: a `callcap` of anything that redraws is silently truncated. Write the result to a JSON out-file (`callcap <addr> <steps> <path> ...`) as `overlay/verbs2/h.py` does.
- Joystick fire as two packets fails: send `kbd ff 80` as one command (`Repl.joy` sends them separately and leaves `2529(A5)` at 0). `Repl.hits` hides the ~300 settle steps after a fire release, so consumer hits look like 0; `drv.py`'s `Tally.joy` counts them. Fire must be released and pressed again to confirm in the panel; Return waits for release before acting, and a key held forever hangs at `$011898`.
- Object ids read after an action can be wrong: a DELETE compacts the resource block and moves templates (the coin-take first read as 413). Read ids from a map taken before acting.
- A `callcap` of verb 66 with a class other than 10 jumps to garbage and kills the REPL.
- `cadaver.sym` labels are the nearest symbol below an address, not a routine boundary (`QueueEntityIntoRing304_AndSetField2271_Direct` and `StatsScroll_RankTable176A5` cover far more than their names say).
- `tools/disassemble.py` takes bare hex arguments (`--all a3c0 a430`, no `0x`, no `--help`). macOS awk has no `strtonum`; use Python.
- Verbs 8 and 75 assert unless the id is in the creature list at `396(A5)`, verb 29 needs A4 in valid RAM, verb 79 with lo = hi divides by zero; `callcap`'s `regdelta` shows A1 as `$snapshot->$final`. Seeds are in `verb_lengths_callcap.py` and `verbs2/h.py`.
- Script operand bytes are hex in the dump but object ids print decimal (`#16`); message text of verbs 28 and 72 is looked up through the packed table, so a stale snapshot prints `?`.
- The type-8 list is empty at CAVERN start; the four regalia have to be acquired or poked.
- Earlier traps still standing: a literal-pointer hit dismissed as alignment coincidence needs the real table base; a direct-call scan does not cover tables loaded per level; a "key does nothing" verdict must watch the handler's branches and flags (CLAUDE.md).

## Next session

`/resume cadaver` and start with open item 1 (extend `verb_decode.py` to the room records' block lists in both levels; static, tight self-check), then item 2 (walk to the four regalia and the treasury button with real input).
Prompt: `/resume cadaver`.
