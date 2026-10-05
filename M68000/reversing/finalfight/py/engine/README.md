# engine: the deferred rings, the shaker, terrain codes, prop victims, the carrier and lift actors (pass 5, agent B)

Proves the claims of `../../kernel.md` ("The two deferred rings"), `../../frame.md` ("The screen shaker", the tag-`$a` victim handlers), `../../placement.md` ("Terrain codes", "The region word `$726e0`",
"Pool-4 kind 7: the carrier", "The `$ffb228` actor") and the Haggar damage in `../../twoplayer.md`. MAME 0.289 headless, `SDL_VIDEODRIVER=dummy`, no focus grab. Every path is derived from
`__file__` (four levels below `M68000/`, like `py/placement`); `M68000_ROOT` overrides. Work area `scratchpad/finalfight/engine/` (`runs/run_<name>`, `out/`, `run/sta/ffightuc/`); `FFB_BASE` moves it.
Python: `M68000/.venv/bin/python` (numpy and Pillow for the render gates). Each concurrent run needs its own run directory; every wrapper makes one per name.

## Reproduce

```
sh gates.sh            # all batches: states static cold state debug sound; about 25 minutes (the sound sweeps are 5 of them), up to 12 MAME processes at once
sh gates.sh state      # one batch
python gates.py        # 16 gates, PASS/FAIL with counts; python gates.py shaker haggar ... for a subset
```

Inputs it needs: `scratchpad/finalfight/stage/run/sta/ffightuc/{sb_boss,sb_s1,sb_s2,sb_s6}.sta` (copied into the work area), `placement/run/sta/ffightuc/bb_2500.sta`, `twoplayer/run_p/sta/ffightuc/dch2_1900.sta`,
`ff_enemies.sta` (via `py/ai_kind123/run.sh`). Batch `states` builds the three poke states below twice and `gates.py` compares the RAM hashes.

## Scripts

| file | what it does |
|---|---|
| `gates.sh`, `gates.py` | runs every batch and checks the 16 gates (`region ring_static ring_live shaker haggar terrain drums glass car shake_sites edi k7 elevator elevator0 states sound`) |
| `ffb.sh` | MAME wrapper: `ffb.sh <script.lua> [seconds]`, own run dir `$FFB_RUN`, `FFB_DEBUG=1` adds `-debug -debugger none`; `FF_DIR` = `lua/` |
| `playtap.sh`, `tapbot.lua` | `playtap.sh <name> boss\|stage1\|custom`: the `py/stage` bot run with write taps (`FF_W`, `FF_TAP_OUT`); `LUA=` swaps the driver (`sndbp.lua`) |
| `ringcallers.py`, `ringtable.py`, `ringmsgs.py` | static: every `$2874` call with the preceding `D0` immediate (look-back heuristic), decoded to type and message text; the text tables `$65f4c`, `$6718a` |
| `soundids.py` | static: wrappers `$a10-$be6` and every caller of `$9d0/$9de/$9e4/$9f8` by id and by code band |
| `sndbp.lua` | bot run with a breakpoint on `$9f8`: id and return address (`d@(usp)`, task stacks are user stacks) per queued sound |
| `z80tap.lua`, `soundtrace.py` | cold boot with taps on the Z80's YM/OKI writes and latch reads and the 68000 latch writes |
| `z80sweep.lua`, `sweepan.py`, `idmap.py` | sound lab: frees every task but the idle one, injects ids through the real ring, logs the Z80 response; per-id summary; the full byte map |
| `shake.lua`, `sh1.sh` | emulates `jsr $1b428` (allocator logic of `$3946`) at chosen frames of any state, logs camera, scroll shadows and the CPS-A scroll writes, snapshots per frame (`SH_SHOT`), `SH_P20` pokes the axis |
| `hag.sh`, `extra_hag.lua` | Haggar runs through the pass-4 `twoplayer` harness (`crun.sh`, state `dch2_1900`) with write taps on the victim's health and the shaker flag; `FF_EHP` sets the victim health |
| `terr.lua`, `tr1.sh`, `dumpgfx.lua`, `dg.sh`, `scanterr.py`, `shiftdiff.py`, `a5refs.py` | terrain: block pokes (`TR_SETBITS=x:y:code`, `TR_CLRADDR`), key holds, snapshots, read taps on the marker blocks; gfx RAM and work RAM dump; scan of the scroll-2 map for codes and 80-entry runs; whole-frame vertical shift between two PNGs; scanner for `d16(A5)` operands |
| `propdrive.lua`, `pd.sh`, `poolpeek.py`, `actfilter.py` | state driver: relative-frame key levels, pokes, `PD_ADDRS` breakpoint counts (needs `PD_DEBUG=1`), per-frame logs of pool a (`PD_PROPS`), pool 4 (`PD_P4`), pool 8 (`PD_P8`), the `$ffb228` actor (`PD_ACT`), `PD_SAVE=rel:name`; RAM dump reader; filter that keeps only changes |
| `k3run.sh`, `noplan.lua` | the kind 1-3 harness (`py/ai_kind123`) with `hits.lua` counts on the `$1b428` sites |
| `dmk.lua`, `bk.sh` | `py/boss/dm.lua` plus `DMK_KILLAT` (hp -1 into the spawned pool-4 record every frame); `bk.sh <name> kind:ch:x:y:lvl <killat> <frames>`; `BK_LUA` runs another driver |
| `regionsets.py` | diff of the two copies of the placement and script tables selected by `$726e0` |

## Saved states (recipes; the `.sta` files stay in `scratchpad/finalfight/engine/run/sta/ffightuc/`, listed in `scratchpad/ANCHORS.md`)

Frames are the absolute MAME frame at the save; "rel" is relative to the loaded state. Built twice in fresh run directories, work RAM identical both times; load without `-debug`.

| state | recipe | frame | work RAM sha256 |
|---|---|---|---|
| `p5b_bs7` | `sb_s6`, at rel 410 poke `175(A5)` := 01 and `193(A5)` := 4 (`$ff80af`, `$ff80c1`), save at rel 1520: bonus stage 7, area 0, Cody controllable | 41553 | `f92fd2cec0c5eb1e8b866deaef61d2c9750450e84215e64ffdd4265217713099` |
| `p5b_k7` | `sb_s2`, `297(A5)` := 1 (`$ff8129`) at rel 600, save at rel 740 (the carrier appears at rel 734) | 43524 | `4c971a7df73ef98b474a82a763cffa421bd747c0eaaeb6d1ff62d8df3cad1ce9` |
| `p5b_s5pre` | `sb_s6`, at rel 410 poke `175` := 01 and `193` := 6, save at rel 1790: stage 5 area 0, before the scene | 41823 | `737385478131f946c84379147f6133696a6914a261a636c36b7394030a80302e` |

Other recipes: stage 3 area 0 from `sb_s6` with `175` := 01 and `193` := 3 at rel 410, then `297` := 1 at rel 1900, gives area 1 (the lift actor) about rel 3840; the stage 5 elevator from `p5b_s5pre` with camera x `$ff8412` := `$560` and player x `$ff856e` := `$5e0` at rel 20 and `291(A5)` := 1 (`$ff8123`) at rel 60; the EDI.E death with `bk.sh` (see the gate `edi`).

## Traps

- The ring at `324(A5)` is a text ring; sound is `388(A5)`. Do not read an old note that calls `$2874` a sound sender.
- `d@(sp)` inside a task is the supervisor stack: use `usp` for return addresses of task code.
- `dm.lua` before this pass zeroed `+0..+191` of a hand-spawned record, including `+78`; EDI.E then took an address error at `$44fc` and the machine restarted. Keep `+78`.
- `ringcallers.py` pairs each call with the nearest earlier `move.w #imm,D0`; a few sites reached through a branch may be mispaired (read the listing before quoting one).
- `z80sweep.lua` frees task slots: a poke lab for the Z80 side only. The 68000 never sends ids `>= $60` except `$f9` in the test mode.
- `PD_SAVE` and `SW_`/`SH_` names accept letters, digits and `_` only; the state goes into the run directory of that name (`runs/run_<name>/sta`), `gates.sh` copies it.
- `hag.sh` needs the pass-4 state `dch2_1900` (`twoplayer/run_p`); the Haggar gate reads the victim's first health write at `$d9b6`/`$d9e2`.
- A state loaded under `-debug` takes another trajectory: the debug batches (`PD_DEBUG`, `k3run.sh`, `bk.sh`) only count breakpoint hits in short runs.
- In `shake.lua` the camera is not restored between frames: the alternating steps cancel, so a shake leaves no offset only if it runs to the end (the restart path of `$1b428` undoes a pending negative step).
- Hand spawns of pool-4 kinds 1, 3, 4, 5 stay inert without their trigger pokes; kind 2 (EDI.E) works.
