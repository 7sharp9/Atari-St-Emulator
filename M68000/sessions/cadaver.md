# Cadaver: handoff

Updated 2026-10-16 by the session that ended at commit `1100662` plus this handoff commit.

## Resume point

- Last commits of this workstream: `e1730f4` (the script linter, rules a-f, the level-1 object chains, key 508, VAR 17, the health route) and `1100662` (token L driven). No emulator source changed.
- Route work resumes from `scratchpad/cadaver/s93/routeL_promoted/run1/42_take709.snap`: room 43, health 89, poison 0, XP 1084, rucksack 570 (SLEEP), 680, 491 (CURE POISON, 3 doses), 709 (L), 224 (W), 338 (U), 493; token F applied (VAR 9 = 1). Rebuild chain (about 3 minutes, from `M68000/` with `export M68000_ROOT=$PWD ATARI_NOTRACE=1`): `l1/route_level1_room89.py scratchpad/cadaver/s90/run1/end_room90.snap A` (leg 24 is `A/24_back18.snap`), then `l1/route_health.py A/24_back18.snap B`, then `l1/route_tokenL.py B/27_out14.snap C` (all under `reversing/cadaver/py/secrets/overlay/action/exit_level0/`; index in that directory's README).
- Linter: `.venv/bin/python reversing/cadaver/py/secrets/overlay/lint/lint.py` (both level snapshots, about 1 minute with the push-site scan; `--no-scan` skips it). Its output and caches go to `scratchpad/cadaver/lint/`.
- Disk image: `../Cadaver/Cadaver (1990)(Image Works)[cr Empire][one disk].st` (relative to `M68000/`) must exist for every live script; it was missing on the Mac and was copied from Dropbox (sha256 `7d4641dd...ad5c`). Untracked, like the rest of `Cadaver/`.
- Agent working directories (reports in each `report.md`): `scratchpad/cadaver/s93/{lint_abf,lint_c,lint_d,lint_e,ringrefs,unread,bottle,var17,routeH,routeL}`.
- Hatari: build notes in `DEVELOPING.md` "macOS"; no Hatari build is current.
- Uncommitted: `Cadaver/` (disk images), `.obsidian/`, neither this workstream's to commit.

## Proven so far (counts in the docs)

Passes 77-92 (main loop, saves, ranks, asserts, overlay, the 94-verb script language, sound, action panel, level 0's road, level 1 to room 89: `secrets.md`, `mechanics.md` sections 1-12) and the verb 5 XP bug with its 26-byte fix on real Hatari.

This session (`secrets.md` "Dead and unreferenced content", `mechanics.md` section 12):
- **Linter** (`overlay/lint/`, 313 + 59 / 440 + 90 blocks): (a) 58 reward sites, 13 in room blocks the doc missed, 9,379 XP asked, 1,508 paid; (b) the 7 blocks on events 3 and 21; (c) no unobtainable key; (d) UI and room-suffix text nothing shows, the text table is per level (392 / 387 entries); (e) room 27's guard latch never set (live 2 / 0 CREATEs), room 82's countdown gate never matches (live), objects 638 and 688 test unset bits (read), the room-30 levers' counter form; (f) no bare ELSE. Each rule's census prints with it; controls for (c) 5 of 5.
- **Key 508** is delivered by the thrown bottle 465 (event 11, VAR 10 0 to 1, 508 into room 86) and opens `$72` (`l1_objects/bottle_throw.py`, control clean; room 86 entered by an injected teleport).
- **VAR 17 / object 70**: timer 7 takes 1 to 2 after 40,677,845 steps of natural play, THE BODY IS COLD rendered (`body70/`, control clean).
- **Level-1 objects** injected into the consumer (`l1_objects/`): SOULS RETURNED chain, scroll 378 (placed at power 0, recharged to 50), chest 129, casket 329 (STAMINA 475), lever 237 (STAMINA 535, maze flags).
- **Health route** (`route_health.py`, 27 legs): the CURE POISON 491, SLEEP 570 from the west (0 instead of -40), the cure drunk in room 30, room 14 left by `$16`: room 13 at 95, poison 0 (was 35 with a bite pending).
- **Token L** (`route_tokenL.py`, 42 legs, natural input): both SLEEP casts are needed (21 keeps 483 out, 22 deletes the posts), room 85 is a puzzle (777 on slot 374, chain 134 moves block 373), room 92's hunters cost 6, room 17's stair takes four jumps; room 43 at 89.
- The event-ring storage is `$39dbe`-`$3a3fd`; the push scan's 25 "absolute references" are data (`hits` 0 of 25 over 8M steps per level).

## Open, in priority order

1. **Room 43 back to room 89 with all four tokens:** door `$0b` through slot 206 (four applications, `o206.*@18`, YOUR WAY IS CLEAR), then room 9, 10, the shelf of room 89 by door `$0e`, lever 27 (icon 7), door `$01` into the pocket (rooms 4-8: STAMINA 219 +100, key 245, gems 716-718, key 251, door `$10`). Drive from `42_take709.snap` with `explore.py`; the way back from 43 is unwalked (rooms 44, 17, 15, 16, 18, 13 and the room-89 legs of `route_level1_room89.py` in reverse are the candidates).
2. **After the pocket:** the rest of chain (a) with the same suspicion: gem lock 719, keyholes, lever 275, the region teleports of rooms 70 and 71, levers 710 and 711, key 690, the UNLOCK DOOR scroll 407 and its cast (never driven), then START LEVEL 2 (mechanics.md: 137 actions; the urn and emerald throws at block 413 and the six captain objects into room 87's region are injected-only).
3. **Natural entries still injected:** room 86 (take 507 in room 24, shown by object 492) for the key-508 delivery; the casket 513 applied to the strong box 379 with scroll 378 inside.
4. **`explore.py` `C`/`K` lose joystick pulses once the rucksack holds five items** (a panel opened with zero grid pulses ignores them; `C223 Kc` left VAR 9 at 0 with the leg passing). The routes work around it with `I<oid>:<icon>`; find the cause in `explore.py`'s panel code and fix it there, and make `route_level1_room89.py` assert VAR 9 after token F.
5. **Tooling fixes from the 91st-pass review (needs Dave's yes; emulator changes go behind the section-6 net and a build into `bin/` after checking live sessions).** (a) `watch` misses word and long writes that cover an odd watched byte (`MMU.fs:260-264`) and all FDC DMA writes; (b) the REPL ends silently on a blank line, comment, unknown command or wrong argument count, and the batch drivers check neither return code nor stderr; (c) `bp`/`bpc`/`hits`/`until` compare the full 32-bit PC; (d) `hits`/`bpc` count PC arrivals; (e) `find_field_writers.py` and listing greps are text matches (the linter's rule (e) census inherits this); (f) `sec3_anim.py` accepts any `callcap` THREW as "asserted"; (g) disk state is outside snapshots and callcap's restore; (h) `m` on I/O registers has read side effects; (i) unknown encodings abort the process instead of vector 4. Stale text: `DEVELOPING.md` "Regression tests", the "not in MmuSnapshot" remarks, `Program.fs:682-685`, CLAUDE.md's `instructionsPerFrame` claim (VBL is fixed at 12,000 steps).
6. **Linter gaps:** rule (e) objects 638 and 688 are read-only (a live poke of the bit, as for room 27, would prove the gate is the only obstacle); rule (d) cannot see `$e020` or the Disk 2 levels; `$00e186` pushes the debug string's address as a text index (read; drive SLEEP with no creatures registered to see the banner).
7. **Still unread or undriven in the script layer:** `$fa62`'s class `$80`/`$81`/`$84` branches, event 11's two exclusions, ring-queue overflow, the anim ops `$f3 $f4 $fa $f7 $ff`, header `+3` bit 2 and `+15` bits 1, 5, 6, door `+7` bits 4-6 live, verb 44's launch nibble 15, the name of template 135, the Disk 2 levels' scripts; the poison tick schedule (ticks in room 15, not in 13 or 28).

## Known traps

- **The disk image must be at `../Cadaver/...[one disk].st`:** without it every `repl.py`-based script fails with "repl closed". Copy it from `~/Library/CloudStorage/Dropbox/Daves/ST games/Cadaver/` and check the sha256.
- **Drink CURE POISON only after leaving the biter:** in room 28 with the hound in contact the dose is spent and the byte is 10 again at once.
- **Room 18 after the room-20 detour:** the creature phase shifts; back north is clean only after a 450,000-650,000-step stand (525,000 and the rest poison).
- **Room 92:** 808 poisons, 807 (-3 a frame) comes out of wall 400 about 100,000 steps after lever 399; the teleports 401-403 need a vertical jump with x inside 41..43; going north at x lead 44 or more lets 807 push the hero off the column (health 2).
- **A door-graph chain is a hypothesis about geometry** (CLAUDE.md): room 85's walk-in was a four-step puzzle, room 21 needs the SLEEP cast before room 22 is entered.
- **`hold` ends after six stalled chunks**, shorter than some door waits: `Z<door>:<lane>:<chunk>`; a door needs the whole bbox inside its portal range; `M<door>` searches lanes (room 18's `$26` needs lane 20 going, 16 coming back; room 22's `$6f` lane 24 back).
- **zsh redirects an unquoted `GR:x>=24`:** quote every `explore.py` command containing `>` or `<`; zsh does not word-split `$c` either (pass arguments separately).
- **A render right after a room change shows the old room** for about 100,000 steps; `Q` leaves the hero airborne with nothing in front.
- **Health alone does not show a POISON bite:** check `2434(A5)` (`N` in `explore.py`).
- **`slot_map()` in `g2/lib.py` skips slot 0**: read `type8(r)['recs']`.
- **`lib/drv.py` does `os.chdir(ROOT)` on import:** absolutize snapshot arguments before importing it (routeL lost snapshots into `M68000/`).
- **`timeout` does not exist on macOS;** do not `pkill` by pattern: stop your own run with TaskStop.
- **`H.obj()` in the verbs2/graph harness goes stale after a DELETE**; poking a type-8 record needs its index entry.
- **Two snapshots sit in the `$0117c4` fatal-assert spin:** `s86/a7/snaps/gomove31.snap`, `s86/a6/snaps/room69.snap`. Verb 41 PLACE with no free space asserts and hangs.
- **Hold timing:** a hold starts moving about 40,000 steps after the press, one cell per about 25,000 in level 1; a hold begun while falling never moves; a panel left open freezes every hold; jumps need a run-up and the takeoff direction is fixed.
- **Earlier standing traps:** injected-state results show a mechanism, not a route (label them); health only goes up by a verb 45; door words are hex door numbers; the REPL prints at most 4096 lines; REPL `w <addr> <8 hex>` writes four bytes; verb 66 with a class other than 10 kills the REPL.

## Next session

`/resume cadaver`. Drive open item 1 from `42_take709.snap`: back toward room 89, apply W, U and L to slot 206 (VAR 9 to 4, door `$0b`), then rooms 9 and 10, the shelf by `$0e`, lever 27 and door `$01` into the pocket for STAMINA 219. Keep a `route_*.py` driver per stretch with two identical replays, and assert VAR 9 after each token. Parallel agents worked well for this workstream: route stretches, live proofs of linter findings (item 6) and the open item 4 fix can run side by side in separate scratchpad directories. Ask Dave about item 5 first.
