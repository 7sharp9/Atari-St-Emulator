# ai_kind78: kinds 7 and 8 (`ai.md`, "Kinds 7 and 8")

Static tools and the spawn harness that proved the kind 7 / kind 8 claims. Every path is derived from `__file__`
(`M68000/` is four levels up). Outputs go to `$FF_E_OUT` (default `scratchpad/finalfight/p3/e/out`), the MAME run directory
to `$FF_E_RUN` (default `scratchpad/finalfight/p3/e/run`); `ffrun.sh` copies `ff_enemies.sta`, `ff_gameplay.sta` and `ff_k8.sta`
into `<run>/sta/ffightuc/` when they are missing. MAME 0.289 and `~/mame-roms` as in `../../README.md`; `python3` needs no extras.

## Static

| file | what it proves | how to run |
|---|---|---|
| `rdis.py` | recursive-descent lister that follows `bra/bcc/bsr/jsr/jmp` and resolves the `move.w N(PC,Dn.w),D1 / jmp\|jsr M(PC,D1.w)` word-offset dispatches with signed entries; prints reached code, data gaps, every table and the external calls. `--all` listings decode those tables as garbage and cut kind 8 at `$3c500` | `python3 rdis.py 3c000 48000 3c446 3c48e > k78.asm` |
| `dl.sh` | linear listing of the program ROM | `./dl.sh <addr> [count]` |
| `scripts.py` | the 16-byte stage-script spawn entries of both script lists (`$5f5e`, `$5f7e`; `$5f7e` is live) with tag, kind, subtype, x, y, tracked flag; entries two bytes off an adjacent valid entry are dropped. 42 kind 7/8 entries in list 1, none outside the script region | `python3 scripts.py 2 7 8 \| grep '^list1'` |
| `hudnames.py` | the HUD enemy-name sheets of `$5b640` (tag table `$5b682`, kind word table, `+20 * 32`), decoded to text | `python3 hudnames.py 2 9` |
| `anims.py` | resolves the animation setters `$36e24-$36f78` and walks frames (count, event byte, hurt box `+44`, attack box `+45`) | `python3 anims.py 36eb4 0` |

## Spawn harness (needs MAME)

| file | what it does | how to run |
|---|---|---|
| `ffrun.sh` | `reversing/finalfight/ffrun.sh` with its own run directory (`FF_E_RUN`) | called by `sp.sh` |
| `spawn.lua` | loads `ff_enemies`, pops the tag-2 free stack like `$3892`, writes a record like `$5ee6`, then per frame logs the pool 2, 4, 6, 8, `$a` records and Cody (192 bytes hex); pokes (`frame:addr:val:width` or `frame:@off:val:width` into the first spawned record), `FF_PIN`, input plans (`FF_PLAN2`), HUD ring push (`FF_HUDPUSH`), P2 log, script record log, state save (`FF_SAVE_AT`/`FF_SAVE_NAME`), breakpoint counters (`FF_ADDRS`, `FF_MAMEARGS="-debug -debugger none"`). Env documented in its header | via `sp.sh` |
| `sp.sh` | one run: `sp.sh <tag> "<kind:sub20:sub21:dx:y[:f12[:b96]],...>" <rel_stop> [VAR=val ...]` | `./sp.sh t1 "8:0:0:60:47" 300 FF_SPAWN_AT=30` |
| `anal.py`, `cody.py`, `p6.py`, `tgt.py`, `scrwatch.py` | log readers: RLE of a kind's state tuple per frame, Cody hp and state, the tag-6 bottle, the target pointer `134(A6)`, the script record and spawned kinds | `python3 anal.py out/t1.log 8` |
| `plan_hit.lua`, `plan_combo.lua`, `plan_jump.lua`, `plan_grab.lua`, `plan_grab_only.lua` | Cody input plans (`FF_PLAN2`), frames relative to the load | used by the scripts below |
| `addrs.txt` | the 87 handler entry addresses counted by the gates | used by the scripts below |

## Gates (fresh runs, each prints its own counts)

| file | what it proves | result of the last run |
|---|---|---|
| `corpus.sh` then `corpus.py 1 2 3 4 5 6 7 8` | 8 natural kind 8 runs: the execution count of every modelled handler entry equals the number of frames the state log dispatches it | 21 of 21 modelled entries match (`$3c504` 974, `$3c62a` 408, `$3cee2` 75) |
| `forced.sh` then `corpus2.py f_0 ... f_8` | mode-6 reaction ids 0-8 forced into a live record; all reaction sub-state entries | 27 of 27 match |
| `forced2.sh`, `forced3.sh` then `corpus.py g_grabthrow g_release g_thrdie g_held0 g_held3 g_held5 g_held8 g_heldkill` | held, thrown, released, thrown-kill and held-reaction paths | 35 of 35 modelled entries match |
| `cover.py out/c_*.hits out/f_*.hits out/g_*.hits` | which handler entries ever ran | 84 of 87; never: the three kind 7 entries (`kind7.sh` runs them) |
| `kind7.sh` | six kind 7 spawns: handler count = delay + 2 | 6 of 6 (delays 78, 78, 10, 10, 40, 46) |
| `script_spawn.sh` | the stage script itself spawns the two stage-0 area-2 kind 8 entries (`$0707d0`, `$0707e0`) | 2 of 2 |
| `determinism.sh` | the same spawn run in two MAME processes gives one md5 | identical (`8cfade5e...e12`) |

`sp.sh mk_k8 "8:0:0:60:47" 60 FF_SPAWN_AT=30 FF_SAVE_AT=45 FF_SAVE_NAME=ff_k8` regenerates the saved state (written to
`$FF_E_RUN/sta/ffightuc/ff_k8.sta`) and its RAM dump (`$FF_E_OUT/ff_k8_ram.bin`): frame 4195, work RAM sha256 `70381856...af27c`.
The committed copy is `scratchpad/finalfight/p3/e/ff_k8.sta`, which `ffrun.sh` copies into the run directory.
