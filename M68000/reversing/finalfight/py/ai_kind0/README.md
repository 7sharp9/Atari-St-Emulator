# ai_kind0: kind-0 fighter AI (BRED, DUG, JAKE, SIMONS) checks

Scripts behind `reversing/finalfight/ai.md`, section "Shared helpers and kind 0". Everything runs on the saved state
`scratchpad/finalfight/ff_enemies.sta` (loaded with `FF_LOAD`; `run_ai.sh` copies it into the MAME run directory when missing).
Python needs no numpy (system `python3`). The repo root comes from `__file__`; the MAME run directory is `$FF_RUN` (default
`scratchpad/finalfight/p3/a/run`; give each concurrent run its own) and dumps go to `$AI_OUT` (default `scratchpad/finalfight/p3/a/out`,
about 100 MB for the four dumps and test runs, regenerable). `run_ai.sh` is the only place `mame` is started; it exports
`SDL_VIDEODRIVER=dummy`.

| file | what it does / proves | how to run |
|---|---|---|
| `run_ai.sh` | wrapper: `rec` (per-frame dump), `cold` (cold-boot drive then dump), `hit` (breakpoint execution counts), `poke` (hit-type poke on one record) | `FF_GOD=1 ./run_ai.sh rec g1 ff_enemies 6150 ""` |
| `poolrec.lua` | per frame: `$ff8000-$ff87ff`, both player records, the 13 pool-2 records, `$ff1100-$ff11ff`, the 16 prop records. Options: `FF_KEYS="right:a-b,b1:a-b"`, `FF_GOD=1` (refill Cody's hp when below `$50`), `FF_POKE="frame:addr:size:value,..."`, `FF_COPY="frame:src:dst:len"`, `FF_WTAP="lo-hi,..."` (write tap log), `FF_SHOT_WIN` | via `run_ai.sh rec/cold/poke` |
| `hitc.lua` | counts executions of listed addresses under god mode and keys; `FF_LOG=1` logs D0, D1, A6 and the word `$ff1150` at each hit | `./run_ai.sh hit c1 ff_enemies 6150 "22d8e,22da0,22dae"` |
| `rec.py` | loader for the `poolrec.lua` dump (`Frame.p2[i]`, `.pl`, `.a(off,n)`, `.l(addr,n)`, `.props`) | imported |
| `mkkeys.py` | deterministic pseudo-random Cody input plan for `FF_KEYS` | `python3 mkkeys.py 4160 6200 <seed>` |
| `rdl.py` | recursive-descent lister with word jump tables expanded, labels, data gaps; the kind-0 listing is `python3 rdl.py 21cec 2813a 21cec 22ff6 22e4c 22e62 22eba 22ed0 23020 22e36 22456` (the extra roots are targets of `jmp (A1)` tables); `OVR` fixes tables whose length the first word does not give | see left |
| `anims.py` | decodes the 17 animation thunks (`lea 6(PC),A1 / jmp $3b10`) for the four characters: frames, durations, flag byte, hurt/attack box index, and the attack box record (dx, dy, hw, hh, `+8` row, `+11` hit type) | `python3 anims.py` |
| `counters.py` | `$ff1154` equals in-use kind 0/1/2 records (8450/8450); `$ff115a` equals kind 0/2 records with `+136` set (8450/8450); `1(A6)` equals the `$3264` window test (21364/21372, the rest are spawn frames); `44/45(A6)` equal the frame record `+4/+5` (20789/20789); `166(A5)` +1 per frame; `168(A5)` steps | `python3 counters.py g1.bin f1.bin ...` |
| `dmgcheck.py` | damage Cody takes from a single kind-0 attacker equals `byte[char data + $60 + box +8 + v]` (59/59, 14 (char, box, v) cases) | same |
| `slotcheck.py` | state 16 fighters sit within the `$27d30` tolerance of their slot (2855/2857) | same |
| `rngcheck.py` | `$3c26` is the LFSR `S' = (S>>1) \| ((bit1^bit9)<<15)` on `$ff1150` (505/505, D0 = low byte 506/506); needs the `hit` log of `3c56` | `FF_LOG=1 ./run_ai.sh hit r1 ff_enemies 6150 "3c56" ""; python3 rngcheck.py $AI_OUT/r1_log.txt` |
| `hist.py`, `trans.py`, `hits.py` | state histograms and transition counts of kind 0 ((2,3) and 4(A6) in state 12); hit entries by `63(A6)` | `python3 hist.py g1.bin f1.bin ...` |
| `animstate.py` | which animation thunk plays in each state (pointer `32(A6)` against the thunk headers) | same |
| `tl.py`, `hitreact.py` | timelines of one record; `hitreact.py` prints run-lengths of `(2,3,4)` for a poked hit | `./run_ai.sh poke h3 11 3 8; python3 hitreact.py $AI_OUT/h3.bin 11 4200 4420` |
| `st28.py` | state 28: the fighter smashes the prop in `102(A6)` (prop hp 0 to -1 on the frame the attack box appears; 2/2 episodes) | `python3 st28.py f2.bin f3.bin` |
| `gates.sh` | fresh `g1`, `f1`..`f3`, `r1` runs, then every check above | `./gates.sh` (`./gates.sh check` reuses the dumps in `$AI_OUT`) |

Experiments by `FF_POKE` (frame, address and value in hex): hit type poke `./run_ai.sh poke <name> <idx> <63 type> <hp>` (pool-2 array
index 11 is DUG in `ff_enemies`, 10 JAKE, 12 BRED); stage clear `FF_POKE="4200:ff812b:1:1"`; P2 clone `FF_COPY="4200:ff8568:ff8628:192"`;
entrance type on a fresh record `FF_POKE="6255:<record+21>:1:<type>"` with the `f1` key plan. Determinism: `f1` run twice gives md5
`244f2c10...`.
