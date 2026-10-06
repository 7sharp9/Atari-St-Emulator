---
name: reverse-engineer-st-game
description: Workflow for reverse-engineering a commercial Atari ST game against this repo's F# 68000 emulator and tools/, boot it, drive it to gameplay, map control flow and graphics, and (if needed) reverse game logic via the snapshot+callcap differential-test harness. Use when asked to analyse, reverse-engineer, or "look at" a new Atari ST disk image/game, or to document or port its mechanics/graphics.
---

# Reverse-engineering an Atari ST game

Each analysed game lives in `M68000/reversing/<game>/` and has the same shape of artifact: a boot-to-gameplay narrative (README), a `.sym` file, callgraph/cfg dot+svg, screenshots at milestones, and topic docs (`mechanics.md`, `graphics.md`, `ai.md`, `economy.md` as needed). Reproduce that shape for a new game rather than inventing a format. Existing subjects: `a_013`, `supersprint`, `powermonger`, `populous`, `cadaver`, `impossamole`, `black_tiger`, plus the MAME arcade pair `finalfight` and `crudebuster`.

The goal is the game's **architecture and algorithms**, not a catalogue of fields: the data structures behind rooms/levels/entities, the dispatch mechanisms (state machines, per-frame fan-out, event/message passing, any bytecode or script interpreter driving content), and the algorithms behind the core mechanics (pathfinding, collision, AI decisions, procedural generation). A topic-doc section is worth more when it names the general mechanism a fact is an instance of. Mechanisms proven generic in one game (a per-room bounding-box proximity scan) are worth checking for in the next, since these games share engine idioms.

## Scope: what transfers

This skill is Atari ST / 68000 specific. It leans on the F# 68000 core, the real Hatari binary as an oracle, and `tools/` whose opcode tables and graphics decoders assume ST hardware (planar bitmaps, `$ffff8240` palette, GEMDOS/XBIOS traps). Another ST game: full reuse. Another 68000 platform: the CPU core and disassembler technique transfer, the memory map, OS calls and graphics formats do not. Outside 68000, only the method transfers (milestone ladder, snapshot+callcap differential testing, README template, gate discipline). Arcade boards run under MAME, not this core: `reversing/finalfight/` (CPS1) has a headless MAME Lua `callcap`, a ROM-dump script and the MAME quirks (`CURPC` vs `PC`, find a set by CRC); `tools/disassemble.py --rom <flat image> --base 0` decodes a dumped 68000 space.

## 0. Setup

- Get the disk image legally; do not commit it or the cracked archive. Record sha256 and size in the README (`supersprint/README.md` is the template).
- `unzip "<game>.zip"` gives a `.ST` FAT12 image. `./run.ps1 -DiskA "<game>.ST" boot <N>` (or `--disk-a` on a bare `dotnet exec`, with `ATARI_NOTRACE=1`).
- Orphaned `dotnet` processes make a resume look non-deterministic, but another Claude session may share the checkout: check `tasklist | grep dotnet` (`ps` on the Mac) and ask before killing anything. With a second session active, never `dotnet build` into `bin/` (it replaces the DLL under the other session); use `./run.ps1 -NoBuild` or bare `dotnet exec`.
- Create `M68000/reversing/<game>/` and an untracked working dir `M68000/scratchpad/<game>/` for extracted files, snapshots and decompiles (`scratchpad/*` is gitignored; `reversing/populous/py/popcfg.py` shows the `$<GAME>_WORK` path pattern).
- **Classify the program before choosing a method.** Extract the files (`tools/extract_disk.py`, or boot and trace `Fread`), find the main executable and check for magic `$601a` and plain text. Count `4e56` (LINK A6) words in TEXT: hundreds of LINK frames, `N^NuNV` runs in the strings and C-runtime strings (`CON:`, `MMARGV=`) mean compiled C, so take the decompile route (3b), which turns the program into readable C in minutes. Packed, crypted or hand-written assembly (PowerMonger, Impossamole) means the trace + callcap route only. Count before deciding: Super Sprint looks hand-written and is compiled C (263 frames).
- **Read the first bytes of every file on the disk, including those nothing references.** A file the loader never names is not data until its header says so. PowerMonger's `DATA\SPRITE40.DAT` is in no loader table and is a self-extracting GEMDOS program holding the real game build with the linker's symbol table (`reversing/powermonger/powermonger_orig.sym`, `py/s40_symbols.py`). For each file check `$601a` (and the symbol-table size at offset 14), a packer magic (`Ice!`), or a depacker stub (a 601a header then `movem.l d0-a7,-(a7)` and a bit-tree decoder). Align an unpacked text against a RAM snapshot with 16-byte windows: one constant offset means the same build.

## 1. Trace the boot, find the walls

`ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 dotnet exec bin/Debug/net8.0/M68000.dll <N> --disk-a "<game>.ST"` narrates `Pexec`/`Fopen`/`Fread`/`Setscreen`: ground truth for what the game loads and when. Paste the summary into the README.

No `\AUTO\` folder and no bootable sector means the game is launched from the GEM desktop. Make a headless copy instead of driving the desktop:

```
tools/add_file_to_disk.py game.st --from-disk LOADER.TOS --name LOADER.PRG --remove LOADER.TOS --remove DESKTOP.INF --auto --out game_auto.st
```

`--remove` frees space on a full disk; the game never reads `DESKTOP.INF`. The `--name` must be a valid 8.3 name: the tool accepts a longer one, but TOS's `\AUTO\*.PRG` scan then silently finds nothing and boots the desktop. The GEMDOS trace shows `Fsfirst("\AUTO\*.PRG")` with no following `Pexec`; check for a `Pexec` of your file before concluding the game does nothing.

An unimplemented opcode or EA mode is an instruction wall. Fix it through the shared EA decoder (`x.ResolveEa`/`x.ReadEa`/`x.WriteEa`); new titles mostly hit missing addressing modes on existing instructions, not new hardware. Each fix is its own commit behind the regression net (section 6).

## 2. Drive it to gameplay

Progress attract, menu, gameplay by injecting input: REPL `kbd <hex>...` and `mouse move|down|up`, or `ATARI_KEY_INPUT`. Read the game's own IKBD handler first (disassemble around the vector it installs, typically `$118`/`$120`) to learn its packet format and key mapping, then script the exact bytes. Super Sprint's README section "Driving it into a race" is the model. Once the drive works, write it as a REPL script (`reversing/<game>/drive.txt`, fed on stdin) and prove it deterministic: run it twice from cold boot and `cmp` the snapshots.

**Input rules**

- **Make and break in separate calls.** Send a key's make and break codes as two `kbd` calls with a real `s <n>` between them (`kbd <make>`, `s 3000000`, `kbd <break>`, `s <n>`), not one `kbd <make> <break>`. A game with its own interrupt-driven IKBD ISR drains both bytes in the one interrupt that follows, so its main loop never sees the key down and the input is dropped silently (Cadaver README, "Keyboard discipline").
- **A hold must span a full poll cycle.** The status byte is a raw level; a pulse shorter than the game's poll period can fall between two polls and never register. Hold at least one full VBL frame (`instructionsPerFrame`: about 12,000 to 15,000 steps idle, about 24,000 in Impossamole's gameplay rooms, so 30,000 is the safe hold) before releasing, and prefer a hold longer than the longest poll period. Lead the packet with an idle delay, and when a "no-op" and a "success" look identical from position and damage alone, watch a signal that only changes if the mechanism fired (a counter, a one-shot flag, a state transition).
- **Held fire may be software-debounced.** A game can cache the previous frame's raw byte and clear the current bit when it was already set (rising edge only), so a constant held packet reads as pressed for one frame. Read the consumer for a cache-and-compare before concluding a held test says anything about repeat rate, and to fire repeatedly alternate pressed and released packets (Impossamole `$227ef`/`$227f5`).
- **Check for a busy flag.** Some games skip the per-frame input read while the controlled object is mid-animation (Impossamole hero base+101). Run several frames past the packet: the effect (a walk cycle, a state transition) can take multiple frames to show even when the input was read on the first.
- **Census every comparison against a key or joystick pattern after the game's key-read service before poking toward later levels.** Black Tiger ships a level skip (joystick 1 up+left+fire `$85` while ClrHome is read arms flag `$17826`, then each Return advances a level), found by reading the key consumers to their next control-flow instruction (`reversing/black_tiger/secrets.md`). The same census proving there is no cheat word or debug key is a result worth a line in the doc.
- **Release or change a held direction at the game's own state transition, not at a guessed step count.** A held up that re-enters a jump every time the hero lands can bounce through a hazard repeatedly. Checkpoint the movement-state byte every 100,000 to 200,000 steps to find the step range where it flips (jumping to falling), then switch input exactly there. Impossamole: `$227f3` flips from 2 to 3, the signal to drop up.
- **Keyboard polled directly from the ACIA** (`cmpi.b #$39,$fc02.w` / `bne` back) never sees a key here, because `MMU.fs` pops the FIFO on the read and returns 0 when empty, so TOS's ISR takes the byte first. Check whether the game uses TOS Bconin or the ACIA before concluding input is broken (`reversing/black_tiger/`'s `drive.txt` pokes the branch).

**Reading a state transition.** The routine a transition branches to is often one-shot entry setup, not the per-frame body, and the two can be different addresses even when the entry falls through into the body. Reading only the entry's linear continuation to its first `rts` can look complete and describe nothing that runs from frame 2 on. Find the per-frame body with `hits <n> <candidate addrs>...` over several VBL frames of held input: hit counts in the tens (not 0 or 1) mark the real per-frame handlers. Impossamole's jump entry `$c742` plays a sound, latches facing and falls through into `$cbbc`, which applies the displacement.

**Chaining segments.** When driving a long input chain from snapshot to snapshot, save every segment's `.repl` under its own name and tag its snapshot. The finished walk is the concatenation of those files, and its final snapshot must `cmp` byte-identical to the interactively reached one. A script rebuilt from memory fails replay on one off-by-one nudge count.

**A/B discipline for "does this input matter".** Do not infer an input's effect from trials that also vary the step count. Run the A/B from the same snapshot with the same step budget, once with the input and once without; only that difference counts. A screen that looks different says only that something changed. The same applies to gameplay: diffing a held-input frame against the pre-input frame, instead of a same-length no-input control, reads ordinary animation as input-driven movement and cannot say which sprite moved. Do not name a sprite "the hero" without checking that it moves independently of the background in the control.

**A movement that reaches its target is not thereby safe.** Watch health and every per-object status field (busy, cooldown) across the whole maneuver, not just the end position. A jump or dash can clip a hazard mid-arc, and the game may gate the visible symptom (a death animation, a lockout) on a later condition, so the damage and its symptom are tens of thousands of steps apart and the symptom looks like an unrelated soft-lock at the landing spot.

**Several independent trials failing the same way point at one shared mechanism.** Three varied inputs ending at the same position means the game is doing something uniform at that boundary: disassemble around the boundary constant (`cmpi.w #$c0,...`) instead of trying a fourth variation. A hero pinned at one screen coordinate is usually a camera-follow trigger, not a wall: `watch` the scroll counter across the trial and find its writer with `find_field_writers.py` (Impossamole `x=192` was `addq.w #2,$227b6`). Before trial-driving to find what is "past" a spot, dump the data structure the scroll/loader reads (the whole tile map, room/exit tables, spawn list are usually resident from the start).

**A fixed step count does not give a rest position.** A snapshot after holding a direction for N steps can be a mid-motion frame. Check the mover's state byte reads idle, or run further and confirm the position stops changing, before writing up where an input "walks to". Likewise a `bp`/`bpc`/`watch` that finds nothing inside its budget proves nothing past that budget: re-run with a budget well beyond the maneuver's known duration, and when a later check does hit, read `A0` and the contact address to learn which object caused it.

**Screenshots.** `python tools/snap_render.py x.snap x.png` at each milestone (title, menu, gameplay). It reads base, rez and palette from the shifter, so double-buffered games come out right. Keep every screenshot that proves a milestone; drop exploratory ones before committing.

**Mouse-driven menus.** The game keeps its own pointer and `mouse move dx dy` sends relative packets (keep each |d| <= 127). Before clicking, find the pointer in a screenshot and do the arithmetic in 320x200 space (screenshots are often saved at 2x). Better, read the menu's hit-test code (button x/y bands) and the game's pointer variables and move exactly; `reversing/populous/py/popdrive.py` plans clicks that way. Screenshot after the move, before the click.

**Before a long `u <addr>` or `bp` run, read the loop around the target** to confirm it runs when you think it does: a title-menu routine that runs once per intro cycle burns hundreds of millions of steps if the run starts after it.

## 3. Map control flow

Once a step range covers the behaviour of interest:

```
ATARI_TRACE_EVENTS=<game>_events.bin ATARI_TRACE_GEMDOS=1 dotnet exec bin/Debug/net8.0/M68000.dll <N> --disk-a "<game>.ST"
python tools/trace_cfg.py <game>_events.bin --steps <lo> <hi> --range <lo> <hi> --names <game>.sym \
    --callgraph callgraph.dot --blocks blocks.txt
python tools/trace_cfg.py <game>_events.bin --steps <lo> <hi> --range <lo> <hi> --names <game>.sym --cfg cfg.dot
dot -Tsvg callgraph.dot -o callgraph.svg
dot -Gnslimit=1 -Gmclimit=1 -Tsvg cfg.dot -o cfg.svg
```

Scope `--range` to the program's own text segment (from the `Pexec` basepage decode); for `--cfg`, one dense region at a time, since a whole-program CFG is unreadable. Build the `.sym` sidecar (`addr<TAB>name`) incrementally as routines are named; it feeds `trace_cfg.py --names` and `disassemble.py`.

`disassemble.py --snap <path> <addr>` or `--linear <addr> <n>` reads real instructions. `--callers <addr>` scans only the TOS ROM, not the loaded program: grep a `--linear` dump for `jsr $<addr>.l` instead. To count calls per function over a trace, filter the event log for kind 3 (call) records by target: the once-per-frame routines are the best seed for everything after.

**The whole-image listing.** `disassemble.py --snap <snap> --all <lo> <hi> > game.asm` writes the loaded image as one listing that carries on past jump-table stops. Make it once per session and grep it for callers (`jsr $xxxx.l`, `bsr $xxxx`), for every writer of a field (`',44(A[0-7])$'`, then the `-N(An)` forms for pointers into the middle of a record) and for every reader of a global.

- A claim that nothing, or only one routine, writes a field needs that grep plus a read of each writer's whole block: the next instruction can overwrite the value (PowerMonger `$2452` copies a byte into a unit and `$245c` overwrites it four instructions later).
- A pre-existing `.asm`/`.c` export is not automatically whole: Populous's `pop_ad58.asm` stopped at `$1d462`, short of the text segment's end at `$21464`, and two "no writer" verdicts were wrong. Confirm its last address reaches the end of the text segment (the PRG header's text size) or re-run the tool.
- An operand-text scan cannot see a block clear or copy (`lea $3f364,A0 / clr.l (A0)+`) that reaches the field from a lower base. Before "display only" or "only writers X and Y", poke a marker into the field and `watch` whether it vanishes (`reversing/powermonger/py/aggr/scan_block_writers.py` lists such loops).
- `tools/rdis.py` does not follow longword state tables (`jsr (A0)` after `movea.l 0(A0,D0.w),A0`), so it is no basis for "who calls Y".

**Static scans for "does anything reference X".** In order of escalation, all taking a snapshot and an address, and each validated first against an address with a known caller:

1. `tools/find_ram_callers.py <snap> <addr>...`: direct `bsr`/`jsr`/`jmp`/`bcc` whose decoded text names the target.
2. `tools/find_literal_ptr.py <snap> <addr>`: the target as raw data (an abs-long `jsr` operand or a table entry, any alignment). The real table base comes from the code that installs the table (the `move.l #<base>,<field>` and the routine that indexes it), not from neighbouring bytes: try both 2-byte alignments before dismissing a hit as coincidence.
3. `tools/find_jump_table_hit.py <snap> <addr>`: the target as a displacement-table entry (`target - table_base`, the `add.w D0,D0; adda.w 0(An,D0.w),An; jmp (An)` idiom) against every literal address any instruction names as a candidate base.

"No caller anywhere" from these means no direct call. A block whose routines all read as uncalled is usually reached through a per-level pointer table (an overlay with an export or dispatch table): look for the routine that does `movea.l <field>(A5),A6 / jmp (A6,Dn)` before writing "dead". "Never reached" holds only for the roll and address list it was measured with (PowerMonger routines "synthetic only" in preview rolls ran hundreds of times in Play Random Land runs), and a census file with no line for an address says "not looked for", not zero.

**Resolving what a dispatch entry does.** Bound the forward walk: walk the entry's own straight-line body (an unconditional `bra`/`jmp` is a same-routine continuation, since error stubs are often reached through one or two chained `bra`s) and follow a conditional branch found there exactly one level further. An unbounded transitive walk wanders into shared code and attributes handlers to an unrelated string (`py/verb_opcode_map.py`, Cadaver `mechanics.md`); an implausibly high visited-block count is the tell.

**Real entry or a bounded-walk false positive landing mid-instruction.** A target whose first instruction looks implausible (`ori.b` on an address register, a `movem.l (A7)+,...` with nothing pushed) is a real entry only if (a) that instruction is provably harmless (any register it touches is not read before the next real branch) and (b) no push or pop is skipped. A target 2 bytes into a `movem` mask word or into a `lea` operand corrupts the stack or leaves a register unset. A jump table's word arithmetic can be exactly right while the target decodes as garbage (an F-line opcode) with clean code resuming 2 bytes later: check whether the next instruction onward reads as a coherent routine before discarding it as misaligned.

**A target that looks like noise may be deliberate.** Copy-protection code looks like garbage under a blind static scan (self-installing exception-vector handlers, deliberately executed reserved opcodes as CPU-detection probes, trace-mode single-step decrypt loops). Step the live CPU through it before calling it stale data misread as code: a Rob Northen protection chain in Cadaver hid two real emulator gaps (a reserved opcode and the trace exception).

**Name a routine from its own body.** Read it to its first branch before writing its role into a doc, and grep for the label before reusing it. A routine seen running at some PC may only be the tail of a neighbour: Impossamole's `$1c6de` was "the shared depacker" because PC was seen near `$1c68e`, but its first instructions are `Fopen` (`move.w #$3d`, `trap #1`); it is a file loader and the depacking is a crack hook in low RAM (`reversing/impossamole/secrets.md`). When a doc quotes a listing with `...` eliding part of a routine, re-disassemble it in full before reasoning about its structure: the elided part is often the loop count or register mask that decides the answer. A `movem.l (A0)+,list` / `movem.l list,-(A1)` block copy reverses the order of whole transfer chunks (relative byte order within a chunk is unchanged), which explains buffers that look like noise at the obvious raster width.

**Why a routine does nothing for an input.** Read to its next control-flow instruction (branch, jump, rts), not to the first `jsr` whose target looks self-contained. An unconditional `jmp`/`bra` right after that call can be the mechanism: Impossamole's fire handler reads as dead until `jmp $17c9c`, the world-select re-entry.

## 3b. Decompile a compiled-C program

1. `python tools/prg2img.py GAME.PRG game.img <text>`, with `<text>` the runtime TEXT address from the Pexec trace, so every image address equals a runtime address.
2. `python tools/disassemble.py --rom game.img --base <text> --linear <text> 30000 > game.asm`: a whole-program linear sweep (C code is contiguous; small data tables embedded in TEXT decode as garbage).
3. Headless Ghidra (its install paths on each machine are in `CLAUDE.md`, "Shell pitfalls"): `tools/ghidra/DecompileAll.java`, usage in its header. It writes every function to one C file and applies your `.sym` names, so re-run it whenever the `.sym` grows. Compiler runtime helpers that return through stack slots (Alcyon `lmul`/`ldiv`) need a purge override or callers fill with `puVarN + -4` noise; trap wrappers get a varargs override. A handful of very large functions will lose stack tracking anyway: read those from the asm.
4. The decompile is a reading aid, not proof. Trap-call argument lists come out wrong; confirm OS calls in the asm. Every behavioural claim still goes through section 5.

## 3c. Fan out once the map exists

After the per-frame routine list, the decompile and a gameplay snapshot exist, the topic areas (graphics, world and terrain, people and mechanics, AI) are independent enough for parallel subagents. A mature workstream fans out by open item instead: one agent per handoff "Open" item, each with a start snapshot and a match-count gate, about an hour apiece. A dependent item starts from a labelled poke and is chained afterwards by a `SendMessage` follow-up ("rerun from the other agent's snapshot, produce one combined replay, `cmp`").

**The brief.** One shared `BRIEF.md` in the working dir holds: program layout and base; runtime-helper conventions; the per-frame routine list with call counts; known structures; artifact paths; the snapshot list; the REPL cheat-sheet; the required output (`<area>.md`, `sym.txt`, scripts); and HARD RULES.

- HARD RULES: no build, no git, no taskkill; write only under `agents/<area>/`; cite addresses; label inferred claims; prove behaviour against the emulator with a match count; wait for or stop every background process it started before the final message (a finished agent's emulator run held `bin/`'s DLL and blocked the parent's build).
- Name the tool index (`M68000/DEVELOPING.md` "Other tools"): six agents each wrote their own recursive-descent lister before `tools/rdis.py` existed.
- Put addresses and symbol names in the brief, not roles. Roles read off symbol names were wrong in every area of one brief (terrain build with roads as causeways, panel templates, a Timer A sample player, masked blitters). Write "role unknown: name it from its body".
- Take addresses, strides and struct offsets from the game's constants module and the docs' proven sections, never from memory: a brief with the object table wrong made every agent correct it.
- Ask for each agent's start snapshot, the exact command, expected output, labelled pokes, and the doc sentences it contradicts. The contradictions list keeps the topic docs honest.
- Scripts are written as they will be committed: locate the repo root by walking up to the directory holding `tools/rdis.py` (or `M68000_ROOT`), never a literal path or a fixed `../` count (promotion changes the directory depth); write data under `$<GAME>_WORK/<area>/`; keep temp files in one named scratchpad dir; import the game's `py/` modules from one directory up. Then promotion into `reversing/<game>/py/<area>/` is a plain copy. Name the promoted directory anything but `build/` (`.gitignore` ignores it and the scripts stay untracked).
- Tell agents that inject into a ring queue to append at the write pointer (`304(A5)` for Cadaver, advanced by 8, with `1154(A5)` += 1): an entry written at the read side is overwritten by the game's own pushes.
- Give an exhaustive-audit agent a budget: a wall-clock limit in the prompt, an interim report at about an hour, and the out-of-scope open questions listed.
- Agents that time an A/B share the machine with other agents and sessions. Tell each to record `uptime` per run, interleave the variants, report median and min, and call a gap under about 5% noise unless it repeats in every pair. One MAME per agent, each in its own run directory.
- Subagents cannot write report files: ask for the report as the final message and save it as `agents/<area>/report.md` the moment it arrives.
- Append to the brief rather than re-briefing when something new is learned mid-run, and re-read your own addenda for over-claims.
- If agents die on an API or network error, resume each with `SendMessage` to its agent id; they keep their context.

**Reconcile before merging.**

- Verify a cross-agent contradiction yourself before issuing a correction, and settle a name clash from the routine's body. Dump the table and read the bodies: two agents read the same Black Tiger table differently until `m cf20 88` showed where each kind went; three HUD routines were named in swapped order until the bodies (which variable, which icon) decided it.
- Merge the `sym.txt` files with `tools/merge_sym.py`. It lists addresses given different names: most are synonyms, but real disagreements hide there (Populous `$219b0`, "two-player" vs "one-player" flag, settled in the code). Read the clashes where the two names describe different things.
- Cross-check each doc's open questions against the others' answers, spot-check each headline match count by re-running its script, and check live-behaviour claims against snapshots.
- Re-run every agent gate from fresh callcaps (no `reuse`), from the promoted location, before committing; then run every older gate of that module again. A promoted script whose docstring or default path still names the agent dir fails silently on another checkout. Corpora stay in scratchpad, listed in `scratchpad/ANCHORS.md`.
- When two agents transcribe the same callee, keep one version and run both corpora against it: the cross-check is free.
- Resume each agent with `SendMessage` for the merge work instead of redoing it: it knows which doc sentences it contradicts. Lift the "write only under your directory" rule for exactly the promoted paths and the doc sections. Seed the topic doc with one placeholder heading per agent first, and tell them to use `Edit` with small unique strings, never a whole-file rewrite; afterwards check every agent's section is still present.
- Chained segment scripts: a leg that costs nothing in its own agent's run is proven only for that lineage. Roaming creatures move as a function of the steps spent inside their room, so a fixed wait is a lottery that differs per lineage. Run each segment from the previous segment's actual end snapshot, then the whole chain twice and `cmp` every snapshot. Wait by reading the creature table, not by counting steps. Check "an id is selected" against the game's own item word (`1236(A5)` in Cadaver), not the cursor cell.

## 4. Find and decode the graphics

`gfxview.py <snap> --contact ram.png` first: a whole-RAM overview that shows where decoded assets sit. Then `--html` for an interactive per-region viewer (base, width, rows, bpp, palette, zoom) to pin down the format (planar, chunky, tiled). `ATARI_GFX_SIDECAR=<path>` during the run records every XBIOS `Setpalette`/`Setscreen` so gfxview can auto-mark candidates. Write findings to `graphics.md`, not just screenshots.

- **For hand-written assembly the contact sheet shows only bands: read the code that draws.** Impossamole's contact sheet located nothing; the room-install routine and the tile and sprite blitters gave the whole chain (level map, block definitions, tile bank; base and stride of each table; the row layout, where the blitter's `or.l x4` for the mask gave the 32px sprite format; the transparency rule). Then prove each format against the live screen (`reversing/impossamole/py/tiles.py --check`, `sprites.py --check`: slide the render over the screen and report the match count per snapshot).
- **Take a sprite bank's extent from the data, not from a stated end.** Scan for the last non-zero frame (and look past it) before writing "N frames". Impossamole's bank 2 was documented as 140 frames and runs to 171, and the missing 32 were half the enemies.
- **Render and commit the asset once a format is confirmed.** A decoded spritesheet, tileset, icon set or palette swatch goes in `reversing/<game>/` (or a `graphics/` subdir) as a real PNG, table-indexed in `graphics.md` or the README's files table next to the gameplay screenshots. A coordinate and a bpp value in prose is not the deliverable; the picture is.
- **Before declaring a sprite or object catalog "the whole background", put its contact sheet next to a real gameplay screenshot.** A struct-driven, byte-exact catalog can still be structurally partial: Cadaver's 22-entry object array (torches, barrel, boat, chest) was correct and fully proven, yet the terrain lived in a separate boot-loaded tile catalog reached by different code and a different resource type (`reversing/cadaver/graphics.md` section 5). A visual coverage check finds that in seconds.
- **Rule out a resource or dispatch type by censusing every call site's selector value.** Grep a whole-image listing for every caller of the `(type, index)` fetch and read the `moveq #<type>,D0` / `move.w ...,D0` before each: a complete negative test, cheaper than proving a type unused from its data shape.
- **Composite overlapping art with a transparency mask, not an opaque paste.** Isometric engines fake tall walls by stacking square tiles with about 50% overlap; each tile is a shape on palette index 0, and an opaque paste lets every later tile's background corners erase the previous tile's edge, leaving a comb of gaps. The result outlines the right shape and reads as plausible, so it is misdiagnosed as a placement error one layer up. Decode the tile a second time with no palette ("L"/raw index image) to get the mask and `Image.paste(img, pos, mask)`.
- **A sprite spotted "in roughly the right area" is not proof it belongs to the object you think drew it**, and a buffer's first N bytes are not proof of its whole content. Check the object's exact declared coordinates (a tight crop, or a breakpoint on its own draw call), and read struct fields at their real width and buffers across their full extent.
- **A "(A5)+N array" may be a pointer to the array.** Check whether the routine that uses the field does `movea.l N(A5),Ax` (dereference) or uses `N(A5)` as a base displacement. Reading the wrong one returns real, plausible memory, which is what makes it costly.

## 4b. Prove a renderer or port pixel for pixel

What took PowerMonger's port to 100.00% on 27 frames (`reversing/powermonger/port/SPEC.md` section 6 "Scoring a capture", scripts in `reversing/powermonger/py/`):

- **Pair state i with the screen of snapshot i+1.** A snapshot stopped at the frame driver holds the state the next frame is drawn from, while its finished buffer shows the frame drawn from the previous state. Take `n` consecutive frames with `bpc <driver> 1` plus `snap` and score a against b.
- **Score per category.** Render once with everything and once without category c; the pixels that differ are c's visible pixels, and the game should show the sprite there, not what is under it.
- **Transcribe position and blit arithmetic word for word.** PowerMonger's sprite lerp works on packed `(x<<16)|y` longs, so a borrow leaks between halves; an "equivalent" two-lerp version put one sprite in ten a pixel off. Probe the game's `D0`/`D1` at the blit (`bp` on the blit call) for a few records before generalising.
- **Name a sprite from its writer, not its look.** Sixty frames of `track`ed fields showed a white shape rising 1 px a tick from a body, and the code setting the category (`move.b #<n>,6(An)`) said it was the kill branch.
- **A global `(dx,dy)` grid search of the render against the reference cheaply falsifies a hypothesized sub-pixel correction.** If `(0,0)` is already optimal the correction is a no-op. A search that stays flat while the match is low rules out a shift bug without saying what the cause is; do not default-blame "missing content".
- **Check the palette conversion before reading a low, spatially uneven score as missing content.** The repo has two independent `$0RGB`-to-RGB conversions: `tools/gfxview.py` `ste_colour` (`gun*255//7`) and `tools/snap_render.py` `st_colour` (`gun*36`). Cadaver's TUNNEL scored 19.7% against a reference rendered with the other formula and 96.0% with the matching one, with no code change. The tell: tiles look identical at a glance but match nowhere exactly (a real content bug looks wrong somewhere). Sample a few RGB values at the same coordinate: a consistent small offset (182 vs 180) is a formula bug.
- **Before unifying against an external authority, confirm your reference assets came from it.** Hatari's `conv_st.c` uses `gun*34`, and re-scoring Cadaver's two milestone screenshots against it gave 0 exact matches: neither was ever rendered by Hatari, so there was no ground truth to converge on.

## 4c. Cover the content, then watch what runs by itself

- **Screen many worlds before porting.** If the game builds levels from a seed, find where the seed is chosen (PowerMonger's briefing preview picks one of 144 lands; poke it at the world-build entry) and build a spread (`reversing/powermonger/py/build_land.sh` plus `census.py`). A per-world census of entity categories showed 8 categories the first level never draws.
- **Natural runs beat forced ones.** Run 3 or 4 worlds for 200M steps in stretches with the REPL `hits <steps> <addr>...` census over the routines you care about, snapshot per stretch (`runland.sh`), and re-run one to prove the counts are deterministic. Those snapshots become the differential-test corpus.
- **Find a write's real author with `watch`**: `watch <field>` over the stretch names the writing PC in one run, where docs had attributed it to the wrong routine.
- **Find how a level ends from the code before playing for it.** Grep for the end-screen resources or strings and the routine that leaves the game loop, then the command or test that reaches it. Drive both branches, and run a natural run well past its last snapshot to catch a natural ending.

## 5. Reverse the logic (mechanics, AI)

For "what does routine X do", build a differential test rather than reading disassembly and guessing. `snap` at an anchor, `detcheck` it to confirm determinism, then `callcap` the routine in isolation: it returns the register delta, the full memory diff and a trace hash, and restores the snapshot.

**`callcap` syntax.** The form is `callcap <addr> <maxSteps> [Rn=hexval ...]` (`Program.fs` REPL loop, the `parts.Length >= 3` branch). Always give an explicit step cap (for example `2000000`) before any preset. Bare `callcap <addr>` uses a hardcoded default and accepts no presets; with presets but no step cap the first preset is parsed as `maxSteps` and the REPL dies on an unhandled `FormatException`. Presets are hex: `D0=10` is `$10`. To prime state without presets, drive there first with `s`/`bp`/`bpc` from a real run.

**The corpus.** Write a Python reconstruction of the hypothesis and diff it against `callcap` over a corpus of states. `tools/pm_fsm_diff.py` (`Harness`, `State`, `run_corpus`) is the game-agnostic harness; only the reconstruction module (`pm_fsm_ref.py`) is PowerMonger-specific and needs a per-game equivalent. Report a diff count ("1847/1847") before calling a hypothesis proven. A corpus script's first argument (other than `reuse`) filters to the states whose name contains it; check the state count before trusting "0/0", since a stray argument can filter everything out.

Build the corpus with `tools/capture_hits.py <start.snap> <addr> <n,...> <out>`: it stops at chosen natural hits (numbers from a `hits` census line), snapshots each with its `.ram`, and writes entry registers and return address to JSON for the `State` presets. Group states by caller (the JSON's `ret`): that is how a second caller of the same routine shows up. A routine listing that starts two bytes early turns its opening `movem.l` push into "no matching push, not callcapable".

**Interrupt-masked calls.** `callcap` runs with interrupts masked, so a routine that waits on an interrupt-cleared flag (a sound driver's busy byte) never returns. Poke the flag clear in the state (PowerMonger `$2c993 := 0`). A call that "does not return" is often a fatal assert on the poked state (an id missing from a list): read the handler's error block before giving up.

**A callcap that touches none of the memory you expected is informative.** It can mean the routine depends on setup only its real caller does, not that it does nothing. Cadaver's room loader `$00cd50` touched none of the object array called alone; its real caller `$00e854` (the room-transition trigger) sets up registers and globals first. Confirm a callcap reproduces the expected side effect before reading its absence as a negative; if it touches nothing, look one level up the call chain.

**Read the right output.** `callcap` prints the whole changed-memory footprint (`mem $addr $old->$new`) unconditionally; an armed `watch` prints `WATCH: step=... $addr <- $val` live, only for its own range. Piping both through `tail` or a narrow `grep` can make one look like the other's silence. Grep for `WATCH:` and `callcap \$` by name, and confirm a negative both ways (the watch's silence and absence from the callcap delta).

**Verb and opcode tables are hypotheses until each handler is called live.** Call each handler under `callcap <addr> <steps> - A1=<scratch script> ...` (the `regdelta` line gives final A1, so the operand length; the `mem` lines give the effect) and tile the whole script corpus with the grammar (`py/secrets/overlay/verb_effects_callcap.py`). Reading bodies mislabeled Cadaver's verb 5 as "XP += n" (the handler overwrites D0 with a sound id before the add) and comparison op 2 as `!=` (it is `==`).

**Who calls X, and under what gate.** Cheaper than a differential test: one `bpc <addr> 1 <maxSteps>` (the hit banner prints registers) plus one `bt 1`. Do not also run a `hits` census first (the hit itself proves it fires and the step), and do not `r` after the hit. Read the caller's disassembly around the return address for the gating condition rather than a deeper `bt`. Size a `disassemble.py --linear <addr> <n>` dump low (60 to 100 instructions covers most routines) and widen only if it runs off mid-routine. `hits <n> <addrs>` after a `bp` that stopped the run counts only what happens after the stop: a routine that ran earlier reads 0 and looks uncalled. Start `hits` from the end of the click, before any `bp`, to count a whole route. In a mouse drive, the click is consumed during the settle after `mouse down`: start `hits` or `bp` before the down.

**Detect-then-apply pairs.** When a hazard is a pair (contact recorded into a shared cell one frame, consumed and applied later), pin "who dealt this hit" by breaking at the detect site, not the apply site: by the apply site the routine has re-pointed `A0` at the victim, so a breakpoint on the health decrement reads the victim's own base. Break on the line that copies the damage value out of the attacker. A zero-hit pin can be a timing-window problem: derive the exact step from a `watch` on the health field (it fires reliably on the known apply site), then aim the attacker-side `bpc` at a window covering it. Pin the real object with a breakpoint on the mechanism's own write site and read `A0` there; "looks like the right hazard from its position" is not an attribution.

**Naming a field or table.** Name from the game's own UI before the code's use: the panel text tables (PowerMonger `$9000..$b000`: `$9ccc`, `$9c80`, `$90ca`, `$9d52`) return a string pointer in A5 and are the developers' own words. PowerMonger's building kind 7 was "capital" until `housenam` at `$a15a` said WorkShop; lord `+6` and group `+112` were read as men at home and a patience budget and are both food (the captain panel `$921a` labels group `+36` "Food:"). Match a table's entries against an independent record set: PowerMonger's `$4d252` was documented as herded animals, but 203 of 203 live entries sit on tree render records (`reversing/powermonger/economy.md` section 2, `py/tree_census.py`). A census column (class, type, kind) is only as good as the table the game's own reader uses for that field: find the reader (PowerMonger's description routine `$011066`) and check one live object against it. For a player-driven mechanic, click it through the real UI against a no-order control run over the same steps; the difference is the effect.

**Census filters.** A decoder that filters its input turns "no script touches X" into an artefact. Reconcile the decoded count against the raw count bytes and print both (Cadaver's script census kept only blocks ending on `$17` at `len-1`, dropping 49 of 224 objects, the opener of door `$22` among them). Treat an unexplained id field as an item id until the rucksack scan says otherwise (five doors' positive id words were keys), and name a lookup's table from the code that fills it (`$00c42a`, the pick-up) before calling it a registration table.

**"No input opens X" is only as strong as the input list.** Confirm each icon of the object's own panel (`probe` returns them) against a no-panel control from the same snapshot, and read the object's z span next to the mover's: an object at z 18..31 on another's 0..17 is never overlapped from the floor, while fire with nothing in front is a jump (peak base z 34) that reaches it. Cadaver's lever needed its operate icon (7) confirmed with a second press (`mechanics.md`; `secrets.md` "The regalia walk"). A single scan of the whole door/flag table shows which doors have a switch at all. Likewise a "does nothing" verdict for a key must watch the handler's own branches and flag bytes, not one output: Cadaver's main loop (`$006ba2`) handles pause, map, save, load and F2 to F4 toggles from the same key cell.

**A door-graph or dataflow chain is a hypothesis about geometry, hazards and one-way doors.** Drive each leg before building on it (Cadaver `l1/route_level1_room89.py`, `l1/explore.py`: 46 legs in 40 s found eight gates in the first twelve rooms and a health budget the graph lacked). A hold that stalls, a room change that bounces back, or a health drop arriving legs later (a POISON bite: check `2434(A5)`) is geometry or timing to read, not a dead end.

**`w <addr> <8 hex digits>` writes a longword.** Poking a one-byte field clobbers the next three (Impossamole's `w bb74 12120300` also set the world index and zeroed the shop flag). Read the neighbouring fields and write the whole longword deliberately. `watch <addr>` on an odd byte misses a word or long write covering it (`MMU.fs` `checkWatch` tests only the write's start address) and all FDC DMA writes: also watch the even byte below, and read the writers in the listing. One `watch` region per REPL session: a second concurrent region silently drops events.

**A static value across two far-apart snapshots is not proof of "stuck" or "ungated".** A busy-poll utility can set and clear a value within a couple hundred steps of each tick, so any snapshot in its idle majority shows the same value. Prove it live: `hits <n> <handler-addr>` shows whether a handler fires, `watch <addr>` shows who changes it.

**A long-lived snapshot lineage is not ground truth.** If its original cold boot silently took a wrong path (skipped a load, missed a timing-sensitive event), every descendant inherits it and resuming passes reads as independent confirmation. A finding that looks like "this emulator cannot do X", especially one contradicting a real-hardware cross-check, is re-checked from a fresh cold boot before being written up as a bug (Impossamole's `after_select3.snap` lineage never populated a hero-sprite bank that a fresh cold boot with different keypress timing did).

## 6. Regression net (every commit that touches the emulator)

1. `./run.ps1 -NoBuild verify 5000000`: PASS (re-run 2 or 3 times on a byte-identical FAIL: a build-cache race, not a real failure).
2. `./run.ps1 -NoBuild snap 30000000 after.snap`, `cmp` against a diskless baseline. A diff is a gate decision, not an automatic failure: investigate before accepting or reverting.
3. `dotnet build -c Debug` as its own tool call, read it, `&&` never `;`.
4. Full `./run.ps1 selftest tests/680x0`: the gate is 0 wrong and 9 skip; the pass total drifts up with coverage, so do not gate on it.

An MMU change also needs a game snapshot compare, since `selftest` never reaches the RAM fast path. Pre-register the falsifier (the result that would mean the change is wrong) before running any of this.

## 7. Write the README

Every game's README covers, in this order: what the game is and its provenance (publisher, year, cracker, sha256, disk-image file layout); milestones reached and how; what it needed from the emulator as a commit table (wall to fix); how it was run (exact commands); how the CFG was built; what the artefacts show; a files table. When there are topic docs, open with a table of document, what it covers and its proof and match count (`populous/README.md`), and end with an explicit list of what was not exercised in the emulator. Match that shape so someone else can reproduce the run without re-deriving it.

Once enough is known, add a short architecture thread to the README or `mechanics.md`: the top-level per-frame/per-VBL dispatch, the core data structures (room/level layout, entity records, any resource manager or index table), and which mechanics are instances of a shared mechanism. That is what makes a doc useful for the next game.

**Docs are definitive reference text, not a diary.**

- A finding that changes, narrows, closes or reframes an earlier claim is folded into that claim's own prose in the same edit: correct the sentence, do not leave the old one standing beside a new dated one that contradicts it.
- A numbered section in `mechanics.md`, `graphics.md` or `ai.md` reads as a normal explanation of how the mechanism works now, with the proof (match count, script) attached. It is not a transcript of how understanding evolved; no "Nth pass found". That history lives in `git log` and `M68000/sessions/<workstream>.md`.
- The per-file table row in a README is the one place a running changelog clause is acceptable.
- If re-reading a section cold would confuse a newcomer about what is true today, rewrite it before or with the next finding that touches it.
- Before writing a new interpretive claim, grep the doc for whether a later section already retired that framing, and before disassembling a routine to decode it, grep the topic docs (and sibling games' `ai.md`/`economy.md`, for shared engine code) for its hex address: a routine can already be pseudocoded.
- Every behavioural claim carries an emulator check with a match count, or is labelled inferred.

## REPL commands (check `help` before assuming a gap)

`s`, `p` (preview), `u`, `bp`/`bpc` (breakpoints, auto-print registers), `bt` (backtrace), `hits <steps> <addr>...` (PC-hit census, counting first and last step too), `callcap`, `detcheck`, `r`, `m`, `w` (big-endian long), `watch`/`unwatch`, `snap`, `disk` (hot-swap drive A), `kbd`, `mouse`.

## Known tooling gaps

Not built; build the one a task actually needs: call-depth or step prefix and jsr/rts target on the live `-Trace` line; `.sym` symbolication of that trace; a mouse "move to absolute x,y" (read the game's pointer variables and compute deltas by hand); a windowed or call-subtree trace; `trace_cfg.py` ingesting the text `-Trace` dump (it reads only the binary event log). `disassemble.py` still has gaps in rarer families: if a listing looks wrong (an `ori` or `subi` on an address register, a pointless immediate), check the opcode bits before believing it (`movep.l` printed as `subi` and hid what `$e6ee` did).

## Discipline

- Transcribe hardware and OS semantics from source (Hatari's `src/*.c`, `M68000PRM.pdf`), not from memory.
- Stage named files only, never `git add -A`: disk images and cracked archives are copyrighted and stay untracked.
