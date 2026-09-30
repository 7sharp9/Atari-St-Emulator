# Cadaver: handoff

Updated 2026-09-30 by the 77th-pass session (the secrets and algorithms survey; two subagents, algorithms and the level code overlay). Commits: see `git log` for `cadaver: 77th pass`.

## Resume point

- Read `reversing/cadaver/secrets.md` first: it is the new reference for keys, saving, the text table, the assert layer, the level code overlay and its export table, the object-script consumer and 94-verb table, the LZHUF expander and level directory, the sound sequencer, the day clock and the RNG. Every script is in `reversing/cadaver/py/secrets/` (table in its README); all run from `M68000/` against `scratchpad/cadaver/gameplay_empire.snap` (CAVERN). Working data: `scratchpad/cadaver/secrets_out/` (indexed in `scratchpad/ANCHORS.md`).
- No emulator source changed, so no rebuild or regression-net run is needed.
- Uncommitted and not this workstream's: `M68000/sessions/README.md` (a pre-existing line-wrap edit), `Cadaver/` (disk images), `.obsidian/`.

## Proven this pass (counts in `secrets.md`)

Main-loop keys (F1 map, P pause, S/L save/load, F2-F4 toggles, Return/Space, H, C; F4 proven); the save price `max(1186(A5), (level+1)*50-45)` (4/4) and a full save/load round trip; the rank table and its overrun at XP >= 60000 (12/12); 67 assert sites; the LZHUF expander `$0118ec` (8/8 blocks bit-exact) and the level directory (two levels on the one-disk image, the second loads and renders); the three-voice sound sequencer (62/62 sounds, 38/38 scenario events); the day clock (`2166(A5)`, 90,000 VBLs per day); the RNG `$011544` (40/40); the level code overlay (timers 17/17, creature classes 10/10, events 4/4, potions 18/18, spells read from each body, MAP cast live); the export table and the teleport as service 8 (`export_service8.py`); the object-script consumer `$00fdbc` and the 94-entry verb table at `$00ffba` (lever scripts run live; verb 37 teleports; verb 51 loads level 1). Corrections written into the docs: mechanics.md §51-§56 (depacker exists, two levels), §69b, §23a/§64 (verb table base), ai.md §1-5 (it is the sound engine), item 10 (`2516(A5)` is max health).

## Open, in priority order

1. **Decode the 94 verbs**: operand lengths and names (only 37, 50, 51, 54, 55, 74, 75, 89, 90 are pinned); then write a script disassembler and dump all 212 blocks of the 174 scripted objects. This is where the walkthrough's room-to-room levers live (id 2 BUTTON, 86 LEVER, 56 STONE SHELF teleport; the TUNNEL lever id 144 has no teleport). Use `script_census.py`, `verb_table94.py`.
2. **Reach the rest of the game**: drive object 86 (room `$22`) and 2 (room `$25`) from their rooms, and the level-start verb, then walk level 1 (`level2_loaded.png`). Try creature rooms (slot 27 GIANT RAT) with the overlay's creature loop live; class behaviours are read at call level only.
3. **The Disk 2 builds**: overlays with two extra header words, a negative class-1 record, service table `$005eee` (29 entries), spell 28 as a real damage effect; the Empire `[t]` Disk 2 levels 3 and 5 look damaged (prefer Replicants); `disk2_levels.py`, the stride-28 record of the two-disk loader is inferred.
4. The unfinished items listed in `secrets.md` "Open": F2/F3 effects, the escape-number lock (1044), the class bytes of type-6 templates, which sound ids fire in play, `$0115a2` (a rotating checksum nobody calls), whether XP 60,000 is reachable, the first-room-load writer check from a cold boot (old item 4).
5. Older loose ends still standing: the room-census oddities of mechanics.md §67 (14 rooms with fewer `$00ce78` writes, slot 69's 102 hits, slot 71's missing terminator; slots 69 and 71 are probably not rooms), STOPACTI's `$f8ba`, the sconce's art source, the tile-stack direction (graphics.md 5e).

Retired: old items 1 (the interpreter's caller is `$00fdbc`), 2 (the "entity script" system is the sound engine, not a creature interpreter), 5/10 as stated (dispatch ids: the table base was wrong; `2516(A5)` is max health), 9 (Disk 2 does add content; the one-disk image itself has two levels).

## Known traps (new this pass)

- A literal-pointer hit dismissed as alignment coincidence needs the real table base (the `move.l #$6082,392(A5)` installer); "no caller" from a direct-call scan does not cover tables loaded per level; a "key does nothing" verdict must watch the handler's branches and flags, not one output (CLAUDE.md).
- A "no RNG" count taken from `mul`/`div` sites misses a shift-built LCG (`$011544`): search for a persistent word updated by shifts and adds, and for the routine that divides a 16-bit value into a range.
- Both agents' first reports disagreed with each other and with the parent (overlay size, RNG, `$01616c`'s role): every cross-claim was re-checked in the code before it went into `secrets.md`.
- `find_ram_callers.py` scans of the whole image saw 0 callers for the verb block and overlay routines because they are reached through tables: use `find_literal_ptr.py` with both 2-byte alignments and the pointer installer.

## Next session

`/resume cadaver` and start with open item 1 (the verb table decode and a script disassembler), then item 2.
Prompt: `/resume cadaver`.
