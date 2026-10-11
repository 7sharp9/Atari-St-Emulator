"""For each natural $5cde entry of the diff_5cde corpus (scratchpad/pm122/agents/herdop/corpus): the model's exit
(D2), the altitude byte $3f86c[4(L)] that $5d8c tests against $10, and 18(L).  Model only.  uv run python <this>"""
import re, sys
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(ROOT / "tools"))
import pm_fsm_ref as P
D = ROOT / "scratchpad/pm122/agents/herdop/corpus"
for log in sorted(D.glob("*.log")):
    txt = log.read_text()
    blocks = txt.split("--- breakpoint $00005cde hit")[1:]
    rams = sorted(D.glob(f"{log.stem}_*.ram"), key=lambda p: int(p.stem.split("_")[1]))
    for b, ram in zip(blocks, rams):
        regs = {k: int(v, 16) for k, v in re.findall(r"([DA][0-7]):([0-9a-f]{8})", b)}
        r = ram.read_bytes(); m = P.Mem(r); A0 = regs["A0"] & 0xffffff
        alt = r[(0x3f86c + P.s16(m.wu(A0 + 4))) & 0xfffff]; b18 = m.wu(A0 + 18)
        P.init_tables(r) if hasattr(P, "init_tables") else None
        d2 = P.call_5cde(P.Mem(bytearray(r)), A0, regs["D1"] & 0xffff, regs["A5"])[0]
        print(f"{ram.stem:10s} D2={d2:#04x} alt={alt} 18(L)={b18}")
