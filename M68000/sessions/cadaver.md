# Cadaver: handoff

Updated 2026-09-30 by the 78th-pass session (the object-script verb decode). Commits: see `git log` for `cadaver: 78th pass`.

## Resume point

- Read `reversing/cadaver/secrets.md` first, "Object scripts" and its subsection "The script language": block layout, event gates, IF/ELSE grammar, the 94-verb table with operand layouts, and what the scripts do. Scripts are in `reversing/cadaver/py/secrets/overlay/` (table in `py/secrets/README.md`); all run from `M68000/` against `scratchpad/cadaver/gameplay_empire.snap` (CAVERN, level 0) or `scratchpad/cadaver/level1_loaded.snap` (level 1 loaded). Decoded scripts of both levels: `scratchpad/cadaver/secrets_out/scripts_level0.txt`, `scripts_level1.txt` (regenerate: `verb_decode.py [snap] --dump`); indexed in `scratchpad/ANCHORS.md`.
- No emulator source changed, so no rebuild or regression-net run is needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven so far (counts in `secrets.md`)

Earlier passes (77th): main-loop keys, gold-priced saves, rank table overrun, assert layer, level code overlay and export table, the consumer `$00fdbc` and the 94-entry verb table at `$00ffba`, the LZHUF expander and two-level directory, the sound sequencer, day clock, RNG.

This pass (78th, item 1 closed):
- The verb grammar: 212 of 212 level-0 blocks and 264 of 264 level-1 blocks decode to exactly their `len`, end on `$17`, and agree with every IF/ELSE length byte (`verb_decode.py`); event gates read 0, 1 or 2 operand bytes before the verbs (table `$00fe84`); 61 of the 94 verbs occur in the two levels.
- Operand lengths of 92 of the 94 handlers measured under `callcap` (`verb_lengths_callcap.py`: ok 99, bad 0); the other two are verb 15 (assert by design) and 51 (level loader, tiled by a script).
- Effects of verbs 5, 6, 13, 85, 86, 38, 39, 40, 45, 62, 63, 64, 79, 81 (`verb_effects_callcap.py`: 45 of 45). Verb 5 adds 26 XP whatever its operand; verb 85 adds 26 or zeroes XP; the gold pile is verb 6; comparison ops are 0 `>`, 1 `<`, 2 `==`, else `!=`.
- Object 2 BUTTON's script under the real consumer: four items (16, 32, 28, 26) in the type-8 list give sound, teleport to room `$25` and four placements; fewer give message 246 (`treasury_gate_live.py`, 3 of 3 runs).
- The catalogue of what the scripts do (treasury, levers, gold piles, hazards, restoratives, level-1 teleporters) is in `secrets.md`; the verb names come from the handler bodies and the author's assert strings.

## Open, in priority order

1. **Reach the rest of the game** (old item 2, now cheaper): the scripts say what each lever needs. Drive object 86 (room `$22`) and 84 (level 1) from their rooms by walking; walk level 1 with `level1_loaded.snap` and the 13 level-1 teleport scripts (`scripts_level1.txt`: rooms `$0c $22 $34 $46 $52 $55 $5b`, the skulls and teleporters messages). What the type-8 list holds in play (how the player acquires 16/32/28/26, and which verb PUTs items in it: verb 35 is unused in both levels) is the first thing to find, by playing to a pickup with `watch` on the list at `(A5)+96` type 8.
2. **The Disk 2 builds**: decode the Disk 2 levels' scripts with `verb_decode.py` (needs a snapshot per level, made with `level2_load.py`; the 33 verbs neither level uses may occur there); overlays with two extra header words, a negative class-1 record, service table `$005eee` (29 entries), spell 28 as a real damage effect; the Empire `[t]` Disk 2 levels 3 and 5 look damaged (prefer Replicants).
3. **Verb semantics that are read, not run** (`secrets.md` "Open"): DELETE (0, 2), SHOW (1), GOANI/STOPANI/GOMOVE/STOPMOVE, the CREATE/PLACE family (36, 41, 44, 73, 84), the type-4 flag verbs (10, 27, 61), and verbs 9, 42, 60, 65, 66, 87, 88, 91. Prove each with a `callcap` memory delta as `verb_effects_callcap.py` does, or by running the level-1 scripts that use them (3, 4, 7, 11 are level-1 heavy).
4. What each event opcode is when the game queues it (only 5 is proven): find the queuers (`$00a474` and the writers to `152(A5)`) and inject each opcode for an object that has a block for it.
5. The unfinished items listed in `secrets.md` "Open": F2/F3 effects, the escape-number lock (1044), the class bytes of type-6 templates, which sound ids fire in play, `$0115a2` (a rotating checksum nobody calls), whether XP 60,000 is reachable, the first-room-load writer check from a cold boot.
6. Older loose ends: the room-census oddities of mechanics.md §67 (slots 69 and 71 are probably not rooms), STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

Retired: the 94 verbs' operand lengths and names (old item 1), the mid-instruction entries of the level-start verb (the table base was wrong, verb 51 is a clean entry).

## Known traps

- A callcap that "does not return" is usually a fatal assert on the poked state: verbs 8 and 75 assert unless the id is in the creature list at `396(A5)`, verb 29 needs A4 in valid RAM (it writes `1(A4)`), verb 79 with lo = hi divides by zero (`$011544`). The seeds are in `verb_lengths_callcap.py`/`verb_effects_callcap.py`.
- `callcap`'s `regdelta` shows A1 as `$snapshot->$final`, not relative to the preset: measure `final - preset`.
- Script operand bytes are hex in the dump but object ids print decimal (`#16`); the message text of verbs 28 and 72 is looked up through the packed table, so a stale snapshot prints `?`.
- The type-8 list is empty at CAVERN start (64 index words at type-8 descriptor +0, 4-byte data records `[id][+2]`); the four regalia have to be poked or acquired.
- Earlier traps still standing: a literal-pointer hit dismissed as alignment coincidence needs the real table base; a direct-call scan does not cover tables loaded per level; a "key does nothing" verdict must watch the handler's branches and flags (CLAUDE.md).

## Next session

`/resume cadaver` and start with open item 1: find how the type-8 list is filled in play (watch it while picking up an item), then drive lever 86 and lever 84 by walking, and run level 1's teleporter chain from `level1_loaded.snap`. Item 2 (Disk 2 script decode) is a mechanical rerun of `verb_decode.py` once a snapshot per level exists.
Prompt: `/resume cadaver`.
