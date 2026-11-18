# learning/py

| script | what it does | output |
|---|---|---|
| `hatari_callcap.py <snap> <hexaddr> [nth] [outdir] [--control]` | runs one call of a routine on Hatari's CPU from this emulator's snapshot state and compares RAM and registers with this emulator's `callcap` (`../hatari_oracle.md`) | `scratchpad/learning/hatari_callcap/<addr>_<nth>/` |
| `gate_hatari_callcap.sh` | the same over eight Virus routines, three calls each, then the control; prints `24/24 calls` | `scratchpad/learning/hatari_callcap/gate.log` |
| `hatari_game.py <snap> <hexaddr> <nticks> [outdir] [--until <hexaddr>] [--control]` | lets the game run on Hatari from this emulator's snapshot state with interrupts live and compares the game state at every arrival at a once-per-tick routine with this emulator's own run; `--until` ends at this emulator's first arrival at a game-over address | `scratchpad/learning/hatari_game/<addr>_<nticks>/` |
| `gate_hatari_game.sh [full]` | Virus's demo flight at `Ship_Tick`: 2,000 ticks, or with `full` the whole flight (`11782/11782`), then the control | `scratchpad/learning/hatari_game/gate.log` |

All need a Hatari binary (`HATARI`, default `~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari`) and
`TOS100UK.IMG`; the gates also need `scratchpad/virus/demo/S1b.snap`.
