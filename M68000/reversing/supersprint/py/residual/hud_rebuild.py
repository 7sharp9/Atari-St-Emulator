"""Rebuild the whole HUD band (screen rows 0..29) of a live race snapshot from first principles and compare with the live stash/screen:
tile-map crowd (engine/proof_playfield.build) + caption strips ($144ca) + wrench-count icons ($1453a) + lap-panel strips (lap.py = $158ea)
+ big lap digit (engine/hud.py = $15e5a), using only the snapshot's per-car state (-3914, -3954, -3906, -4822, -4870(A4)) and SUPER.DAT.
usage: hud_rebuild.py [snap]"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rcommon import *
os.environ['ENGINE_OUT'] = os.path.join(AGENT, 'engine_out')
import proof_playfield as PF
from common import *
import hud, lap
from PIL import Image

snap = sys.argv[1] if len(sys.argv) > 1 else sscfg.SNAP_RACE
dat = open(os.path.join(sscfg.FILES, 'SUPER.DAT'), 'rb').read()
b5 = bytes(dat[132566:132566 + 30000]); b7 = dat[165566:165566 + 3520]
img = open(os.path.join(sscfg.WORK, 'ss.img'), 'rb').read()
PANEL_OFF = struct.unpack_from('>3H', img, 0x14530 - 0xA304)       # caption strip offsets, $144ca
ICON_OFF = struct.unpack_from('>4H', img, 0x145DE - 0xA304)        # wrench-count icon offsets, $1453a


def rebuild(R, track=0, verbose=True, blank=None):
    """R = Ram of a race snapshot. returns (bytearray 32000: rebuilt screen with the HUD, info dict)"""
    g = R.g; gs = R.gsw
    PF.r = R                                                         # PF.build reads the tree tables from the module-level snapshot
    bg = bytearray(PF.build(track))                                  # crowd, trees, shadows (the 'background')
    S = bytearray(bg)
    drone = [R.sw(A4 - 3914 + 2 * c) for c in range(4)]; wr = [R.sw(A4 - 3954 + 2 * c) for c in range(4)]
    # --- $144ca captions: panel 0..2, frame panel (+3 for a drone) ---
    for panel in range(3):
        fr = panel + (3 if drone[panel] else 0)
        for r in range(6):
            for gx in range(7):
                o = PANEL_OFF[panel] + r * 160 + gx * 8
                w0, w1, w2, w3 = struct.unpack_from('>4H', b5, 0x6720 + fr * 336 + r * 56 + gx * 8)
                opaque = (w0 | w1 | w2 | (~w3 & 0xFFFF)) & 0xFFFF
                w3 &= opaque; keep = ~opaque & 0xFFFF
                for p, v in enumerate((w0, w1, w2, w3)):
                    cur = (S[o + 2 * p] << 8) | S[o + 2 * p + 1]
                    cur = (cur & keep) | v
                    S[o + 2 * p] = cur >> 8; S[o + 2 * p + 1] = cur & 255
    # --- $1453a icons (human cars): the bg strip -4944(A4) is the screen's top rows as they were before the icon (captions included) ---
    bgstrip = bytes(S)
    for car in range(3):
        if drone[car]: continue
        ic = min(wr[car], 9)
        for r in range(6):
            o = ICON_OFF[car] + r * 160
            w0, w1, w2, w3 = struct.unpack_from('>4H', b5, 0x6F00 + ic * 48 + r * 8)
            opaque = (w0 | w1 | w2 | (~w3 & 0xFFFF)) & 0xFFFF
            w3 &= opaque; keep = ~opaque & 0xFFFF
            bgw = struct.unpack_from('>4H', bgstrip, o)
            for p, v in enumerate((w0, w1, w2, w3)):
                struct.pack_into('>H', S, o + 2 * p, (bgw[p] & keep) | v)
    # --- panels: pristine bg = crowd rows 7..17 (the -4940(A4) buffer), digits from the latched state ---
    pbuf = bytes(bg[0x460:0x460 + 0x6E0 + 16])
    blank44 = bytes(R.b[A4 - 4988:A4 - 4988 + 44]); blank88 = bytes(R.b[A4 - 5076:A4 - 5076 + 88])
    state = bytes(R.b[A4 - 4870:A4 - 4852])
    if blank is None:
        import blink; blank = blink.predict(R, 0)
    layer = bytearray(0x4200); stash2 = bytearray(S)
    for car in range(3):
        if blank[car]: continue                                      # the leader's panel blinks: $13bbe/$13c50 restore it to the crowd
        lap.draw(S, stash2, layer, pbuf, b7, blank44, blank88, state, car)
        digit = R.sw(A4 - 4822 + 2 * car)
        hud.draw_digit(S, stash2, layer[0x3E80:], pbuf, hud.digit_rows(b7, digit), car)
    return S, dict(blank=blank, drone=drone, wrench=wr, state=state.hex(), digits=[R.sw(A4 - 4822 + 2 * c) for c in range(3)], lapcur=[R.sw(A4 - 3906 + 2 * c) for c in range(3)])


if __name__ == '__main__':
    R = Ram(snap)
    import re
    mt = re.search(r'(?:race_t?|pre_)(\d)\.snap$', snap); track = int(sys.argv[2]) if len(sys.argv) > 2 else (int(mt.group(1)) if mt else 0)
    S, info = rebuild(R, track)
    print(info)
    stash = bytes(R.b[R.g(-86):R.g(-86) + 32000]); draw = bytes(R.b[R.g(-78):R.g(-78) + 32000]); shown = bytes(R.b[R.g(-82):R.g(-82) + 32000])
    regs = load_video_regs(snap); pal = [st_rgb(w) for w in regs['palette_words']]
    a = decode_st_screen(bytes(S), pal); b = decode_st_screen(stash, pal); pa, pb = a.load(), b.load()
    bad = [(x, y) for y in range(30) for x in range(320) if pa[x, y] != pb[x, y]]
    print('HUD band rows 0..29: %d / 9600 pixels equal; %d bytes equal of %d' % (9600 - len(bad), sum(1 for i in range(30 * 160) if S[i] == stash[i]), 30 * 160))
    print('differing pixels', len(bad), bad[:30])
    Image.new('RGB', (1, 1))
    diff = Image.new('RGB', (320, 30)); dp = diff.load()
    for y in range(30):
        for x in range(320): dp[x, y] = (255, 0, 0) if pa[x, y] != pb[x, y] else (0, 0, 0)
    W = Image.new('RGB', (960, 3 * 90))
    for i, im in enumerate((a.crop((0, 0, 320, 30)), b.crop((0, 0, 320, 30)), diff)): W.paste(im.resize((960, 90), Image.NEAREST), (0, 90 * i))
    W.save(os.path.join(AGENT, 'out', 'hud_rebuild_%s.png' % os.path.basename(snap).replace('.snap', '')))
