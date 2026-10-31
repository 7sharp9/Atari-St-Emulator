# Cadaver: handoff

Updated 2026-10-31 by the session that ended at the commit of this handoff.

## Resume point

- Last commit of this workstream: `86b7d47` (push rule, `route_pocket2.py`, `send_joy`, room 7's drain).
- The shared `bin/` DLL now includes `5636dc5` (ACIA keeps its last byte). Under it a joystick packet sent as one `kbd ff XX` burst leaves a phantom key in `$18b34` that blocks the joystick (mechanics.md section 14). The drivers' `send_joy()` works around it. The emulator fix was reported to ws-emulator, not checked: the re-raised channel-6 interrupt should be dropped once the FIFO has emptied.
- End snapshot: `scratchpad/cadaver/s97/fullA/10_to1.snap` (room 1 at (41..47, 30..36), health 189, poison 0, key 251 used, `$10` open; rucksack 391, 570, 680, 491, 493). Rebuild (about 4 minutes from `M68000/` with `export M68000_ROOT=$PWD ATARI_NOTRACE=1`): `uv run python reversing/cadaver/py/secrets/overlay/action/exit_level0/l1/route_pocket2.py scratchpad/cadaver/s95/pocket/full/33_to6.snap <OUT>`. Run B (`s97/fullB/`) is byte-identical (11 of 11).
- `33_to6.snap` and the rest of the s95 lineage are records from the old input timing. Replaying `route_pocket.py` with `send_joy` passes legs 1-24 and then fails leg 25 (`drop89`: `=x28` ends at 30). Its 24 snapshots match none of the old ones (`s97/pocket_new/`). So the chain before room 6 does not rebuild today (Open 1).
- Records of this session: `s97/push/`, `s97/pushgate/north.snap` (push A/B), `s97/r3/` (the forks the route came from), `s97/build0b9/` (emulator built at `0b92317`, for input A/Bs).
- Disk image `../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (relative to `M68000/`), untracked. The root `Cadaver/` folder also holds `disk1_*`/`disk2_*`; not committed.
- Uncommitted work left behind: none of this workstream. `M68000/scratchpad/ANCHORS.md` and the other games' files are other sessions' changes.

## Proven so far (counts in the docs)

Earlier passes: `mechanics.md` sections 1-12 (main loop, saves, ranks, overlay, the 94-verb script language, level 0's road, level 1 to room 89, the health route, token L, rooms 9, 10, 89's shelf, room 4's lift, the surveys of rooms 5, 7, 8).

This session:
- **Push rule** (section 3, "Pushing"): `$ed5a` charges each object in the chain its template weight (byte 13) against the strength `2144(A5)`: 50, or 199 between drinking 480 and 7.0 to 7.5M steps after `33_to6.snap`. Post 380 weighs 140, lift 2 weighs 40. Same-snapshot A/B with `l1/push_probe.py`: refused at `$ef84` (budget -90) at 50, applied at `$ef94` at 199. The previous session's failed pushes ran after the strength had expired.
- **Room 6 driven** (section 12): `l1/route_pocket2.py`, 10 legs. Diagonal push, flask 219 drunk (+100), key 251 taken, keyhole 698 opens `$10`, room 1. Two runs identical. Legs 1-6 use 6.65M steps of the strength window.
- **Room 7's drain** (section 12): room 7's region-1 block (event 15) runs HEALTH -4 while tile 634's bit 0 is clear. Writer `$010cc8` was hit 4 times, called from the verb loop (`$01064a`) with D1 = 634. The SLEEP answer (event 24, gate 23) sets the bit and queues records for the walleyes. The cast itself is not driven.
- Design digest: the pushable-blocks line now carries the strength rule.

## Open, in priority order

1. **Re-promote the chain before room 6 under `send_joy`.** First fix `route_pocket.py` leg 25 (`=x28` on room 89's shelf now ends at 30: try a shorter `tapn`, or tap from the other side). Then run legs 25-33 and route_pocket2 on top, two runs each, every snapshot `cmp`. Do the same for `route_tokenL.py`/`route_health.py` if anything upstream is to be rebuilt. If ws-emulator fixes the interrupt instead, re-check whether the old one-enqueue drivers reproduce the s95 snapshots byte for byte.
2. **Room 7's gems.** This needs the way from room 1 to room 5: room 4's lift raised and `$07`, key 245 off cap 12, `$06`. Read 570's remaining charges from its record (casts so far: rooms 1, 21, 22). Cast SLEEP in room 7 and check that 634's bit 0 gets set and the drain stops on the same walk as `r7probe.snap` (control: no cast). Then take gems 716 and 717 and put 716, 717, 718 on gem lock 719 in room 2.
3. **Room 8's chests** with scroll 458 (Unlock Chest, *inferred*): select it, FIRE at a chest, for two moneybags, wand 478 and flask 475. Also find the gold word (`1188(A5)` read 0 after the sack).
4. **The 91st-pass chain from room 1**: `graph/plan_full.py` with `CAD_LINEAGE_SNAP=s97/fullA/10_to1.snap`, covering key 538, lever 275 and rooms 50, 70, 71, 93, 82 (key 690) and 52 (scroll 407).
5. Tooling leftovers: `explore.py` `C`/`K` lose pulses with five or more rucksack items (use `I`); `m` on an unmapped address; negative hex operand; `snd_proof.py:64`; the write-protect tab; linter gaps.

## Known traps

- **Hero ignores the joystick**: read `$18b34` (the game's key byte). Non-zero means a phantom key from a burst. Send a lone break byte or rebuild with `send_joy`, and never `kbd ff XX` in one command.
- **The strength window is about 7M steps from `33_to6.snap`** and is the binding constraint in room 6. Every new leg there prints `steps`/`strength`; keep pushes first.
- **A `G` goto that meets an obstacle holds for 1,200 chunks (6M steps)**: use exact taps (`=`) or `H` where an overshoot can touch the post, the keyhole or a wall object.
- **The post's band must not cover an item's landing row** (flask y 57..59, key y 74..76), and for the key it must be exactly y 64..72. `P` stops on the condition; the 30,000-step settle sometimes adds one cell.
- **An item walked into a block pushes both** if the weights fit (the flask moved the post to the south wall).
- The previous traps stand: the first hold after a reload starts about 120,000 steps late; the `255` rects mid-move; small items pushed ahead of a walk; zsh `=x23`; `slot_map()` skips slot 0; room 4 one-way by `$01`; the Return grid's lost first pulse; `lib/drv.py` chdirs on import.

## Next session

`/resume cadaver`. If ws-emulator has landed the channel-6 fix, run the old one-enqueue drivers on `33_to6.snap` first to see whether old snapshots reproduce. Otherwise do Open 1: fix `route_pocket.py` leg 25 under `send_joy` and re-promote legs 25-33 plus `route_pocket2.py` (two runs, `cmp`). Then room 7's SLEEP cast (Open 2) on a fork from room 5.
