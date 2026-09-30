'use strict';
/* landscape_core.js - JS port of Populous's landscape code, for landscape_infographic.html.

   Every function is a transcription of a routine documented in terrain.md / graphics.md, and is
   checked against the Python models (popgen.py, powers/powers_ref.py, pop_render.py) by
   landscape_infographic.py --check (which runs landscape_check.js in node).

     rand           $16702      raisePt   $bf60      lowerPt  $d262
     derive         $c0ee       genWorld  $b316 (terrain part: $be84 walks, $c0ee, $12e06 scatter)
     cmdRaise       $1186c      cmdLower  $116fa
     flood          $11f6a      earthquake $12350    volcano  $1263c     swamp $12a14
     cornerAt       $119e6 (land cursor, as popdrive.corner_at)
     renderTerrain  $14364 / $142d6 / $14540

   World arrays: h = 65x65 corner heights ($34be4, index y*65+x), alt/shape/feat = 64x64 bytes
   ($33be4, $36e78, $3c522, index y*64+x). */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LS = factory();
})(this, function () {
  const N = 65;
  const NB = [[1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1], [0, -1], [1, -1]]; // E SE S SW W NW N NE

  function World(seed) {
    this.seed = (seed || 0) & 0xffff;
    this.h = new Int16Array(N * N);
    this.alt = new Uint8Array(4096);
    this.shape = new Uint8Array(4096);
    this.feat = new Uint8Array(4096);
    this.points = 0;            // $37f8a, corner changes made by the last raise/lower
    this.box = [0, 0, 0, 0];    // dirty box: min x, max x, min y, max y ($36ce8 $3b006 $3d522 $37eb8)
    this.draws = 0;             // rand() calls so far (instrumentation, not in the game)
    this.log = null;            // when an array, every corner change pushes its corner index (lowers: -(i+1))
    this.protect = [0];         // cells a volcano's rock may not land on (no leader, no magnets: cell 0)
  }
  World.prototype.clone = function () {
    const w = new World(this.seed);
    w.h.set(this.h); w.alt.set(this.alt); w.shape.set(this.shape); w.feat.set(this.feat);
    w.protect = this.protect.slice();
    return w;
  };

  function rand(w) {          // $16702
    w.seed = (w.seed * 0x24a1 + 0x24df) & 0x7fff;
    w.draws++;
    return w.seed;
  }

  function growBox(w, x, y) {
    const b = w.box;
    if (x < b[0]) b[0] = x;
    if (x > b[1]) b[1] = x;
    if (y < b[2]) b[2] = y;
    if (y > b[3]) b[3] = y;
  }

  function raisePt(w, x, y) { // $bf60
    if (x > 64 || x < 0 || y > 64 || y < 0) return 0;
    const i = x + N * y, h = w.h;
    if (h[i] >= 8) return h[i];
    w.points++;
    h[i]++;
    if (w.log) w.log.push(i);
    for (let k = 0; k < 8; k++) {
      const nx = x + NB[k][0], ny = y + NB[k][1];
      if (nx < 0 || nx > 64 || ny < 0 || ny > 64) continue; // the game's call would be rejected
      if (h[i] - h[nx + N * ny] > 1) raisePt(w, nx, ny);
    }
    growBox(w, x, y);
    return h[i];
  }

  function lowerPt(w, x, y) { // $d262
    if (x > 64 || x < 0 || y > 64 || y < 0) return 0;
    const i = x + N * y, h = w.h;
    if (h[i] === 0) return 0;
    w.points++;
    h[i]--;
    if (w.log) w.log.push(-1 - i);      // a lowered corner is logged as -(i+1)
    for (let k = 0; k < 8; k++) {
      const nx = x + NB[k][0], ny = y + NB[k][1];
      if (nx < 0 || nx > 64 || ny < 0 || ny > 64) continue;
      if (h[nx + N * ny] - h[i] > 1) lowerPt(w, nx, ny);
    }
    growBox(w, x, y);
    return h[i];
  }

  // $c0ee(x0,y0,x1,y1): recompute altitude / shape / feature for cells x0..x1 by y0..y1
  function cellOf(w, x, y) {
    const i = x + N * y, h = w.h;
    const a = h[i], b = h[i + 1], c = h[i + 66], d = h[i + 65];
    let s = (a + b + c + d) >> 2;
    let bits = (a > s ? 1 : 0) | (b > s ? 2 : 0) | (c > s ? 4 : 0) | (d > s ? 8 : 0);
    return { a, b, c, d, s, bits };
  }
  function derive(w, x0, y0, x1, y1) {
    for (let x = x0; x <= x1; x++) {
      for (let y = y0; y <= y1; y++) {
        const cell = x + (y << 6);
        const r = cellOf(w, x, y);
        let s = r.s, d5;
        if (w.shape[cell] === 0x2f && (r.bits || s)) d5 = w.shape[cell];
        else { w.shape[cell] = r.bits; d5 = r.bits; }
        if (s && !d5) { s--; d5 = 0x0f; }
        if (s === 0 && d5 !== 0x0f && d5) d5 += 0x10;
        w.alt[cell] = s;
        if (w.shape[cell] !== 0x2f) w.shape[cell] = d5; else d5 = 0x2f;
        if (d5 === 0) w.feat[cell] = 0;
      }
    }
  }
  // what one cell becomes: the rule of derive() without touching the world (for the cell widget)
  function deriveCell(a, b, c, d) {
    let s = (a + b + c + d) >> 2;
    const bits = (a > s ? 1 : 0) | (b > s ? 2 : 0) | (c > s ? 4 : 0) | (d > s ? 8 : 0);
    let shape = bits, alt = s, note = 'slope: block = the mask of raised corners';
    if (s && !bits) { alt = s - 1; shape = 0x0f; note = 'flat land: one level lower, block $0f'; }
    else if (s === 0 && bits) { shape = bits + 0x10; note = 'slope at sea level: shore block, mask + $10'; }
    else if (!bits) note = 'all corners at sea level: sea, block 0';
    return { avg: s, bits, shape, alt, note };
  }

  function clampBoxDerive(w) {
    const b = w.box;
    if (b[0] < 1) b[0] = 1;
    if (b[1] > 63) b[1] = 63;
    if (b[2] < 1) b[2] = 1;
    if (b[3] > 63) b[3] = 63;
    derive(w, b[0] - 1, b[2] - 1, b[1], b[3]);
  }

  // The land commands as the game runs them: seed the box, clear the counter, change, re-derive.
  // Returns { points, cost } (cost 4n + 10, charged by the caller).
  function cmdRaise(w, x, y) {
    w.box = [x, x, y, y]; w.points = 0;
    raisePt(w, x, y);
    clampBoxDerive(w);
    return { points: w.points, cost: 4 * w.points + 10 };
  }
  function cmdLower(w, x, y) {
    w.box = [x, x, y, y]; w.points = 0;
    lowerPt(w, x, y);
    clampBoxDerive(w);
    return { points: w.points, cost: 4 * w.points + 10 };
  }

  // ------------------------------------------------------------ the powers (terrain effect only)
  function flood(w) {                 // $11f6a
    for (let i = 0; i < N * N; i++) if (w.h[i] > 0) w.h[i]--;
    derive(w, 0, 0, 63, 63);
  }
  function earthquake(w, x, y) {      // $12350, the RNG + re-derive half from $12470
    w.box = [x, x, y, y];
    for (let pass = 0; pass < 2; pass++) {
      for (let cx = x; cx <= x + 8; cx++) {
        for (let cy = y; cy <= y + 8; cy++) {
          if (w.h[cx + N * cy] === 0) continue;
          const r = rand(w) % 5;
          if (r === 1) raisePt(w, cx, cy);
          else if (r >= 2) lowerPt(w, cx, cy);
        }
      }
    }
    clampBoxDerive(w);
  }
  function volcano(w, x, y) {         // $1263c
    w.box = [x, x, y, y];
    for (let a = 0; a < 5; a++) {
      for (let i = a; i < 9 - a; i++) {
        for (let j = a; j < 9 - a; j++) {
          const r = rand(w) % 5;
          if (r === 1 || r === 2 || r === 4) raisePt(w, x + i, y + j);
        }
      }
    }
    for (let cx = x; cx < x + 8; cx++) {
      for (let cy = y; cy < y + 8; cy++) {
        if (cx < 0 || cx > 63 || cy < 0 || cy > 63) continue;
        const c = cx + (cy << 6);
        if (rand(w) % 5) continue;
        if (w.protect.indexOf(c) >= 0) continue;
        w.shape[c] = 0x2f; w.feat[c] = 0;
      }
    }
    clampBoxDerive(w);
  }
  function swamp(w, x, y, occ) {      // $12a14; occ(cell) -> true when an entity stands there
    const hit = [];
    for (let t = 0; t < 30; t++) {
      const cx = x + (rand(w) % 7) - 3;
      const cy = y + (rand(w) % 7) - 3;
      if (cx < 0 || cx > 63 || cy < 0 || cy > 63) continue;
      const c = cx + (cy << 6), s = w.shape[c];
      if ((s === 0x0f || s === 0x1f || s === 0x20 || s === 0x42) && !(occ && occ(c))) {
        w.shape[c] = 0x35; hit.push(c);
      }
    }
    return hit;
  }

  // ------------------------------------------------------------ generation ($b316, terrain part)
  function walk(w, rx, ry, rec, k) {  // $bebc
    let x = rand(w) % 64;
    let y = rand(w) % 64;
    for (;;) {
      const top = raisePt(w, x, y);
      if (rec) rec.push({ walk: k, x, y, cum: w.log.length });
      if (top === 6) break;
      x += (rand(w) % (rx * 2 + 1)) - rx;
      y += (rand(w) % (ry * 2 + 1)) - ry;
      x = Math.min(Math.max(x, 0), 64);
      y = Math.min(Math.max(y, 0), 64);
    }
  }
  function genLand(w, rec) {          // $be84
    walk(w, 2, 4, rec, 0); walk(w, 4, 2, rec, 1); walk(w, 3, 3, rec, 2);
  }
  function scatter(w, rec) {          // $12e06
    for (let k = 0; k < 22; k++) {
      const rock = k < 7;
      const r1 = rand(w), r2 = rand(w);
      const placed = [];
      for (let t = 0; t < 30; t++) {
        const x = (rand(w) % 9) + (r1 % 59);
        const y = (rand(w) % 9) + (r2 % 59);
        if (x >= 0 && x < 64 && y >= 0 && y < 64) {
          const c = x + (y << 6);
          if (w.shape[c] !== 0 && w.shape[c] !== 0x2f) {
            const v = (rand(w) % 3) + (rock ? 0x2f : 0x32);
            if (rock) w.shape[c] = v; else w.feat[c] = v;
            placed.push([c, v]);
          }
        }
      }
      if (rec) rec.push({ cluster: k, rock, x0: r1 % 59, y0: r2 % 59, placed });
    }
  }
  // rec (optional) = { steps: [], log: [], clusters: [] } receives the replay data
  function genWorld(seed, prerolls, rec) {
    const w = new World(seed);
    for (let i = 0; i < prerolls; i++) rand(w);
    if (rec) { w.log = rec.log; }
    genLand(w, rec ? rec.steps : null);
    w.log = null;
    derive(w, 0, 0, 63, 63);
    scatter(w, rec ? rec.clusters : null);
    return w;
  }

  // The world as it stood at a replay stage: 0..steps.length = after that many walk steps (raise calls),
  // then one more stage per scatter cluster (22). rec is the record genWorld filled in.
  function replayWorld(rec, stage) {
    const w = new World(0), ns = rec.steps.length;
    const cum = stage <= 0 ? 0 : (stage <= ns ? rec.steps[stage - 1].cum : rec.log.length);
    for (let i = 0; i < cum; i++) w.h[rec.log[i]]++;
    derive(w, 0, 0, 63, 63);
    for (let k = 0; k < stage - ns && k < rec.clusters.length; k++) {
      const cl = rec.clusters[k];
      for (const [c, v] of cl.placed) { if (cl.rock) w.shape[c] = v; else w.feat[c] = v; }
    }
    return w;
  }

  // ------------------------------------------------------------ land cursor ($119e6)
  function landOk(x, y) {
    const u = y + (x >> 1) - 32, v = y - (x >> 1) + 32;
    return u >= 0x3e && u <= 0x10a && v >= -0x40 && v <= 0x88 && x >= 0x40;
  }
  // The corner under the pointer (x,y) for view origin (ox,oy): [cx, cy, highlightY] or null.
  function cornerAt(w, ox, oy, x, y) {
    if (!landOk(x, y)) return null;
    const col = (x - 0x38) >> 4;
    let c0 = oy * N + ox, n = 9, sy = 0x48;
    if (col > 8) { n = 17 - col; c0 += col - 8; sy += (col - 8) * 8; }
    if (col < 8) { n = col + 1; c0 += N * (8 - col); sy += 8 * (8 - col); }
    let best = null;
    for (let k = 0; k < n; k++) {
      const c = c0 + 66 * k;
      const ys = sy + 16 * k - 8 * w.h[c];
      if (ys <= y + 4) best = [c, ys - 3];
    }
    if (!best) return null;
    return [best[0] % N, (best[0] / N) | 0, best[1]];
  }
  // where corner (cx,cy) is drawn for view origin (ox,oy): [x, y] of the corner marker, or null
  function cornerXY(w, ox, oy, cx, cy) {
    const i = cx - ox, j = cy - oy;
    if (i < 0 || i > 8 || j < 0 || j > 8) return null;
    return [192 + 16 * (i - j), 72 + 8 * (i + j) - 8 * w.h[cx + N * cy]];
  }

  // ------------------------------------------------------------ terrain renderer
  const ORG = 0x2858, EMPTY = 255;
  const pmod = (a, b) => ((a % b) + b) % b;
  function blit(pix, img, bw, bh, x0, y0) {
    for (let j = 0; j < bh; j++) {
      const yy = y0 + j;
      if (yy < 0 || yy >= 200) continue;
      for (let i = 0; i < bw; i++) {
        const c = img[j * bw + i];
        if (c < 0) continue;
        const xx = x0 + i;
        if (xx >= 0 && xx < 320) pix[yy * 320 + xx] = c;
      }
    }
  }
  // $142d6: the destination of block (col,row) lifted by hpix pixels; returns [x,y] or null
  function blockPos(col, row, hpix) {
    const off = ORG + 8 * col - 8 * row + 160 * (8 * col + 8 * row) - 160 * hpix;
    if (off < 0) return null;
    return [((pmod(off, 160) / 8) | 0) * 16, Math.floor(off / 160)];
  }
  // pix: Uint8Array(64000), EMPTY where nothing is drawn. blocks[n] / spr[n]: Int8Array, -1 transparent.
  // opts.cells: draw only the first n cells in painter order (and no walls until n = 64).
  // opts.trace: array that receives {cell, col, row, layer, block, x, y} for each block drawn.
  function renderTerrain(pix, w, blocks, spr, cx, cy, shim, opts) {
    opts = opts || {};
    const ncell = opts.cells === undefined ? 64 : opts.cells;
    const trace = opts.trace;
    function put(col, row, hpix, blk, cell, layer) {
      const p = blockPos(col, row, hpix);
      if (!p) return;
      blit(pix, blocks[blk], 32, 24, p[0], p[1]);
      if (trace) trace.push({ cell, col, row, layer, block: blk, x: p[0], y: p[1] });
    }
    for (let r = 0; r < 8; r++) {
      for (let c = 0; c < 8; c++) {
        if (r * 8 + c >= ncell) break;
        const cell = (cy + r) * 64 + cx + c;
        let b = w.shape[cell];
        if (b === 0 && shim === 0) b = 0x10;
        let h = w.alt[cell] * 8;
        put(c, r, h, b, cell, 'ground');
        h += 8;
        const o = w.feat[cell];
        if (o) put(c, r, h, o, cell, 'feature');
      }
    }
    if (ncell < 64 || opts.walls === false) return;
    const sp = (off, n) => blit(pix, spr[n], 16, 16, ((pmod(off, 160) / 8) | 0) * 16, Math.floor(off / 160));
    let base = ORG + 0x2840;
    for (let r = 0; r < 8; r++) {
      const hh = w.alt[(cy + r) * 64 + cx + 7];
      for (let k = 0; k < hh; k++) sp(base - 0x500 * k, 77);
      base += 0x4f8;
    }
    base -= 0x500;
    for (let c = 7; c >= 0; c--) {
      const hh = w.alt[(cy + 7) * 64 + cx + c];
      for (let k = 0; k < hh; k++) sp(base - 0x500 * k, 76);
      base -= 0x508;
    }
  }

  // decode a "0-9a-f." string (. = transparent) into Int8Array
  function decodeImg(s) {
    const a = new Int8Array(s.length);
    for (let i = 0; i < s.length; i++) { const ch = s.charCodeAt(i); a[i] = ch === 46 ? -1 : (ch <= 57 ? ch - 48 : ch - 87); }
    return a;
  }

  return {
    N, World, rand, raisePt, lowerPt, derive, deriveCell, cellOf, clampBoxDerive, cmdRaise, cmdLower,
    flood, earthquake, volcano, swamp, walk, genLand, scatter, genWorld, replayWorld,
    landOk, cornerAt, cornerXY, blockPos, renderTerrain, decodeImg, EMPTY, ORG,
  };
});
