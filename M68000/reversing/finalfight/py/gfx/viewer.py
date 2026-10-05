"""viewer.py: the viewer set, at most 20 PNGs of at most about 400 KB each, copied (and palette-quantized to 256 colours when
a file is larger) into scratchpad/finalfight/gfx/out/viewer/ together with proof_side_by_side.png (MAME screenshot, this
decode, difference mask for one frame pair).  Run after sheets.py, chars.py, render_pristine.py, layers_full.py."""
import os, shutil
import numpy as np
from PIL import Image
from cpsgfx import *
import prove

V = os.path.join(OUT, "viewer")
os.makedirs(V, exist_ok=True)
LIM = 400 * 1024
SET = [
    ("sheets/sprites_0.png", "01_sprite_rom_0000-087f.png"),
    ("sheets/scroll2.png", "02_scroll2_tile_rom.png"),
    ("sheets/scroll3.png", "03_scroll3_tile_rom.png"),
    ("sheets/scroll1_left.png", "04_scroll1_tile_rom_left_half_set.png"),
    ("chars/Cody.png", "05_cody_animations.png"),
    ("chars/Guy.png", "06_guy_animations.png"),
    ("chars/Haggar.png", "07_haggar_animations.png"),
    ("chars/fighter_k0_BRED.png", "08_bred_animations.png"),
    ("chars/other_boss_0_DAMND.png", "09_damnd_animations.png"),
    ("chars/other_boss_1_SODOM.png", "10_sodom_animations.png"),
    ("chars/other_item_(pickup)_handler.png", "11_items.png"),
    ("chars/other_weapon_kind_0.png", "12_weapon_kind_0.png"),
    ("pristine/png/stage0_scroll2_y0000.png", "13_stage0_scroll2_pristine.png"),
    ("pristine/png/stage0_scroll3_y0000.png", "14_stage0_scroll3_pristine.png"),
    ("pristine/png/stage2_scroll2_y0000.png", "15_stage2_scroll2_pristine.png"),
    ("pristine/png/stage3_scroll2_y0000.png", "16_stage3_scroll2_pristine.png"),
    ("layers/stage1_c_s1a1_screen.png", "17_stage1_screen_composite.png"),
    ("layers/stage0_st_chkA_1_scroll2.png", "18_stage0_scroll2_whole_map_dump.png"),
]


def put(src, name):
    im = Image.open(os.path.join(OUT, src)).convert("RGB")
    dst = os.path.join(V, name)
    im.save(dst, optimize=True)
    if os.path.getsize(dst) > LIM:
        q = im.quantize(256, method=Image.MEDIANCUT, dither=Image.NONE)
        q.save(dst, optimize=True)
    return os.path.getsize(dst)


def proof():
    g, r, pens, shot = prove.ld("en", 2)
    gp, rp, _, _ = prove.ld("en", 1)
    ob = cps_base(rp.a[A_OBJ], 0x800)
    gm = g.copy(); gm[ob // 2:ob // 2 + 0x400] = gp[ob // 2:ob // 2 + 0x400]
    img, _ = compose(prove.G, gm, r, obj_base=ob)
    diff = (img != shot).any(axis=2)
    d = np.zeros_like(shot); d[diff] = (255, 0, 0)
    both = np.concatenate([shot, img, d], axis=1)
    im = Image.fromarray(both).resize((both.shape[1] * 2 // 1, both.shape[0] * 2), Image.NEAREST)
    dst = os.path.join(V, "00_proof_mame_vs_decode_diff.png")
    im.save(dst, optimize=True)
    return os.path.getsize(dst), int(diff.sum())


def main():
    print("proof", proof())
    for s, n in SET:
        print(n, put(s, n))


if __name__ == "__main__":
    main()
