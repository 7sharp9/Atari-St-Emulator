---
name: reverse-engineer-st-game
description: Workflow for reverse-engineering a commercial Atari ST game against this repo's F# 68000 emulator and tools/, boot it, drive it to gameplay, map control flow and graphics, and (if needed) reverse game logic via the snapshot+callcap differential-test harness. Use when asked to analyse, reverse-engineer, or "look at" a new Atari ST disk image/game, or to document or port its mechanics/graphics.
---

# Reverse-engineering an Atari ST game

Grounded in four prior subjects at `M68000/reversing/{a_013,supersprint,powermonger,populous}/`. Each produced the same shape of artifact: a boot-to-gameplay narrative, a `.sym` file, callgraph/cfg dot+svg, screenshots at milestones, and topic docs (`mechanics.md`/`graphics.md`/`ai.md`/`economy.md` as needed). That shape is the deliverable, reproduce it for a new game rather than inventing a new format.

The goal is not just cataloguing individual facts (this field does X, this routine writes Y) but surfacing the game's **architecture and algorithms**: how its systems are actually built — the data structures behind rooms/levels/entities, the dispatch mechanisms (state machines, per-frame fan-out, event/message passing, any bytecode or script-like interpreter driving content), and the algorithms implementing its core mechanics (pathfinding, collision, AI decision-making, procedural generation). A topic doc section is more valuable when it names the general mechanism a fact is an instance of, not just the fact itself — and a mechanism proven generic in one game (e.g. a per-room bounding-box proximity scan) is worth checking for when reversing the next one, since these games often share engine-level idioms even when their content differs.

## Scope: what actually transfers

This skill is Atari ST / 68000 specific. It leans on this repo's F# 68000 core, the real Hatari binary as an oracle, and `tools/` whose opcode tables and graphics decoders assume ST hardware (planar bitmaps, `$ffff8240` palette, GEMDOS/XBIOS traps). Full reuse: another ST game. Partial reuse: another 68000 platform (Amiga/Genesis/Mac), the CPU core and disassembler technique transfer, the memory map/OS calls/graphics formats don't. For anything outside 68000 entirely, only the *method* below (milestone ladder, snapshot+callcap differential testing, README template, gate discipline) transfers, the tool layer would need rebuilding from scratch.

## 0. Setup

- Get the disk image legally; do not commit it or the cracked archive. Record sha256 + size in the README (`supersprint/README.md` is the template).
- `unzip "<game>.zip"` → a `.ST` FAT12 image. `./run.ps1 -DiskA "<game>.ST" boot <N>` (or `--disk-a` on a bare `dotnet exec`).
- Orphaned `dotnet` instances make resume look non-deterministic, but **another Claude session may be sharing the repo**: check `tasklist | grep dotnet` and ask before `taskkill //F //IM dotnet.exe`; never kill blind. With a second session active, also never `dotnet build` (it replaces the DLL under the other session) and use `./run.ps1 -NoBuild` or bare `dotnet exec`.
- Create `M68000/reversing/<game>/` now, and an untracked working dir `M68000/scratchpad/<game>/` for extracted files, snapshots and decompiles (`scratchpad/*` is gitignored; `reversing/populous/py/popcfg.py` shows the `$<GAME>_WORK` path pattern).
- **Classify the program before choosing a method.** Extract the files (`unzip`, then FAT12-walk or boot and `Fread`-trace), find the main executable and check: magic `$601a` and plain text? Count `4e56` (LINK A6) words in TEXT. Hundreds of LINK frames, `N^NuNV` runs in the strings and C-runtime strings (`CON:`, `MMARGV=`) mean compiled C: take the decompile route (§3b), which turned Populous into a readable program in minutes. Packed/crypted or hand-written asm (PowerMonger, Super Sprint) means the trace + callcap route only.

## 1. Trace the boot, find the walls

`ATARI_NOTRACE=1 ATARI_TRACE_GEMDOS=1 ATARI_TRACE_OS=1 dotnet exec bin/Debug/net8.0/M68000.dll <N> --disk-a "<game>.ST"` narrates `Pexec`/`Fopen`/`Fread`/`Setscreen`, free ground truth for what the game loads and when. Paste the summary into the README.

No `\AUTO\` folder and no bootable sector means the game is launched from the GEM desktop. Make a headless copy instead of driving the desktop: `tools/add_file_to_disk.py game.st --from-disk LOADER.TOS --name LOADER.PRG --remove LOADER.TOS --remove DESKTOP.INF --auto --out game_auto.st` (`--remove` frees space on a full disk; the game never reads `DESKTOP.INF`).

Any unimplemented opcode/EA mode is an instruction wall. Fix it through the shared EA decoder (`x.ResolveEa`/`x.ReadEa`/`x.WriteEa`), the pattern the 45th–56th passes used for every prior game, new titles mostly hit missing addressing modes on existing instructions, not new hardware behaviour. Each fix is its own commit behind the regression net (§6); non-negotiable.

## 2. Drive it to gameplay

Progress attract → menu → gameplay by injecting input, not by guessing: REPL `kbd <hex>…` / `mouse move|down|up`, or `ATARI_KEY_INPUT`. Read the game's own IKBD handler first (disassemble around the vector it installs, typically `$118`/`$120`) to learn its packet format and key mapping, then script the exact byte sequence, Super Sprint's README section "Driving it into a race" is the model.

**Send a key's make and break codes in two separate `kbd` calls, with a real `s <n>` step count between them, not one `kbd <make> <break>` call.** A game with its own interrupt-driven IKBD ISR (stores raw scancodes into a game-internal cell the main loop polls) drains both bytes inside the single interrupt that follows one `kbd` call, so the main loop's poll never observes the transient "key is down" state and the input is silently dropped — the screen just sits there, looking like the wait loop is ignoring input entirely. `kbd <make>`, `s 3000000`, `kbd <break>`, `s <n>` mirrors a human press/release and is what actually advances the menu (`reversing/cadaver/README.md`'s "Keyboard discipline" note; cost a cadaver pass real time rediscovering it before finding that note already there).

`python tools/snap_render.py x.snap x.png` at each milestone (title, menu, gameplay): it reads base, rez and palette from the shifter, so double-buffered games come out right. Keep every screenshot that proves a milestone; drop exploratory ones before committing.

Mouse-driven menus: the game keeps its own pointer, and `mouse move dx dy` sends relative packets (keep each |d| <= 127). Before clicking, find the pointer in a screenshot and do the arithmetic in 320x200 space (screenshots are often saved at 2x; halving the wrong number cost Populous two failed clicks). Better, read the menu's hit-test code (the button x/y bands) and the game's pointer x/y variables, then move exactly. Screenshot after the move, before the click.

Before a long `u <addr>` / `bp` run, read the loop around the target to confirm it runs when you think it does: a Populous `u` into the intro's title-menu routine burned 300M steps because the routine only runs once per intro cycle, right after `load.pic` loads. Once the drive works, write it as a REPL script (`reversing/<game>/drive.txt`, fed on stdin) and prove it deterministic by running it twice from cold boot and `cmp`-ing the snapshots.

**Don't infer "does this keypress matter" from trials that also vary the step count.** If a
cracktro/intro screen isn't advancing the way you expect, resist the urge to just try a keypress and
eyeball the next screenshot — a screen that looks different only tells you *something* changed, not
that the key caused it, if the two trials also ran different step counts. Run a real A/B from the
*same* snapshot with the *same* step budget, once with the key and once without; only trust a
difference (or lack of one) between those. A Cadaver pass wrongly concluded a keypress was rewinding
a crack intro's greet-scroll from one uncontrolled comparison, when the real cause (confirmed by a
proper same-snapshot/same-budget A/B) was that the intro's greet+loading-bar sequence loops on its
own over hundreds of millions of steps regardless of input (`reversing/cadaver/mechanics.md` §52).
This isn't only a cracktro-intro pitfall: the same uncontrolled comparison (diffing a held-input
frame against the pre-input frame, rather than against a same-length no-input control) reads
ordinary per-frame animation as proof of input-driven movement in gameplay too, and doesn't tell you
*which* on-screen sprite actually moved — don't name a sprite "the hero" from that diff alone without
checking it moves independently of the background/other sprites in the no-input control (impossamole
`reversing/impossamole/README.md`'s "Gameplay input" section: a first pass claimed "the hero sprite
in a different pose" from exactly this uncontrolled comparison and had to retract it after the actual
control showed the pointed-at sprite moving *with* the background, not independently of it).

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
Scope `--range` to the program's own text segment (from the `Pexec` basepage decode); for `--cfg`, one dense region at a time, a whole-program CFG is unreadable. Build the `.sym` sidecar (`addr<TAB>name`) incrementally as routines are named; it feeds both `trace_cfg.py --names` and `disassemble.py`.

`disassemble.py --snap <path> <addr>` / `--linear <addr> <n>` reads real instructions at an address of interest. `--callers <addr>` only scans TOS ROM, not the loaded program, grep a `--linear` dump for `jsr $<addr>.l` to find in-program callers. To count per-function calls over a trace, filter the event log for kind 3 (call) records by target: that list of once-per-frame routines is the best seed for everything after.

`disassemble.py --snap <snap> --all <lo> <hi> > game.asm` writes the whole loaded image as one listing that carries on past jump-table stops. Make it once per pass and grep it for callers (`jsr $xxxx.l`, `bsr $xxxx`), for every writer of a field (`',44(A[0-7])$'`, then the `-N(An)` forms for pointers into the middle of a record) and for every reader of a global. A claim that nothing, or only one routine, writes a field needs that grep plus a read of each writer's whole block: PowerMonger `$2452` copies a byte into a unit, and `$245c`, four instructions later, overwrites it.

**When resolving what a jump-table/dispatch entry actually does (e.g. matching each entry to an error string it can print), bound the forward walk — an unbounded transitive branch-follow wanders into unrelated shared code and reports the wrong string as belonging to the wrong entry.** The reliable shape: walk the entry's own straight-line body (treating an unconditional `bra`/`jmp` as a same-routine continuation, not a stop, since error stubs are often reached through 1-2 chained `bra`s), and follow a conditional branch found in that body exactly one level further, no more. A first attempt at this with no depth limit silently wandered dozens of blocks away from the actual entry and attributed several handlers to an unrelated, oft-referenced string reached only by chance (`reversing/cadaver/mechanics.md` §64, `py/verb_opcode_map.py`) — caught only by noticing an implausibly high visited-block count and spot-checking by hand, not by anything automatic. A jump table's own raw word arithmetic can still be exactly right while the entry it points to decodes as a garbage/unimplemented instruction (an F-line opcode in one Cadaver case) with clean, correct code resuming 2 bytes later — don't discard a target as misaligned without checking whether the *next* instruction onward reads as a coherent routine; see the "deliberately looks like garbage" trap below for the same caution from the opposite direction.

**A concrete, checkable test for "is this dispatch target a real entry or a bounded-walk false positive landing mid-instruction in a neighbouring routine": is its first instruction provably side-effect-free, and does it skip a push or pop.** A target whose first instruction looks implausible (`ori.b` targeting an address register — an invalid EA for that opcode entirely, or a `movem.l (A7)+,...` with nothing pushed on the path that reaches it this way) is only a real entry if (a) that instruction's effect is provably harmless — a register it touches is never read again before the next real branch — and (b) no push/pop is skipped (an extension word from the *previous* real instruction consumed as a bogus opcode is fine if the following bytes are the previous instruction's own clean continuation; a target landing 2 bytes into a `movem`'s own register-mask word, or into the middle of a `lea`'s address operand, corrupts the stack or leaves a register unset if actually invoked). Cadaver's 73rd pass used exactly this pair of checks to accept 3 real dispatch-table pins that land mid-instruction (matching the existing STOPACTI precedent) while rejecting 6 candidates a bounded walk's raw string-match had found, each of which failed one or both tests (`reversing/cadaver/mechanics.md` §64a/§64d).

## 3b. Decompile a compiled-C program

1. `python tools/prg2img.py GAME.PRG game.img <text>`, with `<text>` the runtime TEXT address from the Pexec trace, so every image address equals a runtime address.
2. `python tools/disassemble.py --rom game.img --base <text> --linear <text> 30000 > game.asm`: a whole-program linear sweep (C code is contiguous; small data tables embedded in TEXT decode as garbage).
3. Headless Ghidra (installed at `C:/Program Files/ghidra_12.1_PUBLIC`): `tools/ghidra/DecompileAll.java`, usage in its header. It writes every function to one C file and applies your `.sym` names, so re-run it whenever the `.sym` grows. Compiler-specific runtime helpers that return through stack slots (Alcyon `lmul`/`ldiv`) need a purge override or the caller's decompile fills with `puVarN + -4` noise; trap wrappers get a varargs override. Expect a handful of very large functions to lose stack tracking anyway: read those from the asm.
4. The decompile is a reading aid, not proof. Trap-call argument lists come out wrong; confirm OS calls in the asm. Every behavioural claim still goes through §5.

## 3c. Fan out once the map exists

After the per-frame routine list, the decompile and a gameplay snapshot exist, the topic areas (graphics / world+terrain / people+mechanics / AI) are independent enough for parallel subagents. Write one shared `BRIEF.md` in the working dir: program layout and base, runtime-helper conventions, per-frame routine list with call counts, known structures, artifact paths, snapshot list, the REPL cheat-sheet, the required output (`<area>.md` + `sym.txt` + scripts) and HARD RULES (no build, no git, no taskkill, write only under `agents/<area>/`, cite addresses, label inferred claims, prove behaviour against the emulator with a match count, and wait for or stop every background process it started before sending its final message: a finished Populous agent left an emulator run holding `bin/`'s DLL, which blocked the parent's build). Tell agents to write their scripts as they will be committed: import the game's `py/` from one directory up (`os.path.dirname(__file__)/..`) and write data under `$<GAME>_WORK/<area>/`, so promotion into `reversing/<game>/py/<area>/` is a plain copy; Populous pass 2 had to rewrite five agents' hard-coded paths. Copy the brief's addresses, strides and struct offsets from the game's constants module and proven doc sections, not from memory: the PowerMonger 122nd brief had the object table wrong and all three agents had to correct it. Subagents cannot write report files, so ask for the report as the final message and save it into the agent's directory yourself. Then:
- Append to the brief rather than re-briefing when something new is learned mid-run; re-read your own addenda for over-claims (Populous: "the world barely changes without input" was wrong, the AI terraforms).
- If agents die on an API/network error, resume each with `SendMessage` to its agent id; they keep their context.
- **Reconcile before merging.** Merge the `sym.txt` files with `tools/merge_sym.py`, which lists addresses given different names: most are synonyms, but real semantic disagreements hide there (Populous `$219b0`: "two-player" vs "one-player" flag; settle it in the code). Cross-check each doc's open questions against the others' answers, spot-check each headline match count yourself by re-running its script, and check live-behaviour claims against snapshots.
- Move the scripts into `reversing/<game>/py/` with paths from one config module (not hard-coded scratchpad paths), and re-run every verifier from there before committing.
- **Merging routine proofs.** When two agents transcribe the same callee, keep one version and run both corpora against it (a free cross-check). Re-run every agent gate from fresh callcaps (no `reuse`), merge the transcriptions into the reference module, promote the gates to `reversing/<game>/py/` (corpora stay in scratchpad, listed in `ANCHORS.md`), then re-run every older gate of that module.

## 4. Find and decode the graphics

`gfxview.py <snap> --contact ram.png` first, a whole-RAM overview to spot where decoded assets sit. Then `--html` for an interactive per-region viewer (base/width/rows/bpp/palette/zoom) to pin down the actual format (planar/chunky/tiled). `ATARI_GFX_SIDECAR=<path>` during the run records every XBIOS `Setpalette`/`Setscreen` so gfxview can auto-mark candidates. Write findings to `graphics.md`/`gfxview.md`, not just the screenshots.

**Once a format is confirmed (not just suspected), render and commit the asset**, not only a prose description of its address/dimensions: a decoded spritesheet, tileset, icon set or palette swatch goes in `reversing/<game>/` (or a `graphics/` subdir once there are several) as a real PNG, table-indexed in `graphics.md`/the README's files table next to the gameplay screenshots. A later pass or Dave should be able to look at the sprite without re-running the decode; a coordinate and a bpp value in prose is not the deliverable, the picture is.

**Before declaring a sprite/object catalog "the whole background", put its own contact sheet next to a real gameplay screenshot.** A catalog that's genuinely struct-driven and byte-exact can still be structurally partial — Cadaver's 22-entry sprite-object-array export (props: torches, barrel, boat, chest) was correct and fully proven, but 24 passes of static/live tracing concluded from it that "a room's background is just its object array" anyway, because nobody compared the exported catalog's own contact sheet against a screenshot and noticed nothing in it was wall- or floor-scale. The real terrain lived in a completely separate, shared, boot-loaded tile catalog reached through different code and a different resource type (`reversing/cadaver/graphics.md` §5). A five-second visual coverage check would have caught the gap that four passes of `watch`-based tracing didn't.

**To rule out a resource/dispatch type cheaply, census every call site's selector value, not one spot check.** Grepping a whole-image `disassemble.py --all` dump for every caller of a `(type, index)`-style resource fetch and reading the `moveq #<type>,D0`/`move.w ...,D0` set immediately before each call site is a fast, complete negative test ("type 2 has no live caller anywhere in the loaded program") — cheaper and more trustworthy than trying to prove a type is unused from its data shape alone (`reversing/cadaver/graphics.md` §5a).

**Compositing overlapping sprite/tile art onto a canvas needs a transparency mask, not an opaque paste, whenever the game's own placement relies on tiles overlapping** — common in isometric engines that fake a taller wall by stacking square tiles with ~50% vertical/horizontal overlap rather than drawing full-height art. Each tile is a shape (a cube, a diamond) on a background colour (usually palette index 0), not full-square art; an opaque paste lets every later tile's background corners erase part of the previous tile's visible edge in the overlap zone, producing a comb of gaps. The result still outlines the right overall shape, which is exactly what makes it a dangerous bug: it reads as *plausible* at a glance and only fails on a close look, so it can easily get misdiagnosed as a placement/logic error one layer up instead of a compositing error at the paste itself (cost a Cadaver pass a full extra round of re-verifying its placement maths, which turned out to be correct all along, `reversing/cadaver/graphics.md` §5i). Decode the tile a second time with no palette (an "L"/raw-index image) to get a mask, and paste with it (`Image.paste(img, pos, mask)`); don't paste the palette-applied RGB image directly.

## 4b. Prove a renderer or port pixel for pixel

What took PowerMonger's port from ~96% to 100.00% on 27 frames (`reversing/powermonger/port/SPEC.md` §6 "Scoring a capture", scripts in `reversing/powermonger/py/`):

- **Pair state i with the screen of snapshot i+1.** A snapshot stopped at the frame driver holds the state the *next* frame is drawn from, while its finished buffer shows the frame drawn from the *previous* state. Scoring a snapshot against its own screen leaves everything that moves (and animated water) one tick behind, and the old workaround ("score with tick − 1") only hides it. Take `n` consecutive frames with `bpc <driver> 1` + `snap` and score a against b.
- **Score per category, not just overall.** Render once with everything and once without category c; the pixels that differ are c's visible pixels, and the game should show the sprite there (not what is under it). That isolated every wrong formula in minutes.
- **Transcribe position/blit arithmetic word for word.** PowerMonger's sprite lerp works on packed `(x<<16)|y` longs, so a borrow leaks between halves; the "equivalent" two-lerp version put one sprite in ten a pixel off. Probe the game's `D0`/`D1` at the blit (`bp` on the blit call) for a few records and compare before generalising.
- **Look before naming.** One frame shows a white shape; 60 frames of `track`ed record fields show it rising 1 px a tick from a body, and the code that sets the category (search for `move.b #<n>,6(An)`) says it is the kill branch. Name a sprite from its writer, not its look.
- **A global `(dx,dy)` grid-search of the whole render against the ground-truth screenshot cheaply
  falsifies or confirms a hypothesized sub-pixel correction before you spend time implementing it.**
  Cadaver's 66th pass assumed a draw descriptor's screen-offset field needed a shift-table adjustment
  applied before use (rows/columns only at ~2px granularity); reading the descriptor's own separate
  `x0`/`y0` fields directly instead, then grid-searching `(dx,dy)` over ±3px, found `(0,0)` already
  optimal — proof the two were already mathematically identical and there was nothing left to correct
  (`reversing/cadaver/graphics.md` §5i-2). The same technique flags a *non*-positional bug too: a
  `(dx,dy)` search that stays flat (no offset scores meaningfully better than `(0,0)`) while the
  match is still low rules out a placement/shift bug without telling you what the real cause is —
  don't stop there and default-blame "missing content" (see the next bullet for why that guess can
  itself be wrong).
- **Before concluding a low, spatially-uneven pixel-diff score against an independently-generated
  reference screenshot means missing render content, check whether the two images were produced by
  the same palette-to-RGB conversion.** Cadaver's 66th pass found TUNNEL's tile-only mosaic scored
  only 19.7% against its reference (vs CAVERN's 96.6% using the identical rendering code) and, since
  the placement formula was independently proven correct (table byte-identical across captures, a
  full live re-render reproducing the reference pixel-for-pixel), concluded the gap must be an
  untraced content layer — a plausible-sounding, wrong diagnosis that sent the 67th pass chasing a
  real but irrelevant mechanism before finding the actual cause: this repo carries *two* independent
  3-bit-per-gun `$0RGB`→RGB conversions (`tools/gfxview.py`'s `ste_colour`, `gun*255//7`, vs
  `tools/snap_render.py`'s `st_colour`, `gun*36`), and the two milestone screenshots happened to have
  been generated by different tools using different formulas. Re-scoring with the *matching* formula
  took TUNNEL from 19.7% to 96.0%, in line with CAVERN, with no code or content change at all
  (`reversing/cadaver/graphics.md` §5i-3). The tell in hindsight: individual tiles looked visually
  identical to the reference at a glance (same shapes, same rough colors) despite failing exact-match
  almost everywhere — a real content/placement bug produces a render that *looks* wrong somewhere; a
  palette-rounding mismatch produces one that looks right everywhere but matches nowhere exactly.
  Cheap check before trusting a "missing content" read: sample a few individual RGB pixel values from
  each image at the same coordinate — a consistent small integer offset (e.g. 182 vs 180, 145 vs 144)
  across many samples is a formula/rounding bug, not a wrong tile.
- **"Unify two disagreeing internal formulas against the real emulator's source" can be the wrong
  fix — check whether your own reference assets were ever produced by that source before chasing it.**
  Cadaver's 68th pass followed up on the 67th's open item (which of the two palette formulas above is
  Hatari-accurate) by cloning Hatari and reading `conv_st.c`'s real STF conversion (`gun*34` for a
  3-bit register, matching neither in-repo formula). Re-scoring both milestone screenshots against it
  gave **0/N exact for both** — not a rounding-level miss, complete non-matches — proving neither
  `gameplay.png` nor `room2_tunnel_entry.png` was ever rendered by Hatari at all; they're artifacts of
  this repo's own historical tooling, so there was no ground truth for the two formulas to converge
  on and the "unify" framing itself was wrong (`reversing/cadaver/graphics.md` §5i-3 addendum). Before
  spending a pass chasing an authoritative external formula to resolve an internal tooling mismatch,
  first confirm the assets in question actually came from that authority — a quick 0%-vs-close-match
  test against one known reference settles it before you touch anything else.

## 4c. Cover the content, then watch what runs by itself

- **Screen many worlds before porting.** If the game builds levels from a seed, find where the seed is chosen (PowerMonger: the briefing preview picks one of 144 lands; poke it at the world-build entry) and build a spread of them. A per-world census of entity categories (`reversing/powermonger/py/build_land.sh` + `census.py`) showed 8 categories the first level never draws.
- **Natural runs beat forced ones.** Run 3-4 worlds for 200M steps in stretches with the REPL `hits <steps> <addr>...` census over the routines you care about, snapshot per stretch (`runland.sh`), and re-run one to prove the counts are deterministic. PowerMonger's mission 1 never killed anyone even when forced; later lands fought, revolted and equipped units unprompted, and those snapshots became the differential-test corpus.
- **Find a write's real author with `watch`.** Docs attributed land capture to the wrong routine; `watch <field>` over the stretch named the writing PC (`$5538`, inside the revolt) in one run.
- **Find how a level ends from the code before playing for it.** Grep for the end-screen resources or strings and the routine that leaves the game loop, then the command or test that reaches it. Drive both branches (PowerMonger: post the retire command, then poke the verdict variable for the other branch), and run a natural run on past its last snapshot to catch a natural ending (PowerMonger land 60 lost its captain 94.7M steps past `run/k60_s4`).

## 5. Reverse the logic (mechanics/AI), if that's the goal

For "what does routine X actually do", don't read disassembly and guess, build a differential test. `snap` at an anchor point, `detcheck` it first to confirm determinism, then `callcap <addr> [Rn=hex ...]` to run the routine in isolation and get its register delta + full memory diff + trace hash (snapshot-restored after). Write a Python reconstruction of the hypothesis and diff it against `callcap` output over a corpus of states, `tools/pm_fsm_diff.py`'s `Harness`/`State`/`run_corpus` are a game-agnostic differential-test harness; only the reconstruction module (`pm_fsm_ref.py`) is PowerMonger-specific and needs a per-game equivalent. Report a diff count (e.g. "1847/1847") before calling a hypothesis proven, every PowerMonger pass (93rd–121st) gates on this. `py -3 <corpus>.py <substr>` runs only the states whose name contains `<substr>`. Before trusting a "0/0" or "0 states" result, check the state count: a stray argument once filtered every state out.

Build the corpus with `tools/capture_hits.py <start.snap> <addr> <n,...> <out>`: it stops at the chosen natural hits (numbers from a `hits` census line), snapshots each with its `.ram`, and writes the entry registers and return address to JSON for the `State` presets. Group the states by caller (the JSON's `ret`): that is how PowerMonger's second `$550e` caller and `$2776`'s `$25d6` caller turned up. `callcap` runs with interrupts masked, so a routine that waits on an interrupt-cleared flag (a sound driver's busy byte) never returns: poke the flag clear in the state (PowerMonger `$2c993 := 0`).

**A `callcap` on a routine that touches none of the memory you expected is a real, informative result — it can mean the routine depends on setup only its real caller does first, not that the routine does nothing.** Don't assume the routine a prior pass named "the loader"/"the trigger" for a mechanism is the right one to call in isolation just because its own body contains the write you're after. Cadaver's 73rd pass found a raw `callcap` on the room loader (`$00cd50`, already documented as populating the room's object array) touched zero bytes of that array when called alone — it was missing register/global setup its real caller (`$00e854`, the actual room-transition trigger, one level up the call chain) performs first. Confirm a callcap actually reproduces the expected side effect (check the register/memory delta touches what you expect) before trusting its absence of an effect as a negative result; if it touches nothing, look one level up the call chain for what really sets things up (`reversing/cadaver/mechanics.md` §67).

Name a field from the game's own UI when one prints it: find the panel template's labels and the formatter that reads each field (PowerMonger's captain panel `$921a` labels group `+36` "Food:"). Names inferred from the AI's use of a field can be wrong for a long time: PowerMonger's lord `+6` was read as men at home and group `+112` as a patience budget for 50 passes; both are food. For a player-driven mechanic, click it through the real UI against a no-order control run over the same steps; the difference is the effect.

**`callcap`'s own printed memory delta (`mem $addr $old->$new` lines) is not the same thing as an active `watch`'s output (`WATCH: step=... $addr <- $val`), even in the same REPL run.** `callcap` always prints the *entire* changed-memory footprint of the whole call unconditionally, regardless of whether any `watch` is armed; a `watch` only prints its own lines for writes inside its own narrow range, live, as they happen. Piping both through `tail`/a narrow `grep` can show only the bulk `callcap` delta and make it look like the watch produced nothing (or vice versa) — grep for `WATCH:` and `callcap \$` by name rather than assuming either output's shape, especially when checking a targeted range (e.g. a specific resource table's index slots) for zero writes: confirm the negative both ways, via the watch's own silence and via absence from the callcap's full delta (cadaver 74th pass, `mechanics.md` §68's type-9 negative check).

**A struct field documented as "an array at `(A5)+N`" may actually be a pointer *to* that array, not the array's own address.** Before reading raw memory at `(A5)+N` yourself, check whether the routine that uses it does `movea.l N(A5),Ax` (dereference — the array lives wherever that points, not at `N(A5)`) or uses `N(A5)` directly as a base displacement (the array really is there). Reading the wrong one still returns real, plausible-looking memory (whatever else happens to occupy that address), which is what makes it costly: a Cadaver pass spent most of a live-verification effort reading consistent-but-irrelevant bytes at a field's own address, across eight different snapshots, before checking which addressing mode the field's one real reader actually used (`reversing/cadaver/graphics.md` §5i).

**Three escalating static scans answer "does anything reference X at all" before any live test.**
`tools/find_ram_callers.py <snap> <addr>...` finds direct `bsr`/`jsr`/`jmp`/`bcc` instructions whose
own decoded text names the target. If that comes back empty, it doesn't mean nothing references the
address — it's blind to a target reached only through an indirect jump: `tools/find_literal_ptr.py
<snap> <addr>` finds the target sitting as a raw data pointer (an abs-long `jsr`/table entry whose
own instruction bytes literally encode the address, which a text-based scan can still miss on a
`.l`/`.w` suffix quirk); `tools/find_jump_table_hit.py <snap> <addr>` finds it as a displacement-table
entry (`target - table_base`, this game's own `add.w D0,D0; adda.w 0(An,D0.w),An; jmp (An)` dispatch
idiom, §3's control-flow table shape) added to a table base collected from every literal address any
instruction in the image names. Validate a new scan against an address you already know has a real
caller before trusting a "zero hits" result on one you don't (cadaver mechanics.md §48b/§48c).

**"Who calls X, and under what gate" is cheaper than a full differential test.** The `callcap`
corpus machinery above is for proving what a routine *computes*; for "which caller reaches X, and
what condition selects it" a single `bpc <addr> 1 <maxSteps>` (its hit banner already prints
registers) plus one `bt 1` is enough — don't also run a separate `hits` census first (the `bpc` hit
itself proves it fires and the step it fires at) and don't re-run `r` after the hit, it just
reprints the same register block the banner already showed. Read the caller's own disassembly
around the return address for the gating condition rather than a deeper `bt`. When sizing a
`disassemble.py --linear <addr> <n>` dump, guess low (60-100 instructions covers most routines on
this game) and re-run wider only if the dump plainly runs off the end mid-routine; a dump 2-3x
longer than the routine wastes as much output as it shows.

## 6. Regression net (every commit that touches the emulator)

1. `./run.ps1 -NoBuild verify 5000000`, PASS (re-run 2–3× on a byte-identical FAIL, that's a build-cache race, not a real failure).
2. `./run.ps1 -NoBuild snap 30000000 after.snap`, `cmp` against a diskless baseline. A diff is a gate *decision*, not an auto-fail, investigate before accepting or reverting.
3. `dotnet build -c Debug` as its own tool call, read it, `&&` never `;`.
4. Full `./run.ps1 selftest tests/680x0`, gate is 0 wrong / 9 skip; the pass total drifts up with coverage, don't gate on it.

Pre-register the falsifier, what result would mean the change is wrong, before running any of this, not after.

## 7. Write the README

Every prior game's README (`M68000/reversing/{a_013,supersprint,powermonger,populous}/README.md`) covers, in this order: what the game is + provenance (publisher/year/cracker, sha256, disk-image file layout); milestones reached and how; "what it needed from the emulator" as a commit table (wall → fix); "how it was run" (exact commands); "how the CFG was built"; "what the artefacts show"; a files table. Match that shape so a later pass, or someone else, can reproduce the run without re-deriving it. When there are topic docs, open with a table of document / what it covers / its proof and match count (`populous/README.md`), and end with an explicit list of what was *not* exercised in the emulator.

A game's README or `mechanics.md` benefits from a short "architecture" thread once enough is known: what the top-level per-frame/per-VBL dispatch actually looks like, what the core data structures are (room/level layout, entity/object records, any resource-manager or index table), and which mechanics are instances of a shared general mechanism vs one-off special cases. This is what makes a doc useful to someone reversing the *next* game, not just this one.

**Keeping the topic docs current is not optional, and it is not the same as appending.** A finding that changes, narrows, closes or reframes an earlier claim gets folded into that claim's own prose in the same edit that adds the finding — correct the sentence, don't leave the old one standing next to a new dated one that contradicts it. The per-file table row in a README (`| file | what |`) is the one place a running "Nth pass: ..." clause list is acceptable, because it's already structured as a changelog; a numbered section in `mechanics.md`/`graphics.md`/`ai.md` is not a changelog and should read as a normal explanation of how the mechanism works now, with the proof (match count, script) attached, not as a transcript of how understanding evolved across passes. If re-reading a section cold would confuse a newcomer about what's actually true today, that section needs a rewrite pass before or alongside the next finding that touches it, not a further append.

## REPL commands that exist (check `help` before assuming a gap)

`s`, `p` (preview), `u`, `bp`/`bpc` (breakpoints, auto-print registers), `bt` (backtrace), `hits <steps> <addr>...` (PC-hit census), `callcap`, `detcheck`, `r`, `m`, `w` (big-endian long), `watch`/`unwatch`, `snap`, `disk` (hot-swap drive A), `kbd`, `mouse`.

## Known tooling gaps

From repeated friction across passes (not yet built, build the one a pass actually needs, not all speculatively): no call-depth/step prefix or jsr/rts target on the live `-Trace` line; no `.sym` symbolication of that live trace; `disassemble.py` still has gaps in rarer families, so if a listing looks wrong (an `ori`/`subi` on an address register, a pointless immediate) check the opcode bits before believing it: `movep.l` showed as `subi` until the 121st pass and hid what `$e6ee` did; no mouse "move to absolute x,y" (the game's own pointer variables have to be read and deltas computed by hand; `reversing/populous/py/popdrive.py` is a worked example that plans clicks from the game's hit-test code); no windowed/scoped trace (PC-range or call-subtree only); `trace_cfg.py` only ingests the binary event log, not the text `-Trace` dump.

## Discipline carried over from the CPU-accuracy work

One `watch` region per REPL session, a second concurrent region silently drops events. Transcribe hardware/OS semantics from source (Hatari's `src/*.c`, `M68000PRM.pdf`) rather than recalling them. Stage named files only, never `git add -A`, disk images and cracked archives are copyrighted and must stay untracked.

A `jsr`/`jmp` target whose static disassembly looks like noise (garbage opcodes, an address that
falls inside what should be data like screen memory) is not evidence the target really is stale
data misread as code - copy-protection code deliberately looks like garbage under a blind
byte-for-byte scan (self-installing exception-vector handlers, deliberately-executed
reserved/unimplemented opcodes as CPU-detection probes, trace-mode single-step decrypt loops).
Step the live CPU through it before concluding it's misread data rather than a genuine emulator
gap or an intentional probe (Cadaver 55th pass called a Rob Northen protection chain "stale
framebuffer pixel data decoded as code" from a static read alone; the 57th pass single-stepped it
and found two real emulator gaps - a reserved opcode and the trace exception - that were the
actual wall, `mechanics.md` §57).

When a prior pass's doc quotes disassembly with `...` eliding part of a routine, re-disassemble it
in full (`disassemble.py --linear <addr> <n>`) before reasoning about its exact structure — the
elided part is often exactly the loop-count/register-mask detail that determines the answer
(Cadaver 36th pass: the excerpt looked like a single unrolled copy; the full dump showed a
`subq.b`/`bne` outer loop that fixed the total chunk count). A `movem.l (A0)+,list` /
`movem.l list,-(A1)` block-copy idiom reverses the order of whole transfer *chunks* across the copy
(predecrement mode processes the same register list in fixed reverse order, which cancels with the
address decrementing, so within a chunk relative byte order is unchanged) — recognise this pattern
before assuming a copy is a plain memcpy; it explains buffers that "look like noise" at the obvious
raster width but are actually the right data in chunk-reversed order (Cadaver `mechanics.md` §35).
