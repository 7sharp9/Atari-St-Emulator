# py/placement: the placement tables and who creates every record of a played stage

Scripts behind `placement.md` (`$6026`, the 14-byte entries, `$61a8`, the creator of every record seen in stage 0, the pool 8 / `$a` / 6 / `$12` / `$14` roles).
Static readers work on `scratchpad/finalfight/ff_main.bin`; the live scripts run MAME through `run.sh`. Roots come from `__file__` or `M68000_ROOT`
(this directory must stay four levels below `M68000/`). Python needs numpy and Pillow for `hidediff.py`/`hudsheet.py`: `M68000/.venv/bin/python`.
MAME run and output directories: `BB_RUN` and `BB_OUT` (default `scratchpad/finalfight/placement/{run,out}`); two runs must not share them.

`bbot.lua` is the logging variant of `lua/stagebot.lua`: a copy of its pass-4 form with the same bot (the saved boss state, work RAM `a0cb6b52...4837`, is
reproduced bit for bit with every log switched on), per-pool strides (pool 14 is `0x40`, 30 records), and extra logs. It lacks the later `FF_BOT_HP0` and
`FF_BOT_LEAVE`, and its prop fallback reads the prop y at `+14` where the current file reads `+10`; use `lua/stagebot.lua` for playing, this one for the logs below.

## Scripts

| file | what it does / proves |
|---|---|
| `run.sh <boss, stage1, full or custom>` | runs `bbot.lua`. `boss`: cold boot to camera `$aa0` (frame 8298); `full`: cold boot to the stage byte 1 (frame 11595); `stage1`: from a state `sb_boss` that you copy into `$BB_RUN/sta/ffightuc/`. Logs: `FF_BOT_LOG` per 10 frames and `S` lines; `FF_BOT_WLOG` every write to the in-use word, tag/kind word, `+20` word and x/y of every pool record with the pc (the creator); `FF_BOT_SLOG`/`FF_BOT_LOGFROM` the same census from frame 1300 (before the bot drives); `FF_BOT_TAP=lo-hi,..` with `FF_BOT_TAPPC=lo-hi` and `FF_BOT_TAPLOG` write taps (the HUD name builder `$5b66e` also logs the HUD record's tag/kind/`+20`); `FF_BOT_BP="addr:fmt:args;.."` with `FF_BOT_BPLOG` debugger breakpoints (needs `FF_MAMEARGS="-debug -debugger none"`; use from a cold boot only, see below); `FF_BOT_SAVEAT=f1,f2` saves `bb_<f>`, `FF_BOT_SHOT` screenshots |
| `gates.sh` | the gate: run 1 (`boss`, debugger, taps, saves) and run 2 (`full`), then the five checks below |
| `rom.py`, `placetab.py` | ROM readers: the placement lists (`areas`, `initlist`, `trigmodes`, `entry`) |
| `dumpplace.py [stage..]`, `summary.py` | print every entry of the init and trigger lists; per-area counts, trigger ranges, pool 8 kinds and props placed |
| `match.py <bp> <S log> <W log>` | every entry `$61a8` was called for (breakpoints `$6072`, `$60da`) against the record that appeared: pool, kind, `+20`, `+21`, x, y, `+96` |
| `classify.py <S log> <W log>`, `joinS.py`, `wparse.py` | every record first seen live grouped by the pc that created it (the `W` log joined to the `S` line by pool, record and frame) |
| `flagcheck.py <tap> <bp>` | kind 1 tile patches: a write of 1 to the flag array `$ff12de+ch` against the patch call of the record with `+20 = ch` |
| `hudnames2.py <tap>` | HUD name pointer writes (`$5b66e`) with the HUD record's tag, kind, `+20` and the ROM string |
| `hudpoke.lua/.sh`, `hudsheet.py` | push a record into the HUD enemy-bar ring as `$28d0` does and crop the printed name; `hudsheet.py` does the 8 records of `placement.md` ("Props") from the `bb_*` states |
| `hide.lua/.sh`, `hidediff.py <state> <addr>[:label]..` | zero a record's in-use byte for a few frames and diff the screenshot: the changed pixels are its sprite (`FF_HIDE_PRE`, `FF_HIDE_F`, `FF_HIDE_PRINT=1` lists pool 8). A tile-map writer (GO arrow, tile patches) shows no change |
| `ramdump.lua/.sh` | work RAM of a loaded state (for the hashes in `placement.md`) |
| `sites.py` | every `jsr $3892/$38ce/$390a/$3946/$3982/$39be/$39fa` site with the handler range it sits in and the constants it stores (`kind`, `+20`, `+21`) |
| `drops.py` | the prop drop decode of `$5a934` for every `+21` the tables place, with prop and item names from the ROM text |
| `callers.py <hex addr>..` | direct callers and literal references of any address (jsr, bsr, jmp, bra, `#imm.l`) |

## Gate (`sh gates.sh`, about 70 s; counts from a fresh run of this directory)

| check | result |
|---|---|
| `match.py` | 44 matched, 1 blocked by `$3e88`, 1 unmatched (the two-player-only entry), of 46 entries |
| `classify.py`, boss run | 118 of 118 records attributed to a creator pc |
| `classify.py`, full run | 159 of 159 |
| `flagcheck.py` | 6 of 6 flag writes followed by their patch within 12 frames (14 patch calls) |
| `hudnames2.py` | 10 name keys, each equal to the ROM string |
| saved boss state | work RAM sha256 `a0cb6b520ec11ed769dc6466e70a29fcbde99b6ce5df8a13aa1c8ae5f1504837`, equal to `py/stage`'s `sb_boss`, with `-debug`, taps and saves on |

## Traps

- A state loaded under `-debug` resumes on another trajectory than the same state without it (camera `$aa4` against `$aa0` at frame 8300; the stage-1 bot reached the
  stage byte 1 at 11595 without and never in 22,000 frames with). Cold boots are identical with and without `-debug`. Breakpoint counts therefore come from cold boots.
- `screen:snapshot` hide-diffs need `FF_HIDE_F` of 3 or more: the sprite list is built a frame ahead.
- `-seconds_to_run` counts emulated time, which a loaded state restores: a small value ends a resumed run at once.
- A breakpoint action with an invalid expression (`d@sp`, `sp` as register) prints nothing and the breakpoint looks never hit; use `a7`/`d@a7`.
