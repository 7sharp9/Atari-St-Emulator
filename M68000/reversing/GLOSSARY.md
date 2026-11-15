# Glossary

The game notes under `reversing/` share one vocabulary: the emulator's lab commands, the evidence labels
attached to each claim, the Atari ST's hardware and operating system, and the copies of the games that were
studied. This page defines each term once, so the topic docs can use it without explaining it again. Each
entry says what the term means here; the doc named in brackets holds the detail. How figures, posts and README
openings are written for a reader new to all of this is in `WRITING.md`.

## Notation

- **`$1d22c`**: a hexadecimal address in the emulated machine's memory at run time, not an offset into a
  file. In prose an address is a citation: it lets a reader find the routine or variable in a disassembly
  or check it in the emulator. Where a doc has a name for the thing, the name carries the meaning and the
  address follows it.
- **`D0`-`D7`, `A0`-`A7`**: the 68000's eight data registers and eight address registers. `A7` is the
  stack pointer.
- **`12(A6)`**: the memory at register `A6` plus 12. Several games keep their globals in one block and
  reach every variable this way; the doc gives `A6`'s value, so `12(A6)` names a fixed address.
- **byte, word, longword**: 8, 16 and 32 bits. `move.w`, `cmpi.b` and the like name the operation width
  with the same suffix.
- **47/47 (a match count)**: a model reproduced 47 of the 47 cases it was compared on. The denominator
  says how much was checked, so 47/47 and 65455/65455 are different strengths of the same claim.

## How the work is done

- **step**: one emulated 68000 instruction. Step counts are the emulator's clock: the screen interrupt
  (VBL) fires every 12,000 steps, and "a 3,000,000-step run" means that many instructions.
- **tick**: one pass of a game's own main update loop. A tick is the game's unit of time and is usually
  several VBLs long; each game's doc says how many. Some games run part of the loop less often and the
  doc names that rate: Carrier Command's "economy tick" (production and transport) is every 4th main-loop
  frame.
- **snapshot** (`.snap`): a saved state of the whole emulated machine (CPU, memory, chips, floppy
  position) that can be resumed. Experiments start from snapshots so they repeat exactly; `detcheck`
  confirms that a restored snapshot runs identically. A snapshot written by a current build carries a
  `.prov.json` file recording the disk and emulator build that made it (`DEVELOPING.md`, "Snapshot /
  preview fidelity").
- **snapshot names** (`c_s30`, `pm88_f1`, `base30`, `ai/nat2`): file names of particular saved states,
  for example a Strategy game in Carrier Command with the carrier at its home island. A doc that cites one
  says what state it holds. Snapshots live in the uncommitted `scratchpad/`; the reusable ones, with how
  to rebuild them, are listed in `scratchpad/ANCHORS.md`.
- **anchor**: a snapshot listed in `ANCHORS.md` as worth reusing, with how to rebuild it; some have a
  committed recipe that `tools/recipe.py` replays from a cold boot.
- **cold boot**: starting the emulator from power-on with the disk inserted, rather than from a
  snapshot. A finding that the emulator cannot do something is re-checked from a cold boot, because a
  long chain of snapshots can carry state the real game would never have.
- **REPL**: the emulator's command prompt, driven from a script on stdin. `help` lists its commands.
- **drive, driven**: play the game through its own input (keyboard, mouse or joystick events sent by a
  REPL script) to reach a screen or a situation. A result reached this way is **natural**.
- **poke, poked**: write a value straight into the game's memory by hand, for example to give an island
  to the player or set a timer to 1. It reaches a situation quickly but is not something the game would
  do by itself, so a poked result is labelled as such. A **labelled poke** is one the doc states openly.
- **trace**: the per-instruction log the emulator writes when `ATARI_TRACE=1` is set, or the event log of
  calls and branches from `ATARI_TRACE_EVENTS`, from which `tools/trace_cfg.py` builds a **CFG**
  (control-flow graph: which blocks of code ran and how they connect).
- **hits** (a census): count how many times each listed address executes during a run. It shows which
  routines are live and, within the run's length, which are not.
- **bp, bpc**: stop at the first (or the nth) arrival at an address.
- **watch**: report every write to a memory range, with the instruction that made it.
- **stserver**: the emulator as a long-running process driven by JSON commands, with several watches,
  breakpoints and memory hooks at once (`DEVELOPING.md`, "Memory hooks and the `stserver` process").
- **callcap**: run one routine of the game's own code in isolation. The emulator restores a snapshot,
  sets the chosen inputs in registers, calls the routine, records everything it changed (registers and
  every memory byte) and restores the snapshot again.
- **port, model, reference**: our re-implementation of a game routine in Python or F#, written from the
  disassembly. It is a hypothesis about what the routine does until it is compared with the game.
- **corpus**: the set of saved states a model is compared on, usually captured at natural calls of the
  routine during play (`tools/capture_hits.py`).
- **gate**: a re-runnable check script that compares a model with the game, usually through `callcap`
  over a corpus, and passes only if every case matches, reporting a match count. A gate is trusted only
  once deliberately broken versions of the model (one constant or branch changed), the **controls**, fail
  it; a control that passes shows the corpus never tests that detail. `tools/gates.py run <game>` re-runs
  a game's gates.
- **control run**: the same run with the one change under test left out, so a difference between the
  two is caused by that change.
- **wall**: the point where a program stopped on the emulator because of something the emulator did not
  yet do (an instruction, a chip behaviour). Each game README lists the walls it hit and their fixes.
- **oracle**: a second emulator treated as ground truth for a comparison: Hatari and MAME for ST
  behaviour, and MAME alone for the arcade games (Final Fight, Crude Buster), whose boards this emulator
  does not model.
- **Design digest**: a section in several READMEs that restates the game's rules in plain terms, without
  addresses, for reuse in a new design. Its letters (S, M, G, ...) point to the topic doc proving each line.

## Evidence labels

Every claim in a topic doc says how it is known. The words differ a little between games; they map onto
three strengths.

| Strength | Labels used | Meaning |
|---|---|---|
| Checked against the game | proven, gated, verified, [Proven] | A model matched the game's own code with a match count, usually through a gate. |
| Seen running | live, observed, traced, matched, [Corroborated], [Observed] | Seen in a trace, a watch, a census or a screenshot of the running game. True in the runs made; not shown to hold in every case. |
| Read only | code read, read, inferred, [Hypothesis] | Read from the disassembly or reasoned from other findings, not run. |

PowerMonger's `ai.md` ("Evidence taxonomy") splits the middle row into Corroborated (a code reading and a
run agree) and Observed (true in the runs made). A negative such as "nothing writes this byte" is at most
"seen running" unless the doc gives a whole-program search.

## The Atari ST

- **Atari ST**: a home computer released in 1985, built around the Motorola 68000. The games here were
  written for it, apart from the two arcade games, whose boards also use a 68000.
- **68000**: the Motorola CPU of the ST, 8 MHz, 16-bit data bus, no floating point and no divide wider
  than 32 by 16 bits.
- **TOS**: the ST's operating system in ROM. These notes use TOS 1.00. Its layers are **GEMDOS** (files
  and processes: `Fopen`, `Fread`, `Pexec`), **BIOS** and **XBIOS** (devices, screen, disk sectors:
  `Rwabs`, `Setscreen`), each reached by a `trap` instruction. Many games bypass TOS once loaded.
- **VBL**: the vertical-blank interrupt, raised once per displayed frame (50 times a second on a PAL
  ST). Games use it to time their loops and swap screens.
- **low resolution**: 320 x 200 pixels in 16 colours from a palette of 512.
- **bitplane, plane**: low resolution stores each group of 16 pixels as four 16-bit words, one per
  plane; a pixel's colour number is its bit in each of the four. Drawing one colour means setting or
  clearing a bit in each plane.
- **sprite**: a small image drawn over the background by the game's own code; the ST has no sprite
  hardware.
- **blitter**: in these notes, usually a game's own routine that copies an image onto the screen with a
  mask. The block-copy chip of the same name was fitted only to later ST models, and the games here do
  not use it.
- **MFP** (MC68901): the chip that provides timers A to D and the interrupt lines. Timer B counts
  display lines, which lets a game change the palette part-way down the screen (a **raster split**).
- **IKBD**: the keyboard processor. It sends key presses, mouse movement and joystick state to the CPU
  through the **ACIA** serial chip.
- **FDC** (WD1772): the floppy disk controller; sectors reach memory by **DMA**.
- **PSG** (YM2149): the three-voice sound chip. Some games play sampled sound by writing its volume
  registers at a high rate.
- **PRG, TOS, AUTO**: a program file; `\AUTO\` is the folder whose programs TOS runs at boot.

## Programs, disks and code

- **crack**: a copy of a game with its copy protection removed, released by a cracking group (named in
  brackets, as in [cr Replicants]). Most games here were studied from such copies, which is why each
  README records exactly which disk and file hashes it used.
- **compilation disk**: one floppy holding several cracked games behind a menu (Medway Boys, Zuul,
  Automation and others).
- **trainer**: a cheat menu a cracker added before the game starts.
- **packer, depacker, crunched**: a compressed program that unpacks itself at load time (Automation's
  `LSD!`, `Ice!`). The game's real code exists only after the depack.
- **compiled C, hand-written**: a game built with a C compiler leaves a `link A6` stack frame at the
  start of most functions, which a decompiler such as Ghidra can read; a hand-written assembly game has
  none, so its routines are read from the disassembly.
- **attract mode**: the self-playing demo a game runs when nobody is playing.
- **`.sym` file**: a game's list of names for addresses, used by the disassembler (`tools/rdis.py`) to
  print names instead of numbers.
