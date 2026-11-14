"""Render the three landscapes from the model (virus_terrain.py) as one 3-panel PNG, 256x256 cells each at 2x.
White (255) is the water clamp.  Usage: python render_heightmaps.py <out.png> [snap]   (snap supplies the model's RAM sine
table only for the equality check; default scratchpad/virus/drive/g_game2.snap)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcommon, virus_terrain as vt
import numpy as np
from PIL import Image
S = vt.sine_table()
tiles = []
for L in (0, 1, 2):
    v = vt.VARIANTS[L]; f = np.zeros((256, 256), np.uint8)
    for cy in range(256):
        for cx in range(256):
            m = vt.model_byte(cx << 8, cy << 8, S, v); f[cy, cx] = 0xd7 if m is None else m
    tiles.append(f)
im = np.concatenate(tiles, axis=1)
Image.fromarray(im).resize((im.shape[1] * 2, im.shape[0] * 2), Image.NEAREST).save(sys.argv[1])
print('wrote', sys.argv[1])
