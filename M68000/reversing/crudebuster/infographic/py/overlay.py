"""overlay.py <capNNNNN.ram> <capNNNNN.png> <out.png> [scale]: draw the game's own hit boxes over a MAME screenshot.

The .ram file is $80000-$83fff from player/lua/natbot.lua (CB_CAPTURE), the png is the screenshot of the same frame.
Boxes (R, L, B, T, y grows down; world to screen: x - $8040a, y - $80406):
  P1 body    record +64..70 (absolute), P1 attack +72..78 (absolute, drawn only while +28 is set)
  enemy body $6b000[type][state] + (x, y) of each live pool A record; red when the record's +6 bit 7 (a hit taken this frame) is set
  pool B     $68000[type][+3][+4][+20] is not drawn here (props are decoration for this figure)
The hit test of the game is overlap(X, Y) = R_Y >= L_X and L_Y < R_X and B_Y >= T_X and T_Y < B_X (player.md section 4)."""
import os, struct, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../player/py"))
from romlib import l, sw

def load(ram_path):
    ram = open(ram_path, "rb").read()
    W = lambda a: struct.unpack(">H", ram[a - 0x80000:a - 0x80000 + 2])[0]
    sx, sy = W(0x8040a), W(0x80406)
    P = ram[0x100:0x180]
    pl = dict(x=struct.unpack(">H", P[8:10])[0], y=struct.unpack(">H", P[12:14])[0], face=P[7], flag=P[28],
              atk=struct.unpack(">4h", P[72:80]), body=struct.unpack(">4H", P[64:72]), pose=P[24], hp=P[19])
    E = []
    for i in range(16):
        r = ram[0x1000 + i * 0x40:0x1000 + (i + 1) * 0x40]
        if not r[0] & 0x80: continue
        x, y = struct.unpack(">H", r[8:10])[0], struct.unpack(">H", r[12:14])[0]
        try:
            b = l(l(0x6b000 + 4 * r[2]) + 4 * r[3]); box = [sw(b + 2 * k) for k in range(4)]
        except Exception: continue
        R, L_, B, T = box[0] + x, box[1] + x, box[2] + y, box[3] + y
        E.append(dict(i=i, type=r[2], state=r[3], x=x, y=y, hp=r[5], hit=bool(r[6] & 0x80), box=(R, L_, B, T)))
    return sx, sy, pl, E

def overlap(a, b):  # a = enemy body, b = attack box, both (R, L, B, T)
    return b[0] >= a[1] and b[1] < a[0] and b[2] >= a[3] and b[3] < a[2]

def draw(ram_path, png_path, out_path, scale=4):
    sx, sy, pl, E = load(ram_path)
    im = Image.open(png_path).convert("RGB")
    im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    d = ImageDraw.Draw(im, "RGBA")
    def rect(box, col, fill=40, w=2):
        R, L_, B, T = box
        x0, x1 = (L_ - sx) * scale, (R - sx) * scale
        y0, y1 = (T - sy) * scale, (B - sy) * scale
        d.rectangle([x0, y0, x1, y1], outline=col + (255,), fill=col + (fill,), width=w)
    rect(pl["body"], (60, 220, 90))
    hits = []
    for e in E:
        hit = pl["flag"] and overlap(e["box"], pl["atk"])
        hits.append(hit)
        rect(e["box"], (255, 80, 60) if hit or e["hit"] else (60, 190, 255))
    if pl["flag"]: rect(pl["atk"], (255, 210, 40), fill=70, w=3)
    im.save(out_path)
    return dict(sx=sx, sy=sy, player=pl, enemies=E, predicted_hits=hits)

if __name__ == "__main__":
    info = draw(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 4)
    print("player", info["player"]["x"], info["player"]["y"], "atk flag", info["player"]["flag"], "atk", info["player"]["atk"])
    for e, h in zip(info["enemies"], info["predicted_hits"]):
        print("enemy type %d state %d box %s hit-flag %s predicted %s" % (e["type"], e["state"], e["box"], e["hit"], h))
