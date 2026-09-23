"""121st: pm118/dump_frame.py plus the later-land record fields (b15, b32,
w18, icons), the unmasked $57fed tick byte and the 16x16 $312a0 sheet.
    py -3 dump_frame.py <frame.ram> <out.json>   (input for score.fsx)"""
import base64, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import pm_render_ref as pr
from pm_export import Ram, render_icons
ram_path, out = Path(sys.argv[1]), Path(sys.argv[2])
R = pr.load_ram(ram_path); b = R["ram"]; rb = Ram(b)
TER, CTL = 0x438EE, 0x3F86C
xi = R["x_inset"]; ent = R["ent"]
b64 = lambda bs: base64.b64encode(bytes(bs)).decode()
def obj(o):
    a = o["addr"]
    d = {k: o[k] for k in ("addr", "b6", "b5", "b7", "b14", "b17", "b31", "fx", "fy", "group", "wcx", "wcy")}
    d.update(b15=b[a + 15], b32=b[a + 32], w18=(b[a + 18] << 8) | b[a + 19], icons=render_icons(rb, a), b33=b[a + 33], b44=b[a + 44])
    return d
doc = dict(
    cam=list(R["cam"]), yaw=R["yaw"], tick=R["tick"], x_inset=xi, phase_bias=R["phase_bias"],
    half=R["half"],
    corners=[[[R["corners"][(r, c)][0] - xi, R["corners"][(r, c)][1]]
              for c in range(2 * R["half"] + 1)] for r in range(2 * R["half"] + 1)],
    typ=b64(b[TER:TER + 8192]), hgt=b64(b[TER - 8257:TER - 8257 + 8192]),
    flg=b64(b[TER + 8257:TER + 8257 + 8192]), ctl=b64(b[CTL:CTL + 8192]),
    dith=b64(R["dith"]), ref=b64(R["ref"]),
    anim=ent["anim"], sel_group=ent["sel_group"], tile_off=ent["tile_off"],
    rot_phase=b[0x57FED],
    sheet33=b64(ent["sheet33"]), sheet_prop=b64(ent["sheet_prop"]),
    sheet_prop16=b64(b[0x312A0:0x312A0 + 47 * 160]),
    ram=b64(b),
    objs=[obj(o) for o in ent["objs"]],
)
out.write_text(json.dumps(doc))
print(f"{ram_path.name}: cam {R['cam']} yaw ${R['yaw']:02x} tick {R['tick']} objs {len(ent['objs'])}")
