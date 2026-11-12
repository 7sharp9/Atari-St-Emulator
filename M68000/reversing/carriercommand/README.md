# carriercommand: Carrier Command (Realtime Games / Rainbird, 1988)

A real-time strategy and vehicle simulation: the player's carrier and the enemy's compete for a
64-island archipelago, capturing islands, turning them into resource, factory or defence bases and
supplying the carrier through the network they form. Reached in the emulator: the language menu, the title
menu with its 3D attract scene, the Strategy game with the carrier at Vulcan and the Action game's opening. The game is hand-written
assembly (1 `LINK` frame, about 920 `RTS`), so it is analysed from traces and callcaps, not a decompile.

| Doc | Covers | Proof |
|---|---|---|
| `ai.md` | the enemy carrier's state machine, how it picks its next island, capture and attack, fighting the player's carrier and retreat, island defences, difficulty, the cheat mode, the two games | target choice 1344/1344 score words and 21/21 decisions, with constant-by-constant controls; difficulty A/B/C 3/3 arms; combat states driven state by state |
| `vehicles.md` | the player's carrier motion and autopilot, the arctangent, repair priorities, missiles and flares, the craft slots | carrier 150/150 and 600/600 ticks (1950/1950 in the full run), arctangent 529/529, repair 10/10 and 12/12, flares 5/5 |
| `economy.md` | the fixed island tables, world creation, the RNG, the supply graph and distance matrix, production, production lines and packets, island building | production 175/175, line cost and steps 14/14 each, landings 4/4, RNG 1/1 |
| `render.md` | the 3D engine: sine table, chained 2D rotations, projection, depth tree plus BSP plus back-face culling, the self-modifying span filler, the model format | sine 4096/4096, rotations 360/360 and 120/120, projection 480/480, face test 120/120, spans 780/780 |
| `packer.md` | Automation Packer V2.3r: the `LSD!` LZ77 format, the backwards in-place depack and its safety margin, ratios against modern compressors | depacker output identical to `tools/lsd_depack.py`; minimum read/write gap 218 bytes on all six packed files |

Gates: `uv run python tools/gates.py run carriercommand` (`gates.toml`, five gates, all PASS).

What stands out: the enemy's whole strategy is one additive score over the 64 islands plus an argmax, with a
probable bug that always treats island 4 as connected to its network; difficulty only tunes the island
defences, and past `$8000` a signed compare turns it back to the easiest setting; the enemy carrier only exists
as a physical object while it is fighting; captured islands get a random type; the carrier's autopilot steers
in a straight line and runs aground; repair shares a fixed capacity among the systems at the top priority; a
missile is decoyed by whichever flare its scan meets last within 6000 units; the economy routes goods as packets over an all-pairs distance
matrix relaxed 8 rows per frame; the renderer patches its own span filler per colour and uses three layers of
hidden-surface removal with no 3D matrix anywhere; and the cheat phrase is "GROW OLD ALONG WITH ME", typed
while paused.

## Provenance

- Zuul #45 compilation (`Zuul #45.zip`, one `ZUUL045.MSA`, 792,456 bytes, sha256
  `cfa9031b32e63562e10e3cf30e9d9b03cf5a4590faee2735a6d3d47b150dcd25`), converted with `tools/msa2st.py` to an
  839,680-byte `.st` (sha256 `c098aee2ba30b05a9ba7bd6d80678d41825854cc67636b136d586058a39f364b`). Other games on
  the disk: Arena, Crystal Castles, Deep Space, Trantor, Star Raiders.
- Carrier Command is `PACT2.PRG` (135,486 bytes), wrapped in Automation Packer V2.3r (`packer.md`); it unpacks
  to a 323,196-byte GEMDOS program (sha256 `0d3938982b8a909de79b52d26824ba05b42980cbcdcd94ce790b912bcfe20448`)
  with the copyright string "COPYRIGHT REALTIME GAMES SOFTWARE LTD 1987/88".
- **The crack leaves a time bomb running.** The main loop (`$3a40..$3a4c`) pushes a word onto the stack on every
  pass unless the manual-word protection recorded an answer (`$126d` set and the answer length `$126e`
  nonzero). The protection (`$9da2`, reached from the language menu, whose 1..3 key picks one of three 64-word
  lists) has its key reads replaced by `nop`s and a `bra` past the store in this copy, so `$126e` stays 0 and the
  stack sinks 2 bytes per pass (inferred as the cracker's patch: no original to compare). About 1.55G steps
  after `c_s30` (roughly 43 minutes of play) it reaches the sound-channel records at `$4f032`; the VBL handler's
  register save turns a channel pointer into `$ff412d00`, the read at `$1ff5a` bus-errors (correct: `$400000`
  and up is a bus error on the ST), the game's bus-error handler is a bare `rte` that returns to the faulting
  address with the stack 8 bytes deeper each time, and the stack spirals down until a frame lands on `$4` and
  the CPU halts with a double bus fault. A real ST would do the same (inferred). Proven: the stack falls 20
  bytes per 10 passes from `ai/nat/d2.snap` and stays put with `w 126c 00ff0001`; a 750M-step run with that poke
  does not fault, the unpoked one halts within 700M. **Long runs from `c_s30` need `w 126c 00ff0001` first.**
  The halt reproduces within 50M steps from `crash/c10.snap`, and the first bad read about 16.8k steps into
  `crash/f03.snap`.
- The menu-disk copies of `PACT1..4.PRG` have `$ffffffff` as the first long of the text where the program
  needs `movea.l 4(a7),a5` (`2a6f 0004`, as in `STRAID.PRG`), so run alone they take a Line-F exception at
  once (inferred: the Zuul menu loader writes the instruction before launching). Restoring the 4 bytes at file
  offset `$1c` gives `CARRIER.PRG` (sha256 `34caa0021659ecd33f28fbd368f1672645b384cc0e5a4392c8bf7b37b54cc937`),
  put alone in `\AUTO\` on a blank double-sided disk: `carrier_auto.st` (sha256
  `54261b30545e9a354ada6f0a3e11b80000432029d769584938a36984d8ed9464`).
- After depacking, the game prints "Yes, I have kicked out the OS", takes over the machine and runs from low
  RAM (code about `$3900..$235f8`); addresses in these docs are those runtime addresses.

## Running it

```
W=scratchpad/carrier
uv run python -I tools/msa2st.py $W/zip/ZUUL045.MSA $W/zuul045.st
uv run python -I tools/extract_disk.py $W/zuul045.st $W/files
# patch PACT2.PRG's text long at offset $1c to 2a6f0004 -> $W/CARRIER.PRG, then:
uv run python -I tools/make_blank_disk.py --sides 2 $W/blank.st
uv run python -I tools/add_file_to_disk.py $W/blank.st $W/CARRIER.PRG --auto --out $W/carrier_auto.st
ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll 80000000 snapshot $W/c80.snap --disk-a $W/carrier_auto.st
(cat reversing/carriercommand/drive.txt; echo "snap $W/c_s30.snap") | \
  ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $W/c80.snap repl
```

The banner "AUTOMATION PACKER V2.3r" appears at step 2.55M, the depack finishes by 7.4M and the language
menu is up by 80M (`language.png`). `drive.txt` presses 1 (English), waits 60M steps for the title menu
(`title.png`), moves the pointer 55 pixels up onto "Start Strategy Game", clicks, and runs 30M steps into the
game (`strategy.png`). Both the cold boot and the drive are deterministic: rerunning them reproduces `c80.snap`
and `c_s30.snap` byte for byte.

**Mouse input needs a workaround.** The game's ACIA handler (`$1794c`) lowers the interrupt mask to 5 on entry.
The emulator raises the next IKBD interrupt as soon as a byte is read and does not model the MFP in-service
register, which on hardware holds off a second channel-6 interrupt until the handler clears it
(`bclr #6,$fa11.w` at `$1797a`). A `mouse move` packet's three bytes therefore nest three handlers deep and are
processed last byte first, and the pointer never moves. `drive.txt` sends each packet byte on its own `kbd`
call with 3,000 steps between them (header `$f8`, `$fa` with the left button down). Keyboard input is one
byte per key and works normally. This is an emulator gap, not fixed yet.

## Snapshots

All in `scratchpad/carrier/` (indexed in `scratchpad/ANCHORS.md`):

| Snapshot | State | Made by |
|---|---|---|
| `c80.snap` | language menu | cold boot, 80M steps |
| `c_eng.snap` | title menu, 3D attract | `c80` + `kbd 02/82` + 60.4M |
| `c_mv.snap` | pointer on "Start Strategy Game" | `c_eng` + the `$f8 00 c9` packet + 0.4M |
| `c_s30.snap` | Strategy game, carrier at Vulcan (-4415,-4288, bearing 005), `$1244 = $ff` | `drive.txt` from `c80` |
| `ai2/menu_0.snap`, `ai2/menu_15.snap` | Strategy and Action game starts | each button clicked from `c_mv` (`py/ai2/menu.py`) |
| `ai2/st2.snap`, `ai2/st56.snap` | enemy carrier repairing at island 56; the player carrier at island 56 for the defence census | `py/ai2/drive.py` from the attack poke run |
| `crash/f03.snap`, `crash/c10.snap` | the leaked stack just before it reaches the sound records; 50M steps before the double bus fault | bisected from `ai/nat/d2.snap` |
| `ai/nat/d1,d2`, `ai/nat2/e2..e12` | enemy target decisions from a run of `c_s30`, stopped at `$1ad02` (the `nat2` run pokes `$11c0` to 1 after each decision to skip 500M-step journeys) | `ai/nat*/script.txt` |
| `ai/s1..s6b` | target decisions after single-variable pokes (`ai.md` section 2) | forced state 1 + pokes + `bp 1ad02` |

## Architecture

The VBL handler is `$176d0` (every 12,000 steps); the main loop runs about every 6 VBLs. Per main frame it
runs the enemy carrier's state machine (`$1ac8c`, from `$3a04`, skipped while paused), one island's building
tick (`$18106`, round robin), every 4th frame the economy chain (`$f254`), the entity dispatcher for vehicles,
drones and island structures (`$193dc`, a jump table by type), and the 3D frame (`$14152`). Shared mechanisms:

- **Fixed tables plus simulation.** The map is data (`$4d41a`); the starting state is grown by running the
  ordinary island tick 500 times at instant-build speed.
- **One graph, two uses.** The adjacency lists at `$22afa` and the distance matrix at `$67b40` route the
  economy's packets and feed the enemy's target score (row 63) and the "ISOLATED" display (row 0).
- **Work spread over frames.** The distance matrix is relaxed 8 rows per call; islands are ticked one per
  frame.
- **Self-modifying inner loops.** The span filler is patched per colour.

## Files

| File | What |
|---|---|
| `ai.md`, `economy.md`, `render.md`, `vehicles.md`, `packer.md` | topic docs |
| `carriercommand.sym` | routine and table names, each from its body |
| `drive.txt` | REPL input from `c80.snap` to `c_s30.snap` |
| `gates.toml` | the promoted proofs for `tools/gates.py` |
| `language.png`, `title.png`, `strategy.png` | milestones |
| `cheat.png` | "Cheat Mode active" after the phrase |
| `islands.png` | the 64 islands from the fixed tables, starting owners and the supply graph (`py/world/render_map.py`) |
| `models.png` | the 3D model table decoded and drawn (`py/render/sheet.py`) |
| `py/ccpaths.py` | repo root and work dir (`$CARRIER_WORK`, default `scratchpad/carrier`) for every script |
| `py/autopack_depack.py` | the Automation Packer depacker and its in-place gap check |
| `py/ai/` | `score.py` (target-choice model), `gate_score.py` |
| `py/world/` | `rng.py`, `prove_production.py`, `prove_line.py`, `prove_transfer.py`, `gate_economy.sh`, `render_map.py` |
| `py/ai2/` | `drive.py` (state-change log for the enemy carrier), `defence.py` (structure launch census with a difficulty poke), `menu.py`, `gate_difficulty.sh` |
| `py/units/` | `carrier_proof.py` (per-tick carrier model against the emulator), `atan_port.py`, `atan_grid.py`, `repair_proof.py`, `flare_test.py`, `gate_units.sh` |
| `py/render/` | `rig.py` (REPL and callcap driver), the five gates, `gate_render.sh`, `model.py`, `sheet.py`, `views.py`, `show.py`, `seq.py` |

## Not exercised in the emulator

The Manta and Walrus flight and driving models (no snapshot has a launched craft), a drone launcher or command
centre firing, the island-capture end of an attack, the production-priority and fuel screens, saving and
loading. The decoded 3D model drawing order has not been compared with the game's.
