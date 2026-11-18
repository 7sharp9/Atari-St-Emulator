# learning/py

| script | what it does | output |
|---|---|---|
| `hatari_callcap.py <snap> <hexaddr> [nth] [outdir] [--control]` | runs one call of a routine on Hatari's CPU from this emulator's snapshot state and compares RAM and registers with this emulator's `callcap` (`../hatari_oracle.md`) | `scratchpad/learning/hatari_callcap/<addr>_<nth>/` |
| `gate_hatari_callcap.sh` | the same over eight Virus routines, three calls each, then the control; prints `24/24 calls` | `scratchpad/learning/hatari_callcap/gate.log` |
| `hatari_game.py <snap> <hexaddr> <nticks> [outdir] [--until <hexaddr>] [--control]` | lets the game run on Hatari from this emulator's snapshot state with interrupts live and compares the game state at every arrival at a once-per-tick routine with this emulator's own run; `--until` ends at this emulator's first arrival at a game-over address | `scratchpad/learning/hatari_game/<addr>_<nticks>/` |
| `gate_hatari_game.sh [full]` | Virus's demo flight at `Ship_Tick`: 2,000 ticks, or with `full` the whole flight (`11782/11782`), then the control | `scratchpad/learning/hatari_game/gate.log` |
| `hatari_calls.py <snap> <ticks.log> [outdir] [--calls N] [--control]` | checks a whole `callcap` corpus in one Hatari flight: logs registers and inputs at every entry of `Input_Autopilot` `$2538c` and registers and outputs at every return, and compares each call with this emulator's `callcap` from the pilot corpus (`../../virus/py/pilot/capture_pilot.py`) | `scratchpad/learning/hatari_calls/run/` |
| `gate_hatari_calls.sh` | a fresh pilot capture, then all its calls on Hatari (`3496/3496` at entry and at return), then the control | `scratchpad/learning/hatari_calls/gate.log` |
| `hatari_boot.py <ours.json> [outdir] [--snap <snap>] [--ticks N] [--control]` | cold-boots `scratchpad/virus/aha.st` in Hatari, drives the crack's menus over the control socket (F1, N five times, Return), lets the title time out into the demo and compares every `Ship_Tick` arrival with this emulator's flight (`ours.json` from `hatari_game.py`); `--snap` also counts the RAM bytes that differ at the game start | `scratchpad/learning/hatari_boot/run/` |
| `gate_hatari_boot.sh [full]` | the same over 2,000 ticks, or with `full` the whole flight (`11782/11782`), then the control; needs `gate_hatari_game.sh [full]` run first for this emulator's side | `scratchpad/learning/hatari_boot/gate.log` |

All need a Hatari binary (`HATARI`, default `~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari`) and
`TOS100UK.IMG`; the gates also need `scratchpad/virus/demo/S1b.snap`, and the boot gate `scratchpad/virus/aha.st`.
