"""gfxview.py - browse the graphics a running ST program has decoded into RAM.

Added in the 54th pass of atari-st-emulator-next-instructions. Until now the only
windows into video memory were screendump.py (the *live framebuffer* only) and the
REPL `m` hex dump. A game like Super Sprint unpacks its title bitmap, HUD font, car
sprites and track tiles out of SUPER.DAT into RAM long before any of it reaches the
screen; this tool lets you look at all of it.

Input is a `.snap` file (the SaveState format written by Program.fs - magic "A68S",
a version byte, 19 int32 registers, an int16 CCR, then the length-prefixed RAM
array first), or any raw binary with `--raw` (+ optional `--base`).

Two outputs:

  * an HTML viewer - one self-contained file, RAM base64-embedded, a JS planar
    decoder with live controls (base / width / rows / bpp / plane layout /
    strides / palette / zoom). Open it in a browser, no server.

        python tools/gfxview.py game.snap --html game_gfx.html

  * a contact sheet PNG - a fast whole-RAM overview to find where the data is.

        python tools/gfxview.py game.snap --contact game_ram.png

Detected 16-word `$0RGB` palettes and non-trivial data spans are printed to stderr
and baked into the HTML as jump targets / palette choices.

Layouts the viewer understands:

  * st-interleaved  - standard ST screen memory: bpp bitplanes interleaved in
    16-pixel word groups (what the shifter reads, what screendump.py decodes).
  * planar-linear   - bitplanes stored one after another, each plane a plain
    1bpp bitmap; plane p at base + p*plane_stride, rows every row_stride bytes.
    Super Sprint's transposed sprite blitter ($15436) uses this with
    plane_stride 8, row_stride 1 (planes at src+8/+16/+24, source +1 byte/row).
  * chunky8         - one byte per pixel, straight palette index.
"""
import argparse
import base64
import json
import struct
import sys


# ---------------------------------------------------------------------------
# snapshot / input parsing
# ---------------------------------------------------------------------------

def load_ram(path, raw=False, base=0):
    """Return (ram_bytes, base_addr). For a .snap the base is always 0 (the RAM
    array is the whole 0..$100000 image); for --raw the caller's --base is used."""
    data = open(path, "rb").read()
    if raw or data[:4] != b"A68S":
        return data, base
    ver = data[4]
    reg_count = 19 if ver >= 5 else 18
    off = 5 + reg_count * 4 + 2                      # past magic+ver+regs+ccr
    ram_len = struct.unpack_from("<i", data, off)[0]
    off += 4
    ram = data[off:off + ram_len]
    if len(ram) != ram_len:
        sys.exit(f"{path}: truncated RAM block ({len(ram)} of {ram_len} bytes)")
    return ram, 0


def snapshot_regs(path):
    """(regs dict, ok) - regs a0..a7/d0..d7/pc, or ok=False if not a snapshot."""
    data = open(path, "rb").read()
    if data[:4] != b"A68S":
        return {}, False
    ver = data[4]
    n = 19 if ver >= 5 else 18
    vals = struct.unpack_from(f"<{n}i", data, 5)
    names = (["d%d" % i for i in range(8)] + ["a%d" % i for i in range(8)] +
             (["usp", "ssp", "pc"] if ver >= 5 else ["usp", "pc"]))
    return {k: v & 0xFFFFFFFF for k, v in zip(names, vals)}, True


# ---------------------------------------------------------------------------
# palette detection
# ---------------------------------------------------------------------------

def ste_colour(word):
    """$0RGB -> (r,g,b) 0..255. STF is 3 bits/gun (0..7); STE adds a 4th, least
    significant bit at nibble bit 3, so a gun nibble can reach 15. Detect STE by
    any gun > 7 and treat the whole palette as linear 4-bit in that case."""
    r, g, b = (word >> 8) & 0xF, (word >> 4) & 0xF, word & 0xF
    if r > 7 or g > 7 or b > 7:
        return (r * 255 // 15, g * 255 // 15, b * 255 // 15)
    return (r * 255 // 7, g * 255 // 7, b * 255 // 7)


def _classify_palette(words, allow_ste):
    """Return "STF" / "STE" / None. STF = every gun nibble 0..7 (the strict case
    the pass-54 brief asks for). STE = some nibble > 7 but still a plausible
    palette; only offered when allow_ste is set, and held to a higher bar because
    a random stretch of small words trips the loose test easily."""
    if len(set(words)) < 6:
        return None
    if sum(1 for x in words if x == 0) > 8:                 # mostly-black window
        return None
    guns = [g for x in words for g in ((x >> 8) & 0xF, (x >> 4) & 0xF, x & 0xF)]
    if max(guns) - min(guns) < 5:                           # flat blob
        return None
    if all(g <= 7 for g in guns):
        return "STF"
    if allow_ste and len(set(words)) >= 12 and sum(1 for g in guns if g > 7) >= 4:
        return "STE"
    return None


def detect_palettes(ram, base, allow_ste=False):
    """Find maximal runs of consecutive big-endian words that all look like ST
    colour entries ($0xxx). Within each run, greedily emit non-overlapping 16-word
    palettes (packed palette *tables* are common - Super Sprint keeps dozens near
    $1d4xx). De-duplicate by content, sorted by address."""
    import numpy as np
    n = len(ram) & ~1
    w = np.frombuffer(ram[:n], dtype=">u2").astype(np.uint32)
    valid = (w & 0xF000) == 0                       # $0RGB
    seen = {}
    out = []
    i, L = 0, len(valid)
    while i < L:
        if not valid[i]:
            i += 1
            continue
        j = i
        while j < L and valid[j]:
            j += 1
        # a run thousands of words long is just zero-ish data, not a palette table
        if 16 <= j - i <= 2048:
            s = i
            while s <= j - 16:
                words = [int(x) for x in w[s:s + 16]]
                kind = _classify_palette(words, allow_ste)
                if kind is None:
                    s += 1
                    continue
                key = tuple(words)
                if key not in seen:
                    seen[key] = base + s * 2
                    out.append({
                        "addr": base + s * 2, "type": kind, "words": words,
                        "colors": [ste_colour(x) for x in words],
                        "distinct": len(set(words)),
                    })
                s += 16                              # non-overlapping
        i = j
    out.sort(key=lambda c: c["addr"])
    return out


# ---------------------------------------------------------------------------
# data-span detection (advisory - where to point the viewer)
# ---------------------------------------------------------------------------

def detect_spans(ram, base, block=2048, min_run=4):
    """Coarse map: flag 2KB blocks that hold non-trivial data (not mostly 0x00,
    not mostly 0xFF, byte entropy in a graphics-ish band), merge adjacent runs of
    >= min_run blocks. Purely to give the viewer sensible jump targets."""
    import numpy as np
    nb = len(ram) // block
    a = np.frombuffer(ram[:nb * block], dtype=np.uint8).reshape(nb, block)
    zero = (a == 0).mean(axis=1)
    ones = (a == 0xFF).mean(axis=1)
    ent = np.zeros(nb)
    for i in range(nb):
        c = np.bincount(a[i], minlength=256).astype(np.float64)
        p = c[c > 0] / block
        ent[i] = float(-(p * np.log2(p)).sum())
    interesting = (zero < 0.97) & (ones < 0.6) & (ent > 0.8) & (ent < 7.7)
    spans, i = [], 0
    while i < nb:
        if interesting[i]:
            j = i
            while j < nb and interesting[j]:
                j += 1
            if j - i >= min_run:
                spans.append((base + i * block, base + j * block,
                              float(ent[i:j].mean()), float(zero[i:j].mean())))
            i = j
        else:
            i += 1
    return spans


# ---------------------------------------------------------------------------
# contact sheet
# ---------------------------------------------------------------------------

def contact_sheet(ram, base, out, mode="grey", width=1024):
    from PIL import Image
    import numpy as np
    if mode == "grey":
        # one pixel per byte, row-major - shows zero vs data regions at a glance
        n = (len(ram) // width) * width
        img = Image.fromarray(np.frombuffer(ram[:n], np.uint8).reshape(-1, width), "L")
    elif mode == "1bpp":
        bits = np.unpackbits(np.frombuffer(ram, np.uint8))
        n = (len(bits) // width) * width
        img = Image.fromarray((bits[:n].reshape(-1, width) * 255).astype(np.uint8), "L")
    elif mode == "4bpp":
        # decode the whole image as one tall st-interleaved 4bpp bitmap, greyscale
        px_w = width
        row_bytes = px_w // 2                    # 4 planes * px_w/16 words * 2
        rows = len(ram) // row_bytes
        a = np.frombuffer(ram[:rows * row_bytes], np.uint8).reshape(rows, row_bytes)
        out_img = np.zeros((rows, px_w), np.uint8)
        for x in range(px_w):
            wg, bit = x // 16, 15 - (x % 16)
            idx = np.zeros(rows, np.uint8)
            for p in range(4):
                o = wg * 8 + p * 2
                word = (a[:, o].astype(np.uint16) << 8) | a[:, o + 1]
                idx |= (((word >> bit) & 1) << p).astype(np.uint8)
            out_img[:, x] = idx * 17
        img = Image.fromarray(out_img, "L")
    else:
        sys.exit(f"unknown contact mode {mode}")
    img.save(out)
    print(f"wrote {out} ({img.size[0]}x{img.size[1]}, mode={mode})", file=sys.stderr)


# ---------------------------------------------------------------------------
# HTML viewer
# ---------------------------------------------------------------------------

HTML = r"""<!doctype html><html><head><meta charset=utf-8>
<title>gfxview - __SRC__</title>
<style>
 body{background:#1a1a1a;color:#ddd;font:13px system-ui,sans-serif;margin:0;display:flex}
 #side{width:290px;padding:12px;background:#222;height:100vh;overflow:auto;box-sizing:border-box}
 #main{flex:1;overflow:auto;height:100vh;background:#111;display:block}
 canvas{image-rendering:pixelated;display:block;margin:12px}
 label{display:block;margin:7px 0 2px;color:#9ab}
 input,select{width:100%;box-sizing:border-box;background:#333;color:#eee;border:1px solid #555;padding:3px}
 .row{display:flex;gap:6px}.row>*{flex:1}
 h3{margin:14px 0 4px;font-size:12px;color:#7a9;border-bottom:1px solid #444}
 .jump{cursor:pointer;padding:2px 4px;border-radius:3px}.jump:hover{background:#345}
 .sw{display:inline-block;width:14px;height:14px;border:1px solid #000}
 #status{font:11px monospace;color:#8a8;white-space:pre-wrap;margin-top:8px}
 small{color:#789}
</style></head><body>
<div id=side>
<h3>layout</h3>
<label>base address (hex)</label><input id=base value="__BASE__">
<div class=row><div><label>width px</label><input id=w value="320"></div>
<div><label>rows</label><input id=h value="200"></div></div>
<div class=row><div><label>bpp</label><select id=bpp>
 <option>1</option><option>2</option><option selected>4</option><option>8</option></select></div>
<div><label>zoom</label><select id=zoom>
 <option>1</option><option selected>2</option><option>3</option><option>4</option><option>6</option><option>8</option></select></div></div>
<label>plane layout</label><select id=mode>
 <option value=st>st-interleaved (screen RAM)</option>
 <option value=lin>planar-linear (contiguous planes)</option>
 <option value=chunky>chunky8 (1 byte/pixel)</option></select>
<div class=row><div><label>plane stride (hex, lin)</label><input id=ps value="0"></div>
<div><label>row stride (hex, 0=auto)</label><input id=rs value="0"></div></div>
<label>presets</label><select id=preset>
 <option value="">-</option>
 <option value="st,320,200,4">ST low-res screen 320x200x4</option>
 <option value="st,640,200,2">ST med-res screen 640x200x2</option>
 <option value="st,640,400,1">ST mono screen 640x400x1</option>
 <option value="lin,8,8,4,8,1">SS sprite tile 8x8x4 (stride 8/1)</option>
 <option value="lin,16,16,4,32,2">SS sprite 16x16x4 (stride 32/2)</option>
 <option value="chunky,256,256,8">chunky 256x256</option></select>
<h3>palette</h3>
<select id=pal></select>
<div id=swatches style="margin-top:4px"></div>
<h3>jump to</h3>
<div id=jumps></div>
<div id=status></div>
<small>drag on the image to read an address; &larr;/&rarr; step base by one row, &uarr;/&darr; by one byte, PgUp/PgDn by 0x1000</small>
</div>
<div id=main><canvas id=c></canvas></div>
<script>
const RAM = Uint8Array.from(atob("__DATA__"), c=>c.charCodeAt(0));
const PALS = __PALS__;
const JUMPS = __JUMPS__;
const $ = id => document.getElementById(id);
const hx = v => "$"+(v>>>0).toString(16);

function greyPal(n){ let p=[]; for(let i=0;i<n;i++){ let v=n>1?Math.round(i*255/(n-1)):0; p.push([v,v,v]); } return p; }

function buildPalUI(){
  let sel=$('pal'); sel.innerHTML="";
  [["greyscale",null]].concat(PALS.map((p,i)=>[`${p.type} @ ${hx(p.addr)}${p.note?" "+p.note:""}`,i]))
    .forEach(([t,v])=>{ let o=document.createElement('option'); o.text=t; o.value=v===null?"g":v; sel.add(o); });
  sel.onchange=draw;
}
function curPal(bpp){
  let v=$('pal').value, n=1<<bpp;
  let cols = v==="g" ? greyPal(n) : PALS[+v].colors;
  let sw=$('swatches'); sw.innerHTML="";
  cols.slice(0,n).forEach(c=>{ let s=document.createElement('span'); s.className="sw";
    s.style.background=`rgb(${c[0]},${c[1]},${c[2]})`; sw.appendChild(s); });
  return cols;
}
function buildJumps(){
  let d=$('jumps');
  JUMPS.forEach(j=>{ let e=document.createElement('div'); e.className="jump";
    e.textContent=j.label; e.onclick=()=>{ $('base').value=j.addr.toString(16);
      if(j.w){$('w').value=j.w;} if(j.h){$('h').value=j.h;}
      if(j.mode){$('mode').value=j.mode;} if(j.bpp){$('bpp').value=j.bpp;}
      if(j.pal!=null){$('pal').value=j.pal;} draw(); };
    d.appendChild(e); });
}

function pixel(base,x,y,bpp,mode,W,ps,rs){
  let idx=0;
  if(mode==="chunky"){ let o=base+y*(rs||W)+x; return o<RAM.length?RAM[o]:0; }
  if(mode==="st"){
    let rowBytes = rs || (W/16|0)*2*bpp;
    let wg=x/16|0, bit=15-(x&15);
    for(let p=0;p<bpp;p++){ let o=base+y*rowBytes+wg*2*bpp+p*2;
      if(o+1>=RAM.length) continue;
      let word=(RAM[o]<<8)|RAM[o+1]; idx|=((word>>bit)&1)<<p; }
    return idx;
  }
  // planar-linear
  let rowStride = rs || (W/8|0);
  let planeStride = ps || rowStride*(($('h').value|0));
  let bx=x/8|0, bit=7-(x&7);
  for(let p=0;p<bpp;p++){ let o=base+p*planeStride+y*rowStride+bx;
    if(o>=RAM.length) continue; idx|=((RAM[o]>>bit)&1)<<p; }
  return idx;
}

function draw(){
  let base=parseInt($('base').value,16)||0;
  let W=$('w').value|0, H=$('h').value|0, bpp=$('bpp').value|0;
  let mode=$('mode').value, z=$('zoom').value|0;
  let ps=parseInt($('ps').value,16)||0, rs=parseInt($('rs').value,16)||0;
  if(mode==="chunky") bpp=8;
  let cols=curPal(bpp);
  let cv=$('c'); cv.width=W; cv.height=H; cv.style.width=(W*z)+"px"; cv.style.height=(H*z)+"px";
  let ctx=cv.getContext('2d'), im=ctx.createImageData(W,H), d=im.data;
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    let i=pixel(base,x,y,bpp,mode,W,ps,rs);
    let c=cols[i&((1<<bpp)-1)]||[255,0,255];
    let o=(y*W+x)*4; d[o]=c[0]; d[o+1]=c[1]; d[o+2]=c[2]; d[o+3]=255;
  }
  ctx.putImageData(im,0,0);
  let rowBytes = mode==="chunky"?(rs||W): mode==="st"?(rs||(W/16|0)*2*bpp):(rs||(W/8|0));
  $('status').textContent =
    `base ${hx(base)}  ${W}x${H}x${bpp}  ${mode}\nrow stride ${hx(rowBytes)}  frame ${hx(rowBytes*H)}  end ${hx(base+rowBytes*H)}`;
}

$('preset').onchange=e=>{
  let v=e.target.value; if(!v) return;
  let a=v.split(",");
  $('mode').value=a[0]; $('w').value=a[1]; $('h').value=a[2]; $('bpp').value=a[3];
  if(a[0]==="lin"){ $('ps').value=(+a[4]).toString(16); $('rs').value=(+a[5]).toString(16); }
  else { $('ps').value="0"; $('rs').value="0"; }
  draw();
};
["base","w","h","bpp","zoom","mode","ps","rs"].forEach(id=>{
  $(id).addEventListener('input',draw); $(id).addEventListener('change',draw); });

document.addEventListener('keydown',e=>{
  if(/input|select/i.test(e.target.tagName)&&e.target.id!=="base") return;
  let base=parseInt($('base').value,16)||0;
  let W=$('w').value|0,bpp=$('bpp').value|0,mode=$('mode').value;
  let rb = mode==="chunky"?W: mode==="st"?(W/16|0)*2*bpp:(W/8|0);
  let step={ArrowRight:rb,ArrowLeft:-rb,ArrowDown:1,ArrowUp:-1,PageUp:-0x1000,PageDown:0x1000}[e.key];
  if(step===undefined) return;
  e.preventDefault(); $('base').value=Math.max(0,base+step).toString(16); draw();
});

let cv=$('c'), drag=false;
function report(ev){
  let r=cv.getBoundingClientRect(), z=$('zoom').value|0;
  let x=Math.floor((ev.clientX-r.left)/z), y=Math.floor((ev.clientY-r.top)/z);
  let base=parseInt($('base').value,16)||0;
  let W=$('w').value|0,bpp=$('bpp').value|0,mode=$('mode').value;
  let rb=parseInt($('rs').value,16)|| (mode==="chunky"?W: mode==="st"?(W/16|0)*2*bpp:(W/8|0));
  let ps=parseInt($('ps').value,16)||0;
  let i=pixel(base,x,y,bpp,mode,W,ps,parseInt($('rs').value,16)||0);
  $('status').textContent=`x=${x} y=${y}  index=${i}\nrow byte ${hx(base+y*rb)}  (base ${hx(base)} + ${hx(y*rb)})`;
}
cv.addEventListener('mousedown',e=>{drag=true;report(e);});
cv.addEventListener('mousemove',e=>{if(drag)report(e);});
document.addEventListener('mouseup',()=>drag=false);

buildPalUI(); buildJumps(); draw();
</script></body></html>
"""


def build_html(ram, base, out, src, palettes, spans, sidecar):
    b64 = base64.b64encode(ram).decode()
    pals = [{"addr": p["addr"], "type": p["type"], "colors": p["colors"],
             "note": p.get("note", "")} for p in palettes]

    jumps = []
    # screen buffers Super Sprint flips between + the usual TOS default
    for name, addr in (("screen $f8000", 0xF8000), ("screen $21100", 0x21100),
                       ("screen $78000", 0x78000)):
        jumps.append({"label": f"{name} (320x200x4)", "addr": addr,
                      "w": 320, "h": 200, "bpp": 4, "mode": "st",
                      "pal": 0 if pals else None})
    for i, p in enumerate(palettes):
        jumps.append({"label": f"palette {p['type']} @ {p['addr']:#x}", "addr": p["addr"],
                      "w": 16, "h": 16, "bpp": 4, "mode": "chunky"})
    for s in spans:
        jumps.append({"label": f"data span {s[0]:#x}-{s[1]:#x} (ent {s[2]:.1f})",
                      "addr": s[0], "w": 320, "h": 200, "bpp": 4, "mode": "st"})
    for label, addr in sidecar.get("pointers", []):
        jumps.append({"label": f"{label} {addr:#x}", "addr": addr})

    html = (HTML
            .replace("__DATA__", b64)
            .replace("__PALS__", json.dumps(pals))
            .replace("__JUMPS__", json.dumps(jumps))
            .replace("__SRC__", src)
            .replace("__BASE__", format(base if base else (spans[0][0] if spans else 0), "x")))
    open(out, "w", encoding="utf-8").write(html)
    print(f"wrote {out} ({len(html)//1024} KB, {len(palettes)} palettes, "
          f"{len(spans)} spans)", file=sys.stderr)


# ---------------------------------------------------------------------------
# optional sidecar (produced by the emulator when ATARI_GFX_SIDECAR is set)
# ---------------------------------------------------------------------------

def load_sidecar(path):
    """`<snap>.gfx` text sidecar: lines `palette <hex>` / `pointer <name> <hex>`.
    Behaviourally inert - the emulator only writes it, this only reads it."""
    out = {"palettes": [], "pointers": []}
    try:
        for ln in open(path):
            t = ln.split()
            if len(t) >= 2 and t[0] == "palette":
                out["palettes"].append(int(t[1], 16))
            elif len(t) >= 3 and t[0] == "pointer":
                out["pointers"].append((t[1], int(t[2], 16)))
    except FileNotFoundError:
        pass
    return out


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help=".snap file, or raw binary with --raw")
    ap.add_argument("--raw", action="store_true", help="treat input as a flat binary")
    ap.add_argument("--base", default="0", help="load/display base address (hex), for --raw")
    ap.add_argument("--html", help="write the interactive viewer here")
    ap.add_argument("--contact", help="write a contact-sheet PNG here")
    ap.add_argument("--contact-mode", default="grey", choices=("grey", "1bpp", "4bpp"))
    ap.add_argument("--contact-width", type=int, default=1024)
    ap.add_argument("--sidecar", help="path to a .gfx sidecar (default: <input>.gfx)")
    ap.add_argument("--no-detect", action="store_true", help="skip palette/span scan")
    ap.add_argument("--ste", action="store_true",
                    help="also report STE-style palettes (nibble > 7); noisier")
    args = ap.parse_args()

    base = int(args.base, 16)
    ram, base = load_ram(args.input, args.raw, base)
    print(f"{args.input}: {len(ram)} bytes, base {base:#x}", file=sys.stderr)

    regs, is_snap = ({}, False) if args.raw else snapshot_regs(args.input)
    if is_snap:
        print("  a4=%(a4)#010x  a5=%(a5)#010x  pc=%(pc)#010x" % regs, file=sys.stderr)

    sidecar = load_sidecar(args.sidecar or (args.input + ".gfx"))

    palettes, spans = [], []
    if not args.no_detect:
        palettes = detect_palettes(ram, base, allow_ste=args.ste)
        # tag the sidecar-observed Setpalette addresses
        obs = set(sidecar["palettes"])
        for p in palettes:
            if p["addr"] in obs:
                p["note"] = "(observed Setpalette)"
        spans = detect_spans(ram, base)
        print(f"  {len(palettes)} palette(s):", file=sys.stderr)
        for p in palettes[:16]:
            print(f"    {p['addr']:#010x} {p['type']} {p['distinct']:2d} colours"
                  f" {p.get('note','')}", file=sys.stderr)
        print(f"  {len(spans)} data span(s):", file=sys.stderr)
        for s in spans:
            print(f"    {s[0]:#010x}-{s[1]:#010x}  {(s[1]-s[0])//1024:4d} KB"
                  f"  entropy {s[2]:.2f}  zero {s[3]:.2f}", file=sys.stderr)

    if args.contact:
        contact_sheet(ram, base, args.contact, args.contact_mode, args.contact_width)
    if args.html:
        src = args.input.replace("\\", "/").rsplit("/", 1)[-1]
        build_html(ram, base, args.html, src, palettes, spans, sidecar)
    if not args.contact and not args.html:
        print("nothing to do: pass --html and/or --contact", file=sys.stderr)


if __name__ == "__main__":
    main()
