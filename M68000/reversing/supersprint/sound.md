# Super Sprint: the sound driver

A scripted three-voice tracker on the YM2149. The emulator never raises **Timer D**, so the game is silent in it; the
driver was proved by injecting ticks and logging every YM register write (below). The effect table and proofs here are
from `py/engine/sound_*.py`; raw register logs and WAV renders are regenerable (`py/engine/sound_render.py`, output under
`scratchpad/supersprint/agents/engine/sound/`, not committed).

## Driver

`Xbtimer(3, ctrl 3, data $cd)` programs **Timer D** at 239.77 Hz. The ISR `$13254` runs the pitch modulators every tick
and the sequencer plus the envelopes every 9th tick (26.6 Hz, one *step* = 37.5 ms). The sound data sit in the tail of
`SUPER.DAT` (block offset `$3179a`, arena `$6d51c`): 35 instrument records and the 10000-byte script area.

- **Script opcodes.** 0-2 note-on with an instrument (logical channel 0 uses the opcode as the PSG channel, channels 1
  and 2 are fixed to B and C); 3-5 set the period; 6 wait (9 ticks per step); 7 and above end.
- **Instrument record, 30 words**: pitch step, base period, pitch interval, initial level, three envelope segment
  lengths and deltas, loop flag, glide/warble flag, tone-only flag and priority. Note-on clears the noise-disable bit
  unless the tone-only word is 8.
- **Priority gate.** The triggers `$126ae $1271c $1278a $127f8 $12866 $128e0 $1294e` start only if `-58(A4)[ch]` (the
  priority of the channel's last note) is below their threshold (4/3/4/1/1/2/1).
- **Engine noise** `$12450(car, speed)`: speed above 20 raises the level by 8 up to `200 + (speed >> 3)` and sets the
  period to `3000 - 4*speed` with interval `18 - (speed >> 3)`; otherwise the level falls by 8 to 130. It is skipped while
  an effect owns the channel.
- **F9** toggles the sound flag `-8068(A4)`; every trigger wrapper checks it.
- **A bug in the driver**: `$13308` has no `rts`. After the channel-C volume write it falls into the envelope routine
  `$1330e` again, so **channel C's envelope advances twice per step**. The Python model needs this to match.

## Effects and tunes

Durations are steps x 37.5 ms. Events are inferred from the call context except where marked *live*.

| trigger | script offset | length | caller | event |
|---|---|---|---|---|
| A `$12522` | 0 | 1.3 s | `$b3fc` (only when `-1896 == 0`) | respawn / helicopter start |
| B `$125e6` | 316 | silence | `$b5f8` | stops A |
| C `$126ae` | 28 | 2.6 s | `$ae0e` | rising four-note arpeggio |
| D `$1271c` | 166 | 3.4 s | `$ea32` | not identified |
| E `$1278a` | 88 | 4.5 s | `$abd4` | bonus pickup (*live*: three hits in 12M race steps alongside the wrench/score draws) |
| F `$127f8` / G `$12866` | 180 / 302 | 1.7 / 1.8 s | via `$a608` / `$a62c` | not identified |
| H `$128e0`, I `$1294e` | 14, 74 | 0.1 s | `$d4fa`, `$df18` | blips |
| K `$12a56` | 242 | 3 s, three voices | `$be40`, `$caa8` | "GO" beep (*live*: once at countdown end) |
| L `$12a8c` | 272 | 3.4 s | `$199de` | shop / prepare screen |
| N `$12b00` | 336 | 7.5 s | `$186ce` | title engine rev |
| O `$12b32`, T `$12e30` | 236, 316 | silence | startup; race start and end (T *live*: three hits at race start) | channel kills |
| S `$12dec` | 2580 | 21.6 s | `$18024` | ready-screen tune |
| R `$12da8` | 7780 | 36 s | `$19164`, `$199de` | prepare / shop tune |
| P `$12c10(Random(5) % 5)` | 3398 / 4488 / 5302 / 5916 / 6794 | 28-38 s | `$1a4ca` | five winner's-circle jingles |

**Unreferenced.** `$129bc` (a three-voice chord, scripts 194/208/222), `$12ac2` (script 322) and `$12d64` (script 906, a
**59.5-second tune**, the longest in the game) have no direct caller and no pointer to them anywhere in RAM (`find_ram_callers`,
`find_literal_ptr`, `find_jump_table_hit`). Instruments 10-14, 18 and 21 are used only by these scripts; 17, 26, 27, 28 by
no script; 32-34 are empty. The 906 stream is 1674 bytes (134 command/argument word pairs, terminator `$00ff`), the same
grammar as the live tunes. It is unused content, not a hidden mode (`secrets.md`).

## Random numbers

`rng(n) = (((Random() & $ffff) >> 1) % n)` at `$a666`; `Random()` is XBIOS #17 (ROM `$fc132c`): if the seed at `$29b8` is 0
it becomes `(hz_200 << 16) | hz_200`, then `seed = seed*$BB40E62D + 1` (32 bit) and the result is `(seed >> 8) & $ffffff`.
There is no custom generator. About 24 call sites: wrench and bonus placement, hazard counts, the winner's-circle particles,
tune choice and prize animation.

## Proof table

| claim | script | count |
|---|---|---|
| the Python driver reproduces the ISR's PSG writes tick for tick, all 24 effect/tune entries | `engine/proof_sound.py` | 7200/7200 ticks (300 each) |
| four tunes at 1500 ticks | `engine/proof_sound.py` | 6000/6000 |
| engine noise `$12450` | `engine/proof_engine_snd.py` | 60/60 |
| RNG (values, new seeds, the seed == 0 path) | `engine/proof_rng.py` | 40/40, 40/40, both `$fccfe7a2` |

## Open

- Event names for triggers D, F, G, H, I and the ones not listed, and whether anything untested can start the dead effects.
- A Timer D source in the emulator would make the game audible and let the WAV renders be compared with a real run.
