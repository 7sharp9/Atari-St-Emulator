"""Compare tools/pm_render_ref.py's float project() with the game's $3f364 corner
buffer in a RAM image, at the RAM's own camera/HALF. Usage: float_proj_check.py <ram> [assets_dir]"""
import sys, struct
from pathlib import Path
here = Path(__file__).resolve()
root = next(p for p in here.parents if (p / "tools" / "rdis.py").exists())
sys.path.insert(0, str(root / "tools"))
import pm_render_ref as R
ram = Path(sys.argv[1]).read_bytes()
assets = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "reversing/powermonger/port/assets"
terr, tables, dom, dith = R.load_assets(assets)
u16 = lambda a: (ram[a] << 8) | ram[a+1]
half = u16(0xFDEC); cx = u16(0x4BB3A) - half; cy = u16(0x4BB3C) - half
yaw = u16(0xFF9A); zoom = u16(0xFF9C)
tables = dict(tables); tables["projection"] = dict(tables["projection"], yaw_ff9a=yaw, zoom_scale_ff9c=zoom)
corners, bias = R.project(tables, terr, cx, cy, half)
n = 2*half+1; d0 = d1 = 0; worst = 0
for r in range(n):
    for c in range(n):
        p = struct.unpack_from(">I", ram, 0x3F364 + r*64 + c*4)[0]
        gx, gy = p >> 16, p & 0xFFFF
        gx = gx - 0x10000 if gx >= 0x8000 else gx
        gy = gy - 0x10000 if gy >= 0x8000 else gy
        fx, fy = corners[(r, c)]
        e = max(abs(round(fx) - gx), abs(round(fy) - gy))
        ef = max(abs(int(fx // 1) - gx), abs(int(fy // 1) - gy))
        worst = max(worst, e); d0 += e == 0; d1 += e <= 1
        F1 = globals().setdefault('F1',[0]); F1[0] += ef <= 1
print("floor within1", F1[0]); print(f"cam=({cx},{cy}) half={half} yaw={yaw:#x} zoom={zoom} bias={bias}: exact {d0}/{n*n}, within1 {d1}/{n*n}, worst {worst}")
