# learning/py

| script | what it does | output |
|---|---|---|
| `hatari_callcap.py <snap> <hexaddr> [nth] [outdir] [--control]` | runs one call of a routine on Hatari's CPU from this emulator's snapshot state and compares RAM and registers with this emulator's `callcap` (`../hatari_oracle.md`) | `scratchpad/learning/hatari_callcap/<addr>_<nth>/` |
| `gate_hatari_callcap.sh` | the same over eight Virus routines, three calls each, then the control; prints `24/24 calls` | `scratchpad/learning/hatari_callcap/gate.log` |

Both need a Hatari binary (`HATARI`, default `~/Downloads/hatari-snapshot/Hatari.app/Contents/MacOS/Hatari`) and
`TOS100UK.IMG`; the gate also needs `scratchpad/virus/demo/S1b.snap`.
