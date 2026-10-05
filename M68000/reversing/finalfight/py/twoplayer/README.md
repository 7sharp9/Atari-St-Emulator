# Two players, Guy and Haggar, player versus player (pass 4, agent D)

Proves the claims of `../../twoplayer.md`. Every path is derived from this directory (`d`): output and MAME state go under `scratchpad/finalfight/twoplayer/{out,run*}` (gitignored; `FFD_BASE`,
`FFD_OUT`, `FFD_RUN` override, see `run/env.sh`). The ROM image `scratchpad/finalfight/ff_main.bin` (`lua/dumprom.lua`) is read by the Python gates; nothing depends on any other pass
directory. MAME 0.289, ROMs in `~/mame-roms`; each concurrent run needs its own run directory (`FFD_RUN`); the wrappers keep `SDL_VIDEODRIVER=dummy`. Python: `M68000/.venv/bin/python`
(the gates need no third-party module). Character index (`+20`): 0 Guy, 1 Cody, 2 Haggar.

## Reproduce

```
sh run/all.sh        # states, every run, both gate scripts; about 25 minutes with three MAME processes at once; prints the last line of each gate output
```
or step by step: `sh run/make_states.sh ""` (7 states, about 4 minutes), `sh py/char/run_chars.sh <0|1|2>` then `python3 py/char/gates.py [ch]` (about 3 minutes per character), `sh py/pvp/run_pvp.sh`
(about 4 minutes), `sh py/pvp/run_long.sh` (about 20 minutes), `python3 py/pvp/gates.py`.

## States (`run/make_states.sh`; each created twice from a cold boot with identical work RAM)

| state | frame | content |
|---|---|---|
| `dch0_1900`, `dch1_1900`, `dch2_1900` | 1900 | one player Guy / Cody / Haggar chosen on the select screen, bot walked right, Bred (record 12) just spawned |
| `d2p_ch12_1900`, `d2p_ch01_1900`, `d2p_ch02_1900` | 1900 | two players (P1 Cody / P2 Haggar; Guy / Cody; Guy / Haggar), no bot, no enemies |
| `d2pw_ch12_1930` | 1930 | two players Cody and Haggar, bots walked, Bred alive |
| `d1p_boss`, `d2p_boss` (made by `run_long.sh`) | 7481, 5933 | one / two players at the stage 0 area 2 trigger, camera `$aa0`, `190/191 = 0/2` |

## Scripts

| script | what it is / proves |
|---|---|
| `lua/lib.lua` | `lua/lib.lua` of the parent plus the P2 ioport fields (`right2 left2 up2 down2 b1_2 b2_2 b3_2 coin2 start2`) and an assert on an unknown field name (a typo once left a key held) |
| `lua/bot2p.lua` | cold boot, coin(s), one- or two-player select schedule (`FF_CH1`, `FF_CH2`), then a state-reading bot per player (`stagebot.lua`'s logic with the lane direction corrected), per-player GOD, `S`/`D` spawn logs, stop conditions, `FF_LOAD`, `FFD_SCHED`, `FFD_EXTRA`, `FFD_SHOTS`, `FF_BOT_NOATK`, `FF_BOT_STUCKSTOP` |
| `lua/bot_bp.lua` | `bot2p.lua` plus debugger breakpoints (`FFD_BPS`, `FFD_BPOUT`; `FF_MAMEARGS="-debug -debugger none"`) |
| `lua/pvp.lua` | load a two-player state, apply a plan on both players, poke, log both player records every frame (key=value) |
| `lua/pdrive.lua`, `pbp.lua`, `extra_enemy.lua`, `extra_dummy.lua`, `extra_dummy2.lua`, `extra_dummy3.lua` | one player driven from a state with a dummy enemy next to him (copies of `py/player/` plus: `extra_dummy2` refills the dummy below hp `$180`, `extra_dummy3` stops moving it while a grapple is on) |
| `lua/extra_target.lua`, `extra_fuzz_tok.lua`, `extra_poke127.lua`, `extra_join.lua`, `extra_terr.lua`, `extra_p1terrain.lua` | per-frame loggers and pokes: target fields and health at spawn (`T`, `H`, `G`, `P` lines), token/rank/mask fuzz, `127(A5)` poke, join globals, terrain result `+88/+89/+102` |
| `lua/pokes_*.lua`, `lua/probe_start.lua`, `probe_sel.lua`, `probe_credit.lua`, `py/sched_*.lua` | position pokes (adjacent players, lane offsets, low hp, mid lane); cold-boot probes of coin, start and select |
| `run/ffrun.sh`, `ffmame.sh`, `env.sh` | MAME wrappers and the path variables |
| `run/run.sh`, `crun.sh`, `prun.sh`, `make_states.sh`, `all.sh` | a `bot2p.lua` run; one character from `dch<c>_1900`; a `pvp.lua` run; the states; everything |
| `py/char/charlib.py` | ROM readers (character rows `$a124`, attack boxes, awards `$7ac6`, strikes `$db6e`, `$d86e`, `$d8a6`, chain limit `$be92`) and the pdrive log reader |
| `py/char/run_chars.sh`, `gates.py`, `combo.py`, `grapple.py`, `motion.py`, `plans/*.lua`, `bps/backgrab.lua` | the per-character runs, the 26 gates, small reports (hits against the ROM, grapple timeline, kinematics) |
| `py/pvp/run_pvp.sh`, `run_long.sh`, `gates.py`, `pvlib.py`, `plans/*.lua` | the PvP and two-player runs, the 14 gates |
| `py/pvp/target_check.py`, `token_decide.py`, `token_check.py`, `p2_entries.py`, `census2p.py`, `bps_*.lua` | target rule from `extra_target` logs; token request pairing from breakpoint logs; the byte-15 flag against 1P and 2P spawn logs; `census.py` with `--p2` |

## Gates

`py/char/gates.py` (26, per character unless noted): combo chain id, damage, type and award against the ROM (Guy 5/5, Cody 4/4, Haggar 3/3); jump attacks; special; grapple strikes (damage, type,
award); throw landing damage (Guy -30, Cody -40) or Haggar's pile driver (-50, type 6, +1000); the throw turns the player on the away press (Guy, Cody) or toward press (Haggar); wall jump
(Guy: grip and both bounce branches; Cody and Haggar never enter sub `$16`); random drives equal the ROM row on every hit; Haggar's jump slam (-70, type 5, +1200, 3 runs); walk speed order
Guy > Cody > Haggar.

`py/pvp/gates.py` (14): PvP 1 hp per non-hard hit (9/9); award to the attacker (9/9); P2 on P1 (3/3); `+148` 100 frames; the special spin passes through; depth window [-9, +12] (22/22); kill by a
partner (hp -1, 92-frame fatal knockdown, 60 frames in state 4); P2 inputs 7/7; P2 kill award; target rule 70/70; token request 86/86; script byte 15 (5/5); pool-2 health and tables equal with two
players (17/17); pool-4 boss hp 300 to 450 and table `+$c0`.

## Measured, not gated

The ground line axis (`plans/updown15.lua`, `updown30.lua`, `updown60.lua`, run with `run/crun.sh`; `lua/pokes_midlane.lua`): Up raises both `+10` and `+14`, Down lowers them, 0.8 px per frame, lane limits `$10` and
`$3f` in stage 0. The mid-game join, the select screen and the credit flow are probes (`lua/probe_*.lua`, `lua/extra_join.lua`, `py/sched_join.lua`) with screenshots.
