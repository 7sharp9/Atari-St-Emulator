"""Decode the shared per-type tables of the pool A fighter engine from the ROM (all indexed by pool A type 0..$4f).
  damage: WRONG AS A PER-TYPE TABLE. `$fc34` indexes the byte tables (pointer table $fcba, index (dip $80054 & $c)/4) by the pool C hit-box type (+2 of the box record = D6 of the `$21e72` call),
     not by the owner's pool A type; damage = byte * 4 health points. The columns printed here are only meaningful as the byte at index = pool C box type: see grunts/py/dmg.py and special34/py/boxdmg.py.
     Default dip is $80054 = $80, so column "dip 0" applies.
  hit reaction code (`$fdba`, written to player +23)
  score (`$248bc`; paid on every landed hit, not only on the kill; rows for types >= $4f read past the table end): 4 bytes per type at $24952 : [state1 hit idx][state5 idx][state2/4 (death) idx][sound: 0 random 100/101/103, $ff none]; idx -> BCD long at $4016 + 4*(idx-1)
usage: tables_decode.py [type hex ...]"""
import os, sys
root = os.environ.get("M68000_ROOT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
rom = open(os.path.join(root, "scratchpad/crudebuster/rom/cbuster_main.bin"), "rb").read()
def l(a): return int.from_bytes(rom[a:a+4], "big")
ptrs = [l(0xfcba + 4 * i) for i in range(4)]
def score(idx): return None if idx == 0 else rom[0x4016 + 4 * (idx - 1):0x4016 + 4 * idx].hex()
def info(t):
    dmg = [rom[p + t] for p in ptrs]  # dip 0,4,8,12 -> pointer order as stored: ptrs[i] is for (dip&c)=4*i
    sc = rom[0x24952 + 4 * t:0x24952 + 4 * t + 4]
    return dict(type=t, dmg_by_dip=dmg, react=rom[0xfdba + t], score_idx=list(sc[:3]), score_bcd=[score(i) for i in sc[:3]], snd=sc[3])
if __name__ == "__main__":
    ts = [int(a, 16) for a in sys.argv[1:]] or range(80)
    print("type dmg(dip0,4,8,12)*4  react  score idx (hit,state5,death)  bcd  sound")
    for t in ts:
        d = info(t); print(f"{t:02x} {d['dmg_by_dip']} {d['react']:02x} {d['score_idx']} {d['score_bcd']} {d['snd']:02x}")
