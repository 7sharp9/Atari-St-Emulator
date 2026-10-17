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
  and 2 are fixed to B and C); 3-5 set the period; 6 wait (9 ticks per step; a wait of `w` holds `w+1` steps, so a script lasts the sum of its wait arguments plus one step per wait); 7 and above end. Every set-period op also restarts the voice's envelope, so a stream of period ops is a stream of retriggered hits.
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
  `$1330e` again, so **channel C's envelope advances twice per step**. The Python model needs this to match: without it the live
  comparison fails (Q 15499/15560, J 1080/1187 ticks). Audible effect (`residual/bugfx.py`): only the channel-C volume differs, C attacks
  and decays at double speed (the write samples every second state), flat sustains keep their level and decaying tails end about twice as
  early. Single-voice effects (A-I, M, O) are unaffected; three-voice ones change (J 107 of 125 C writes, K 74/85, L 84/95, N 68/216,
  P tunes 211-1016 of 830-1117, R 612/1006, S 508/644; tune 906 only 60 of 1722, at most 3 of 15 volume steps).

## Effects and tunes

Durations are sequencer steps x 37.54 ms including the extra step per wait (`residual/durations.py`). Events are inferred from the call context except where marked *live*.

| trigger | script offset | length | caller | event |
|---|---|---|---|---|
| A `$12522` | 0 | 1.35 s | `$b3fc` (only when `-1896 == 0`) | respawn / helicopter start |
| B `$125e6` | 316 | silence | `$b5f8` | stops A |
| C `$126ae` | 28 | 2.7 s | `$ae0e` | rising four-note arpeggio |
| D `$1271c` | 166 | 3.4 s | `$ea32` | not identified |
| E `$1278a` | 88 | 4.8 s | `$abd4` | bonus pickup (*live*: three hits in 12M race steps alongside the wrench/score draws) |
| F `$127f8` / G `$12866` | 180 / 302 | 1.7 / 1.8 s | via `$a608` / `$a62c` | not identified |
| H `$128e0`, I `$1294e` | 14, 74 | 0.1 s | `$d4fa`, `$df18` | blips |
| K `$12a56` | 242 | 3 s, three voices | `$be40`, `$caa8` | "GO" beep (*live*: once at countdown end) |
| L `$12a8c` | 272 | 3.4 s | `$199de` | shop / prepare screen |
| N `$12b00` | 336 | 8.75 s | `$186ce` | title engine rev |
| O `$12b32`, T `$12e30` | 236, 316 | silence | startup; race start and end (T *live*: three hits at race start) | channel kills |
| S `$12dec` | 2580 | 24.0 s | `$18024` | ready-screen tune |
| R `$12da8` | 7780 | 37.6 s | `$19164`, `$199de` | prepare / shop tune |
| P `$12c10(Random(5) % 5)` | 3398 / 4488 / 5302 / 5916 / 6794 | 31-42 s | `$1a4ca` | five winner's-circle jingles |

**Unreferenced.** `$129bc` (scripts 194/208/222), `$12ac2` (script 322) and `$12d64` (script 906) have no caller: no longword or
word reference to them in the relocated image (TEXT and DATA), no `bsr/jsr/lea/pea` and no thunk onto them. The 25 script offsets the
starters add to `-54(A4)` tile the script area exactly (8214 bytes, then a duplicate terminator and 1786 zero bytes), so there is no
hidden stream. Instruments 10-12 are used only by J, 13/14/18 only by Q, 21 only by M; 17, 26, 27, 28 by no script; 32-34 are empty
and 0 and 15 are silencers. All three decode with the proved driver (`residual/tune.py`, notes and register logs in `residual/data/`);
the live ISR agrees tick for tick over the whole length (Q 15559/15559 ISR ticks, J 1187/1187, M 125/125).

- **Q (906)**: **64.49 s** (1718 steps; 59.46 s is only the sum of the 134 wait arguments), the longest in the game. Three tone-only
  voices (A inst 13, B inst 14, C inst 18) play a 278-step cycle `E2 x10, B1, A1 x10, D2` (periods 1510, 2016, 2262, 1695; 82.8, 62.0,
  55.3, 73.7 Hz) 6.18 times as retriggered bass hits; instruments 13 and 14 have different vibrato intervals (22 and 27 ticks), so the
  voices beat. It ends with the silence instrument on all three. Its starter does not test the sound flag.
- **J**: a 4.54 s drone, A 69.4 Hz, B 138.1 Hz, C 69.1 Hz (insts 10-12, detuned vibrato), then silence.
- **M**: a 0.11 s 625 Hz blip on channel B (inst 21).

It is unused content, not a hidden mode (`secrets.md`).

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
| the three unreferenced entries over their whole length, with and without the `$13308` fall-through | `residual/liveproof.py` | Q 15559/15560 (the miss is a later non-ISR write) vs 15499; J 1187/1187 vs 1080; M 125/125 |
| engine noise `$12450` | `engine/proof_engine_snd.py` | 60/60 |
| RNG (values, new seeds, the seed == 0 path) | `engine/proof_rng.py` | 40/40, 40/40, both `$fccfe7a2` |

## Open

- Event names for triggers D, F, G, H, I and the ones not listed.
- A Timer D source in the emulator would make the game audible and let the WAV renders (`residual/tune.py`) be compared with a real run.
