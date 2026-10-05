# Crude Buster: sound

One interrupt-driven HuC6280 program (bank 0, 4180 reachable instructions) drives 16 logical channels from a 16-entry command FIFO. The 68000 sends bytes through the latch at `$bc002`.
Channels 0-7: YM2151 voices (music only). 8-10: YM2203 FM voices 0-2 (effects only). 11-13: YM2203 SSG, never used by data (channel 11 only carries OKI1 triggers). 14-15: OKI2 drum streams (music only). OKI1 is triggered only by effects (opcode `$cc`).
Tools and logs: `snd/` (README there indexes every script); the logs the gates read are in `scratchpad/crudebuster/agents/snd/out/` (12 MB, symlinked as `snd/out`, regenerable with the runners). Every number below was reproduced from `snd/` after promotion where marked *(rerun)*.

## Proof table

| claim | count | script |
|---|---|---|
| the HuC6280 disassembler equals MAME's own dasm | 31,182 / 31,182 instructions (linear sweep, 8 banks); 4180 reachable: 4162 on MAME's chain, 18 more match from their own address; 0 mismatches | `snd/check_mame.py` with `lua/dasm_banks.lua`, `dasm_points.lua` |
| 68000 senders: raw scan of the 512 KiB image finds 94 `jsr $e1c` (81 `.l`, 13 `.w`), no bsr/bra/jmp/table reference | 94 sites *(rerun: 94, 90 immediate ids, 4 data-driven)* | `snd/scan68k.py`, `callers68k.py` |
| plays: 368 latch writes in 3 plays; 168 at static sites all matching the prediction, 191 at the four data-driven sites, 9 the direct `$13` write; 27 distinct ids, 16 of 94 sites reached | 0 unpredicted | `snd/check_play.py` |
| IRQ1 is the latch (`$e200` hits equal latch writes) | 25 = 25 (play), 1 = 1 (song run) | `lua/irqcount.lua`, `lua/sweep.lua` |
| IRQ2 (YM2151 timer B) about 499 Hz: 8.594 handler entries per frame; tempo accumulator `$e65a` runs once per IRQ2 and once per timer IRQ | 5171 = 5171+0, 10410 = 10323+87, 21680 = 21485+195 | `lua/irqcount.lua` |
| master volume `$80-$9f`: TL writes follow `min(127, TL + 127 - 4n)` | 192 writes, n = 0, 15, 31 | `snd/analyze_high.py` |
| tempo offset `$d0-$ff`: `$d0` predicted 221.5 frames observed 221; `$ff` 69.5 vs 70 | 2 ids | `snd/analyze_high.py` |
| note encoding to YM2151 KC/KF | 581 / 581 *(rerun)* | `snd/predict_kc.py` |
| OKI starts equal the table lookup (phrase and chip) | 542 / 542 *(rerun)*; 50 / 50 OKI1 effect ids statically *(rerun)* | `snd/check_oki.py`, `check_static_oki.py` |
| FM patch formats equal MAME's register writes | 67 / 67 YM2151 and 29 / 29 YM2203 *(rerun, 0 mismatches)*; static key-on counts 47 / 47 *(rerun)* | `snd/check_patch.py`, `check_patch2203.py`, `check_static_fm.py` |
| sequencer grammar: 4720 dispatches of 49 opcodes in 112 song traces, 0 operand-count contradictions; all 247 channel streams decode (177 end, 70 loop) | | `snd/analyze_trace.py ops`, `static_census.py` |
| effect-mode time unit 256/436 IRQ2 per duration unit | 9 effects within 0.8 frame | `snd/check_effect_time.py` |

## 68000 side

`$e1c` writes D7 (the latch keeps the low byte) to `$bc002` **if `$80054` bit 7 (demo sounds on, from the inverted DSW) or `$80040` bit 7 (game running) is set**. Attract mode never calls it in 3000 frames, so no sound is sent there with demo sounds off. The coin sound is `move.w #$13,$bc002` at `$11ee` (after the protection check) and bypasses the gate.
The 94 `jsr $e1c` sites are reached through the longword state tables, so recursive listings miss 67 of them: use the raw scan.
Data-driven ids: `$1502` level music from a word table indexed by `$80046` (in game `$1532` = 01 07 09 08 07 06, attract `$153e` = 06 07 09 08 07 06); `$a358` the pending sound id at byte 31 of a player record (observed 06 14 41 42 43 45 46 4f 5f; the source of 42/43 is not found); `$f950` byte table `$f964` indexed by 25(A5) (3f, 40); `$23478` word `$81e40` written at `$22576` (17, 2e). `$2494a` is a shared tail for ids `$64 $65 $67`.
Static ids by site (46 distinct) are in `snd/callers68k.tsv` (site, id, nearest handler-table address; that column is not proof of which object type owns the site) and per id in `snd/cmd_table.tsv` (kind, channels, sweep effect, OKI phrases, sites, plays).

## HuC6280 program

- Memory: reset vector at physical `$1ffe` = `$e000` (all MPRs 0 at reset); IRQ2 `$e16d` (YM2151), IRQ1 `$e200` (latch), timer `$e0e4`, NMI never. MPR0 = `$ff` (I/O page: timer `$0c00/$0c01`, IRQ mask/ack `$1402/$1403`; chip pages swapped in per access: `$80` YM2203, `$88` YM2151, `$90` OKI1, `$98` OKI2, `$a0` latch), MPR1 = `$f8` (RAM: zero page `$2000`, stack `$2100`), MPR2-4 = banks 1-3 (song and effect data, song table at `$4000`), MPR5/6 = banks 8/9 at idle and 4/5 inside handlers, MPR7 = bank 0 (driver). Bank 6 is the FM patch loader, bank 7 the patch images. Live check: idle MPR0-7 = ff f8 01 02 03 08 09 00 in 324 of 324 idle samples (`lua/mpr_idle.lua`).
- Init: `sei cld csh clx txs`, MPRs, `tai` zero-fill of RAM, YM2203 regs, YM2151 `$12=$f9` (timer B 2 ms), tempo T = `$78`, accumulator 1250, mask `$fc`, `cli`, `bra *` at `$e0e2`. Everything else is interrupt-driven.
- **IRQ1** calls `$e248`: a byte below `$80` goes into a 16-entry ring (`$2410`; when full the oldest is overwritten: read, not driven); `$80-$9f` sets the YM2151 master volume `$28`, `$a0-$bf` YM2203 `$29` (no observable effect: 8 TL writes identical with and without), `$c0-$c7` OKI2 `$2a`, `$c8-$cf` OKI1 `$2b`, `$d0-$ff` the tempo offset `$27` (T = base + signed `$27`). RAM cells checked exactly for 8 ids (`$80`->`$28=$7f`, `$9f`->`$03`, `$a0`->`$29=$ff`, `$bf`->`$83`, `$c0`->`$2a=$87`, `$c7`->`$80`, `$c8`->`$2b=$87`, `$cf`->`$80`; `lua/hv_ram.lua`).
- **IRQ2** is the 500 Hz tick: reset timer B, start the HuC timer and mask `$f9` so the timer and IRQ1 nest, add 436 to `$01/$02`, run the tempo accumulator (ticks per IRQ2 = T/1250; default 48 Hz) and the clock, `cli`, per-chip voice bookkeeping `$f726`, then `$e5be` (FIFO pop via `$e302`, then all 16 channels). The timer IRQ runs only while the handler runs and adds one more accumulator step (inferred to compensate overruns; the count identity is proven). A second engine (`$f855-$fd50`, gated by `$63`, never written) and a reply ring (no reply latch on this board) are dead: 0 hits in all runs.
- **Dispatch `$e302`**: id 0 restarts the program; `$01-$70` start the song or effect whose pointer is at `$4005+2n` (ids above the byte at `$4000` = `$70` are ignored: `$71-$7b` silent 300 frames each); `$7c-$7f` a service tone. A song header is `5D 5E 5F 16 17` plus 2 bytes per set channel bit (`5D` channels 0-7, `5E` channels 8-15, MSB first), `5F` bit 0 = music (tick-based) versus effect (raw time), `16/17` an override bitmap (a running slot is killed only if its song id is set there, otherwise the new command is dropped); 16 slots at `$2310-$2340`.

Classes from a 256-id sweep (clean state per id, 300 frames, 68000 muted):

| ids | class | count |
|---|---|---|
| `$00` | restart | 1 |
| `$01 $02 $12` | control songs (take over channels and END: silence) | 3 |
| `$03` | stop all music | 1 |
| `$10` | channel parameter reset | 1 |
| `$04-$09 $0a-$0f $11` | music (`$09` drums only, `$0c` YM2151-silent) | 13 |
| `$13-$3e` | YM2203 FM effects (ch10 uses CH3 special mode) | 44 |
| `$3f-$70` | OKI1 voice effects (stream `cc nn a8` through channel 11) | 50 |
| `$71-$7b` | ignored | 11 |
| `$7c-$7f` | service tone | 4 |
| `$80-$ff` | settings, no chip writes | 128 |

The level-1 theme is `$06` (8 channels in the sweep, plus the play log); no id is named from game text. Dynamic play confirms `$01` = silence and `$13` = coin.

## Sequencer data

72 handlers for stream bytes `$90-$d7` (table `$e97a`, full list `snd/ops.tsv`). **Music mode** (`$e6a5`): a byte below `$70` is a note length in ticks that persists; `$70-$8f` and `$e0-$ff` are notes (nibble `(b-$70)&15` or `(b-$c0)&15`; semitone p = nibble + 12*octave + transpose, octave starts at 4; KC = `((p/12 + F836[p%12]) << 4) | F827[p%12]`, `F827` = 0e 00 01 02 04 05 06 08 09 0a 0c 0d, `F836[0]` = -1); a note keys on at once and off after the gate (`$96`: max(1, length*n>>8) ticks). **Effect mode** (`$e925/$e952`): a byte below `$80` is a delay (256/436 IRQ2 per unit), `$80-$8f` sets a pitch, key on/off are the explicit `$a6/$a7`, `$a8` ends the channel.
Main opcodes: `$90` rest, `$91/$92/$93 n` octave, `$94 n` volume, `$95` legato, `$96 n` gate, `$98 lo hi` tempo base, `$99` jump, `$9a n/$9b` repeat, `$a8` end, `$d7 kf tr` fine tune and transpose, `$b6` portamento, `$b7/$b8` PMS/AMS, `$b9/$ba` PMD/AMD, `$bb/$bc` LFO, `$ca` pan, `$c0-$c9` levels, `$d5/$d6` attack and release, `$97 lo hi` inline YM2203 patch, `$d2 n` YM2151 patch, `$ad op lo hi` CH3 operator frequency, `$cc n` OKI1 start, `$cd/$ce` stop OKI. 22 opcodes never occur in any stream (their semantics are from handler bodies only). Music streams begin with a common 31-byte defaults preamble.
YM2151 patch (opcode `$d2`): a 4-byte record at bank 6 `$4600+4n`; image byte 0 = RL/FB/CON (ORed with `$c0` into reg `$20+ch`), then 4 operators x 7 bytes in slot order M1, C1, M2, C2 (DT1/MUL, TL, KS/AR, AMS/D1R, DT2/D2R, D1L/RR, 1 unused), 3 tail bytes only partly checked. YM2203 inline patch (`$97`): byte 0 = reg `$b0+ch`, 4 operators x 7 bytes in the order S1, S3, S2, S4; the AM/D1R and D2R rate fields are written minus 1 when non-zero (`$f63b`).
Chip writers: YM2203 address `$f4ff`/data `$f50e`, YM2151 `$f51d`/`$f52c` (busy waits), OKI1 `$f4eb`, OKI2 `$f4f5`, latch read `$f4d3`, key-off `$ec09`, key-on `$ec31`, volume `$ea49`.

## OKI

Phrase tables from the ROM headers (`snd/data/oki_phrases.tsv`, `oki_usage.tsv`): entry = start (24-bit), end (inclusive), 2 pad. OKI1 (`fu12-.16k`, 7627 Hz) 47 phrases, OKI2 (`fu13-.21e`, 15255 Hz) 62 phrases; the rest of the first 1024 bytes is sample data. Phrases 9 and 22 of OKI1 are 1-byte stubs that never show busy, so the retry loop `$f6c8` writes them 4 times (explains ids `$48`, `$55`). HuC6280 tables of 4-byte entries [phrase+1, attenuation, priority, voice mask]: A `$9e56` (OKI1, selected by `cc n`), B `$9f12` (OKI2, drum notes on channels 14/15), C `$a012` (identity map, only after opcode `$d0`, never run). Allocator `$f651` picks the voice with the highest priority number among the mask's voices; the new sound may replace a voice whose number is greater or equal; ties go to the oldest.

## Open

Event names for the ids (only call-site context is known; a play reaching more than 16 of 94 sites is needed); `$a358` values 42/43; the 22 never-run opcodes; the patch image tail and loader entry `$4200`; FIFO overflow and slot conflicts (read, not driven); music key-on counts are lower bounds (300-frame windows); attract music (sent only with demo sounds on, not seen).
