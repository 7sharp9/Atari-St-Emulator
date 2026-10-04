# Black Tiger sound scripts

Run from anywhere with the M68000 venv (`source M68000/.venv/bin/activate`); the repo root is found from
`__file__` (`M68000_ROOT` overrides), inputs come from `$BT_WORK` (default `M68000/scratchpad/black_tiger`),
outputs go to `$BT_WORK/agents/sound/` (`run/` holds the REPL scripts and raw logs, `wav/` the renders). All
emulator runs use the existing `bin/Debug/net8.0/M68000.dll` with `ATARI_NOTRACE=1` (set by `verify_psg.run_repl`);
nothing builds. The doc is `../../sound.md`.

| script | what it proves | expected output | runtime |
|---|---|---|---|
| `btsnd.py` | decoder: tables (`tables`), WAV renders (`wav`), predicted PSG triples (`regs <id>`); library for the rest | `wav/snd0..8.wav`, `snd0_as_played_t0_overwrite.wav` | 2 s |
| `verify_psg.py` | gate 1: for each BTSND id, poke `w 17848 <id>`, log `watch ff8800 8`, compare with the predicted (R8,R9,R10) per tick | `TOTAL 23813/23813` | 25 s |
| `verify_natural.py <snap> <steps> --tag t` | gate 2: unpoked run, every logged tick explained by a stream (`tl/t23.snap 20000000`) | `explained 52887 / 52887 ticks (0 unexplained)` | 1 min (`--reuse` re-analyses `run/<tag>.out`) |
| `tally_requests.py <snap> <steps>` | writers of the pending-sound cell `$17848` and ids (`tl/t25.snap 10000000`) | 61 requests, 23 handed to `$105e8`; ids 7,3,1,4,9 | 10 s |
| `events_drive.py` | per level (0..7) and per map-object kind: poke the hero onto the first record, which writer requests which id | `events_by_kind.tsv`, sections 6.2 | 35 s |
| `events_probe.py` | kinds `$03..$21` forced into item record 0 of `play_start.snap` | `events_probe.tsv`: 3-9 -> 7, `$e` -> 6, `$f` -> 6, `$10` -> 5, `$1d` -> 5, `$1e` -> 8 | 20 s |
| `events_boss.py` | hero onto the level-exit object, fire held, 2M steps: the requests during each boss arena | `events_boss.tsv`: only ids 4, 9 (and 8 on level index 6) | 10 s |
| `events_shop.py` | `callcap fa9c` for the 10 shop items, money 20000 and 0 | `affordable purchases that requested id 7: 10/10; refused: 0/10` | 5 s |
| `events_misc.py` | urn burst -> 1 (with control and `hits $d5e4` 1/0), time over -> 2, hero damage -> 3 (242 steps after `$1eeb2 <- $14`), chest seeds -> 8 (5/12, equal to the `$d3cc` branch set) | five result lines | 40 s |
| `wav_check.py` | numeric check of the WAVs: length = ticks, rate, no clipping, DC < 1 LSB, ids 1..8 equal to a render of the live captured triples | `ALL OK` | 2 s |
| `sound_sheet.py` | renders `sound_sheet.png` (volume curve and the ten waveforms) | `img/sound/sound_sheet.png` | 2 s |

Rendering uses Hatari's measured three-voice DAC table when it can find `src/includes/ym2149_fixed_vol.h`
(`$HATARI_YM_TABLE`, or `$HATARI_SRC`, default `~/GitHub/hatari`); without it a summed fallback model (INFERRED) is used.
The PSG-write gates do not depend on the level table.
