Crude Buster sound architecture (agent SND). Everything here derives the repo root from __file__ (or $M68000_ROOT); run from this directory.
MAME runs use their own run dirs (run_<name>/), never the shared one. Python: M68000/.venv/bin/python for h6280dis.py (needs nothing but the stdlib), python3 works for the rest.

Static tools
  h6280dis.py        HuC6280 disassembler. Opcode table parsed from MAME's 6280dasm.cpp. `rd --out rd.txt` = recursive descent from reset, IRQ2, IRQ1, timer
                     vectors (vectors at physical $1ff6-$1fff, MPRs all 0 at reset) with MPR tracking through `lda/tam`, plus the 72 sequencer handlers of the
                     table at $E97A. `linear <phys> <n>` = linear listing.   rd.txt = the listing (4180 instructions, gaps marked)
  show.py            show.py <lo> <hi> : rd.txt lines for a physical address range
  check_mame.py      compares h6280dis.py with MAME's own dasm (lua/dasm_banks.lua, lua/dasm_points.lua): 31182/31182 linear, 4180/4180 reachable
  scan68k.py         raw scan of the whole 68000 image for bsr/bra/jsr/jmp to an address (default $e1c)
  callers68k.py      every `jsr $e1c` (94 sites) with the D7 id by backward synchronisation + shared-tail branch sources -> callers68k.tsv
  d68.sh             68000 linear listing wrapper
  songs.py           static song table: header at logical $4000 (bank 1), song header ($5D $5E $5F $16 $17 + channel pointers), channel bit order MSB first
  static_streams.py  effect-mode (raw time) stream decoder, OPLEN = operand byte counts per opcode
  static_census.py   decodes all 247 channel streams (music and effect grammar) and lists the opcodes that never occur
  oki_phrases.py     OKI phrase tables of fu12-.16k (47 entries) and fu13-.21e (62 entries) -> data/oki_phrases.tsv
  oki_usage.py       phrase -> HuC6280 table entries -> latch ids (from the sweep) -> data/oki_usage.tsv
  build_ops.py       ops.tsv (72 sequencer opcodes: handler, name, operands, observed counts, registers written)
  build_table.py     cmd_table.tsv (per latch id: kind, channels, sweep effect, OKI phrases, 68000 sites, plays)

MAME drivers (lua/)
  snd_lib.lua        taps: 68000 writes to $bc002 (with caller return address), HuC6280 writes to YM2203/YM2151/OKI1/OKI2, latch reads; YM2151 reg $14 writes
                     are counted per frame (IRQ2 handler runs) instead of logged
  sweep.lua          msweep.sh <name> LO= HI= WIN= PRE= : load a quiet state, write one latch value from Lua, log WIN frames (decimal LO/HI, hex PRE)
  run.lua            mrun.sh <name> CB_PLAN= CMDS= MUTE= CB_STOP= : plan-driven play with the same log (LAT/LRD/EV lines)
  plans_auto.lua     deterministic pseudo-random autoplay plan (AUTO_N, AUTO_SEED)
  rtrace.lua         mlua.sh rtrace.lua <name> CMDS= CB_STOP= : ordered trace of sequencer stream reads (F/G), opcode dispatch (D), OKI table reads (O) and chip
                     writes (E) through a read tap on the sound ROM
  irqcount.lua       mscript.sh irqcount.lua <name> PTS="addr ..." : entry-point counters with debugger breakpoints (<= 10 points: debugger temp0-temp9)
  hv_ram.lua         reads the sound-RAM variables $27/$28/$29/$2a/$2b/$06-$09 after each latch value >= $80
  dasm_banks.lua, dasm_points.lua   MAME disassembly of every 8 KiB bank / of single points
Runners: msweep.sh mrun.sh mlua.sh mscript.sh trace_all.sh (112 song traces, 4 parallel) run_high.sh (latch >= $80 experiments)

Analysis / proofs
  analyze_sweep.py   per-latch-id effect summary of a sweep log            out/sw_all.log -> out/sw_all.tsv
  analyze_trace.py   ops | chans | opregs over rtrace logs
  analyze_high.py    effect of the volume/tempo ids on a following song (run_high.sh logs)
  predict_kc.py      note encoding: predicted YM2151 KC/KF vs MAME           581/581
  predict_time.py    tick model T/1250 per IRQ2 vs key-on times of music
  check_oki.py       OKI table lookup -> phrase and chip vs the chip's first byte    542/542
  check_static_oki.py static stream + table A/B -> phrase sequence vs MAME           50/50 effect ids
  check_static_fm.py  static key-on count per YM2203 FM channel vs MAME              47/47
  check_patch.py     YM2151 patch loader image layout vs MAME writes                 67/67
  check_patch2203.py YM2203 inline patch layout vs MAME writes                       29/29
  check_effect_time.py effect-mode time unit 256/436 IRQ2 per duration unit          9 effects within 0.8 frame
  check_play.py      68000 latch writes in plays vs the static site table            368 writes, 0 unpredicted

Data: callers68k.tsv cmd_table.tsv ops.tsv rd.txt rdis68k.txt roots68k.txt data/oki_phrases.tsv data/oki_usage.tsv data/fu12-.16k data/fu13-.21e (from the zip)
Logs (out/): sw_all.log (256-id sweep), rt_<id>.log (112 traces), play1b/auto1/auto2.log (68000 plays), hv_/ht_/hf_/ho_ logs, irq_*.log, hv_ram.log
run_*/ directories are MAME cfg/nvram dirs of single runs (deletable).
