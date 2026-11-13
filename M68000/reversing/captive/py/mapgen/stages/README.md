# `fed_MapGen` post-dig stage models

Evidence for `reversing/captive/mapgen.md`, "After the flow field". Run from `M68000/` with `uv run python -I
reversing/captive/py/mapgen/stages/<script>`. The repo root is found by walking up to `tools/rdis.py` (or
`M68000_ROOT`). Output goes to the gitignored `scratchpad/captive/mapgen_stages/`. The scripts need
`scratchpad/captive/mg_ret.snap`; `doorwatch.py natural` also needs `scratchpad/captive/base1/land_mg.snap`
(`py/ai/natural_base.repl`). Make the dumps first; the gates read them.

| script | what it proves | command | expected output |
|---|---|---|---|
| `dumpall.py` | the module and federation state at every stage boundary of `$23bb0`'s base path, through `gen.py`'s shortcut call | `dumpall.py 1 0 40` then `dumpall.py 0 0 40` | `0 39 39 stops`; 80 files `dumps/d<d2>_<d0>.bin` (a re-run is byte-identical) |
| `gate.py`, `models.py` | each ported stage reproduces the emulator's whole state after it, starting from the emulator's state before it | `gate.py 0 40` | 17 lines, each `exact 80/80 cases ... bytes differing 0` |
| (control) | the gates discriminate: one model constant changed | `gate.py 0 40 --stage 2533a --break 'prune_keep=(3,)'`; `--stage 2630c --break pic_mod=5` | `exact 16/80`; `exact 0/80`. Other controls: `25198 deadend_n=2`, `25162 shuffle_n=0x200`, `25240 patch_val=8`, `256f0 doorway=0x22`, `24d64 repl_xor=1`, `24128 mark16=0x17`, `240c2 thin=0x1f`, `26438 obj24=0x23`, `265cc obj25=0x27`, `26606 obj26=0x27`, `26854 lift_up_end=0x2d`, `26532 obj32=0x33`, `26570 obj30=0x2f` |
| `doorwatch.py` | the coded-door list `fed 2330(A6)` is written by the generator's door placer | `doorwatch.py natural scratchpad/captive/base1/land_mg.snap 3000000`; `doorwatch.py shortcut 0,0,2,0` | clear by `$23b8e`, then `$242f0` `$16`, `$242f2` `$15`, `$24300` `$80`; `list at end: 1615 0080 ...` |
| `doorlist.py` | every listed coded door is a door cell with a code below 24, and every kind-2 door is listed | `doorlist.py 0 40` | `357/357`; `{(21, 4): 40, (21, 2): 317}`; `317/317`; codes 0..23 each 7 to 25 times |
| `census.py` | bytes each stage changes, per grid | `census.py 1 0 40` | one line per stage |
| `common.py` | stage list, dump reader, memory helpers | - | - |
