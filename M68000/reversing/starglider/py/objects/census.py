"""Decode the live object pool of a snapshot: record table with type names, a per-type census and a top-down map PNG
(x right, z up, the world wraps at 65536; the player is the white cross).  Usage (from M68000/):
    python3 reversing/starglider/py/objects/census.py [snap] [out.png]
Prints one line per live record and the census; writes the map to $STARGLIDER_WORK/objects/map_<snap>.png."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import objlib as ol
from objlib import A6, Mem
from PIL import Image, ImageDraw
NAMES = {1: 'Walker', 2: 'Pyramid mine', 4: 'Energy Tower', 7: 'Starglider drone', 8: 'Armoured Transport Vehicle', 9: 'Egron Battle Tank',
         13: 'Bute fighter', 14: 'Diamond Proximity Mine', 15: 'Stomper', 16: 'Skim fighter', 20: 'Juno cannon', 21: 'Lotus Starfighter',
         23: 'Tri-launcher', 24: 'Egron Neutron Missile', 25: 'Egron Homing Missile', 26: 'Pyramid Launcher', 27: 'StarGlider One',
         3: '(unnamed: gun emplacement?)', 5: '(unnamed: static)', 6: '(unnamed: silo)', 11: '(unnamed: refuel hub)', 17: '(unnamed: static)',
         22: '(docking bay)', 12: '(unnamed missile)', 10: '(unnamed)', 18: '(unnamed)', 19: '(unnamed)'}
COL = {1: (255, 160, 0), 7: (255, 0, 0), 8: (255, 120, 120), 9: (200, 80, 0), 13: (255, 0, 255), 14: (255, 255, 0), 2: (255, 255, 0), 15: (255, 100, 0), 16: (0, 255, 255),
       20: (255, 60, 60), 21: (0, 255, 120), 23: (255, 120, 0), 26: (255, 0, 120), 27: (255, 255, 255), 4: (0, 120, 255), 11: (0, 255, 0), 6: (0, 200, 200), 3: (120, 120, 120),
       24: (255, 0, 0), 25: (255, 0, 0)}
def main():
    snap = next((a for a in sys.argv[1:] if a.endswith('.snap')), ol.sg.SNAP_GAME1)
    m = Mem(ol.sg.load_ram(snap)); n = m.rws(A6 + 472)
    px, pz = m.rw(A6 + 302), m.rw(A6 + 306)
    print(os.path.basename(snap), 'pool records', n, 'player x,y,z', px, m.rws(A6 + 304), pz, 'level', m.rws(A6 + 662))
    cen = {}
    img = Image.new('RGB', (520, 520), (0, 0, 0)); d = ImageDraw.Draw(img)
    for i in range(n):
        o = A6 + 4762 + 0x40 * i; t = m.rw(o)
        if not t: continue
        cen[t] = cen.get(t, 0) + 1
        x, y, z = m.rw(o + 4), m.rws(o + 6), m.rw(o + 8)
        print('%3d %05x type %2d %-28s x %5d y %6d z %5d head %4d spd %6d flags %02x live/active/view %d%d%d expl %02x hp %d' % (
            i, o, t, NAMES.get(t, '?'), x, y, z, m.rw(o + 12) & 0xfff, m.rws(o + 16), m.rb(o + 2), m.rb(o + 36) == 0, m.rb(o + 35) != 0, m.rb(o + 34) != 0, m.rb(o + 36), m.rws(o + 48)))
        sx = 10 + x * 500 // 65536; sy = 510 - z * 500 // 65536
        d.rectangle([sx - 2, sy - 2, sx + 2, sy + 2], fill=COL.get(t, (90, 90, 90)))
    sx = 10 + px * 500 // 65536; sy = 510 - pz * 500 // 65536
    d.line([sx - 6, sy, sx + 6, sy], fill=(255, 255, 255)); d.line([sx, sy - 6, sx, sy + 6], fill=(255, 255, 255))
    print('census:', ', '.join('%d %s x%d' % (t, NAMES.get(t, '?'), c) for t, c in sorted(cen.items())))
    out = next((a for a in sys.argv[1:] if a.endswith('.png')), ol.sg.work('objects', 'map_%s.png' % os.path.splitext(os.path.basename(snap))[0]))
    os.makedirs(os.path.dirname(out), exist_ok=True); img.save(out); print('map ->', out)
main()
