-- sp.lua (Final Fight pass 5, agent A): load a state, spawn records of any pool through the real allocator bookkeeping, log every live record of
-- pools 8, a, 6, 4, 12, 14 (changed-only), take screenshots, hide records. Own MAME run dir: run it with run.sh.
-- Env (all optional unless noted):
--   FFA_LOAD     state name in <run>/sta/ffightuc/ (loaded on the first frame; the base frame is the frame number after the load)
--   FFA_SPAWNS   "rel:pool:kind:b20:b21:x:y[:b54[:b98[:b96]]],..."  rel = frame after the load; pool = 2|4|6|8|a|12|14 (hex); numbers hex.
--                x is hex absolute, or "c" followed by a signed hex offset from the camera x (c+40, c-20). y absolute hex ("c" + off: camera y).
--                pool 2 and 4 spawns: b96 default 0.  Fields are written as $61f8 writes them (+0=1, x, y, +19, +20/+21, +54, +98, +96).
--   FFA_KILL     rel frame list: clear +0 of every pool-2 record then (isolates what is spawned)
--   FFA_POKES    "rel:addr:value:width,..." hex addr/value; addr "@N" is decimal offset into the FIRST spawned record
--   FFA_PIN      "lo-hi:who:xhex[:yhex],..." each frame in the rel window write x (and y and the ground line) of who = P (player 1) or N (the Nth spawn, 1-based)
--   FFA_HOLD     "lo-hi:N:offset(decimal):valuehex:width,..." each frame in the rel window write value at record N (1-based spawn) + offset
--   FFA_GFX      "name:addrhex:lenhex,..." per-frame hash of gfx RAM regions, line "G name hash nwords_changed" on a change (palette RAM is $914000-$9157ff, scroll maps $908000/$90c000/$910000)
--   FFA_SWEEP    "lo-hi:x0:x1[:y]" move player 1 linearly from x0 to x1 over that rel window; FFA_LIMIT=hex writes the camera right limit 1078(A5) every frame
--   FFA_KILLALL  "lo-hi" every frame in the window clear +0 of every pool-2 record and write 278(A5) = 0 (camera lock) so sweeps are not stopped by the stage script
--   FFA_WATCH    "hexaddr:width,..." a line "B <addr> <value>" (after the F line of the frame) whenever the value changes
--   FFA_HOLDA    "lo-hi:addrhex:valuehex:width,..." each frame in the rel window write an absolute address
--   FFA_HEAL     1: refill player 1 +24/+26 from +28 every frame
--   FFA_LOG      log file. Lines: "F <abs> rel=<n> cam=x,y s=stage,area p1=x,y,hp" per frame; "R <pool> <addr> <192 byte hex>" when a live record's bytes
--                changed since the last logged frame; "X <pool> <addr>" when it stopped being live (+0 == 0)
--   FFA_LOG_LO/HI  rel window of the log (default 0..stop)
--   FFA_STOP     rel frame at which to exit (default 600)
--   FFA_SHOT     "rel,rel,..." screenshot frames (names <FFA_TAG>_<rel>.png under <run>/snap)
--   FFA_HIDE     "rel:addr[+addr..]" zero +0 of those records at rel (hide test; the sprite is built a frame ahead, so shoot at rel+3)
--   FFA_PLAN2    lua file returning {rel, field, level} input entries
--   FFA_POOLS    extra census list "tag:base:stride:count,..." (hex) to log besides the defaults
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local A5 = 0xff8000
local function num(s) return tonumber(s, 16) end
local out = assert(io.open(os.getenv("FFA_LOG") or "sp.log", "w"))
local stop = tonumber(os.getenv("FFA_STOP") or "600")
local lo, hi = tonumber(os.getenv("FFA_LOG_LO") or "0"), tonumber(os.getenv("FFA_LOG_HI") or tostring(stop))
local tag = os.getenv("FFA_TAG") or "sp"

-- allocator bookkeeping: tag -> {count offset, stack pointer offset}
local ALLOC = { [2] = {20240, 20242}, [6] = {20258, 20260}, [4] = {20280, 20282}, [8] = {20346, 20348}, [0xa] = {20384, 20386}, [0x12] = {20410, 20412} }
local function alloc(pool)
  local a = ALLOC[pool]
  local cnt = m:read_u16(A5 + a[1])
  if cnt == 0 then return nil end
  local sp = m:read_u32(A5 + a[2])
  local w = m:read_u16(sp)
  local rec = 0xff0000 | w
  m:write_u16(sp, 0)
  m:write_u32(A5 + a[2], sp + 2)
  m:write_u16(A5 + a[1], cnt - 1)
  return rec
end

local spawns = {}
for spec in string.gmatch(os.getenv("FFA_SPAWNS") or "", "[^,]+") do
  local t = {}
  for p in string.gmatch(spec, "[^:]+") do t[#t + 1] = p end
  spawns[#spawns + 1] = { rel = tonumber(t[1]), pool = num(t[2]), kind = num(t[3]), b20 = num(t[4] or "0"), b21 = num(t[5] or "0"),
    x = t[6] or "0", y = t[7] or "0", b54 = num(t[8] or "0"), b98 = num(t[9] or "0"), b96 = num(t[10] or "0") }
end
local function coord(s, camv)
  if s:sub(1, 1) == "c" then
    local sign = s:sub(2, 2) == "-" and -1 or 1
    local v = num(s:sub(3)) or 0
    return (camv + sign * v) & 0xffff
  end
  return num(s)
end
local pokes = {}
for spec in string.gmatch(os.getenv("FFA_POKES") or "", "[^,]+") do
  local f, a, v, w = string.match(spec, "(%d+):(@?%x+):(%x+):(%d)")
  local off
  if a:sub(1, 1) == "@" then off = tonumber(a:sub(2)) end
  pokes[#pokes + 1] = { f = tonumber(f), a = (not off) and num(a) or nil, off = off, v = num(v), w = tonumber(w) }
end
local kills = {}
for f in string.gmatch(os.getenv("FFA_KILL") or "", "(%d+)") do kills[tonumber(f)] = true end
local shots = {}
for f in string.gmatch(os.getenv("FFA_SHOT") or "", "(%d+)") do shots[tonumber(f)] = true end
local hides = {}
for f, list in string.gmatch(os.getenv("FFA_HIDE") or "", "(%d+):([%x+]+)") do
  hides[tonumber(f)] = hides[tonumber(f)] or {}
  for a in string.gmatch(list, "(%x+)") do table.insert(hides[tonumber(f)], num(a)) end
end
local plan2 = os.getenv("FFA_PLAN2") and dofile(os.getenv("FFA_PLAN2")) or {}

local pools = {
  { "8", 0xff9b28, 192, 30 }, { "a", 0xffb2e8, 192, 16 }, { "6", 0xff90a8, 192, 6 }, { "4", 0xff9528, 192, 8 },
  { "12", 0xffbee8, 192, 10 }, { "14", 0xffc668, 64, 30 }, { "2", 0xff86e8, 192, 13 },
}
for spec in string.gmatch(os.getenv("FFA_POOLS") or "", "[^,]+") do
  local t = {}
  for p in string.gmatch(spec, "[^:]+") do t[#t + 1] = p end
  pools[#pools + 1] = { t[1], num(t[2]), num(t[3]), num(t[4]) }
end
local prev = {}
-- FFA_WATCH="addr:w,addr:w,..." (hex address, width 1|2|4): a line "B <addr> <value>" whenever the value changed
local watch = {}
for spec in string.gmatch(os.getenv("FFA_WATCH") or "", "[^,]+") do
  local a, w = string.match(spec, "(%x+):(%d)")
  watch[#watch + 1] = { a = tonumber(a, 16), w = tonumber(w), v = nil }
end
-- FFA_GFX="name:addrhex:lenhex,...": per frame, FNV hash of those gfx RAM regions; a line "G <name> <hash> <nbytes_changed_vs_previous>" is logged when the hash changed
local gfx = {}
for spec in string.gmatch(os.getenv("FFA_GFX") or "", "[^,]+") do
  local n, a, l = string.match(spec, "(%w+):(%x+):(%x+)")
  gfx[#gfx + 1] = { name = n, a = tonumber(a, 16), len = tonumber(l, 16), h = nil, last = nil }
end
local function fnv_region(base, len)
  local h = 2166136261
  local t = {}
  for a = base, base + len - 1, 2 do
    local v = m:read_u16(a)
    t[#t + 1] = v
    h = ((h ~ (v & 0xff)) * 16777619) & 0xffffffff
    h = ((h ~ (v >> 8)) * 16777619) & 0xffffffff
  end
  return h, t
end
local function rec_hex(a, n)
  local t = {}
  for i = 0, n - 1, 2 do t[#t + 1] = string.format("%04x", m:read_u16(a + i)) end
  return table.concat(t)
end

local loaded, base = false, nil
local first_spawn
local spawned = {}
emu.register_frame_done(function()
  local f = L.frame()
  local ld = os.getenv("FFA_LOAD")
  if ld and not loaded then loaded = true; manager.machine:load(ld); return end
  if not base then base = f end
  local rel = f - base
  local camx, camy = m:read_u16(A5 + 1042), m:read_u16(A5 + 1046)
  do local ka = os.getenv("FFA_KILLALL"); if ka then local a_, b_ = string.match(ka, "(%d+)-(%d+)"); if rel >= tonumber(a_) and rel <= tonumber(b_) then
    for i = 0, 12 do m:write_u8(0xff86e8 + 192 * i, 0) end; m:write_u8(A5 + 278, 0) end end end
  if kills[rel] then for i = 0, 12 do m:write_u8(0xff86e8 + 192 * i, 0) end end
  for _, s in ipairs(spawns) do
    if s.rel == rel then
      local a = alloc(s.pool)
      if not a then out:write(string.format("SPAWN FAILED pool %x rel=%d\n", s.pool, rel))
      else
        first_spawn = first_spawn or a
        spawned[#spawned + 1] = a
        m:write_u8(a, 1)
        m:write_u16(a + 6, coord(s.x, camx)); m:write_u16(a + 10, coord(s.y, camy))
        m:write_u8(a + 19, s.kind); m:write_u8(a + 20, s.b20); m:write_u8(a + 21, s.b21)
        m:write_u8(a + 54, s.b54); m:write_u8(a + 98, s.b98); m:write_u8(a + 96, s.b96)
        out:write(string.format("SPAWN rel=%d pool=%x rec=%06x kind=%x +20=%02x +21=%02x x=%04x y=%04x +18=%02x\n", rel, s.pool, a, s.kind, s.b20, s.b21,
          m:read_u16(a + 6), m:read_u16(a + 10), m:read_u8(a + 18)))
      end
    end
  end
  for _, p in ipairs(pokes) do
    if p.f == rel then
      local a = p.a or (first_spawn + p.off)
      if p.w == 1 then m:write_u8(a, p.v) elseif p.w == 2 then m:write_u16(a, p.v) else m:write_u32(a, p.v) end
    end
  end
  for _, e in ipairs(plan2) do if e[1] == rel then L.F[e[2]]:set_value(e[3]) end end
  for lo_, hi_, who, xs, ys in string.gmatch(os.getenv("FFA_PIN") or "", "(%d+)-(%d+):(%w+):(%x+):?(%x*)") do
    if rel >= tonumber(lo_) and rel <= tonumber(hi_) then
      local a = (who == "P") and 0xff8568 or spawned[tonumber(who)]
      if a then
        m:write_u16(a + 6, num(xs))
        if ys ~= "" then m:write_u16(a + 10, num(ys)); m:write_u16(a + 14, num(ys)) end
      end
    end
  end
  for lo_, hi_, n_, off_, v_, wd_ in string.gmatch(os.getenv("FFA_HOLD") or "", "(%d+)-(%d+):(%d+):(%d+):(%x+):(%d)") do
    if rel >= tonumber(lo_) and rel <= tonumber(hi_) and spawned[tonumber(n_)] then
      local a = spawned[tonumber(n_)] + tonumber(off_)
      if wd_ == "1" then m:write_u8(a, num(v_)) elseif wd_ == "2" then m:write_u16(a, num(v_)) else m:write_u32(a, num(v_)) end
    end
  end
  do -- FFA_SWEEP="lo-hi:x0:x1[:y]" move player 1 linearly (x at +6, optional y at +10/+14) over the rel window; FFA_LIMIT=hex writes the camera right limit 1078(A5) every frame
    local sw = os.getenv("FFA_SWEEP")
    if sw then
      local lo_, hi_, x0, x1, yy = string.match(sw, "(%d+)-(%d+):(%x+):(%x+):?(%x*)")
      lo_, hi_ = tonumber(lo_), tonumber(hi_)
      if rel >= lo_ and rel <= hi_ then
        local x = num(x0) + math.floor((num(x1) - num(x0)) * (rel - lo_) / (hi_ - lo_))
        m:write_u16(0xff8568 + 6, x)
        if yy ~= "" then m:write_u16(0xff8568 + 10, num(yy)); m:write_u16(0xff8568 + 14, num(yy)) end
      end
    end
    if os.getenv("FFA_LIMIT") then m:write_u16(A5 + 1078, num(os.getenv("FFA_LIMIT"))) end
  end
  for lo_, hi_, ad_, v_, wd_ in string.gmatch(os.getenv("FFA_HOLDA") or "", "(%d+)-(%d+):(%x+):(%x+):(%d)") do
    if rel >= tonumber(lo_) and rel <= tonumber(hi_) then
      local a = tonumber(ad_, 16)
      if wd_ == "1" then m:write_u8(a, num(v_)) elseif wd_ == "2" then m:write_u16(a, num(v_)) else m:write_u32(a, num(v_)) end
    end
  end
  if hides[rel] then for _, a in ipairs(hides[rel]) do m:write_u8(a, 0) end end
  if os.getenv("FFA_HEAL") == "1" then m:write_u16(0xff8580, m:read_u16(0xff8584)); m:write_u16(0xff8582, m:read_u16(0xff8584)) end
  if rel >= lo and rel <= hi then
    out:write(string.format("F %d rel=%d cam=%04x,%04x s=%02x,%02x p1=%04x,%04x,%04x c167=%02x c140=%02x c142=%02x cam2=%04x,%04x\n", f, rel, camx, camy, m:read_u8(A5 + 190), m:read_u8(A5 + 191),
      m:read_u16(0xff856e), m:read_u16(0xff8572), m:read_u16(0xff8580), m:read_u8(A5 + 167), m:read_u8(A5 + 140), m:read_u8(A5 + 142), m:read_u16(A5 + 1170), m:read_u16(A5 + 1174)))
    for _, pl in ipairs(pools) do
      for i = 0, pl[4] - 1 do
        local a = pl[2] + pl[3] * i
        local live = m:read_u8(a) ~= 0
        if live then
          local h = rec_hex(a, pl[3])
          if prev[a] ~= h then out:write(string.format("R %s %06x %s\n", pl[1], a, h)); prev[a] = h end
        elseif prev[a] then
          out:write(string.format("X %s %06x\n", pl[1], a)); prev[a] = nil
        end
      end
    end
    for _, wv in ipairs(watch) do
      local v = (wv.w == 1) and m:read_u8(wv.a) or (wv.w == 2) and m:read_u16(wv.a) or m:read_u32(wv.a)
      if v ~= wv.v then out:write(string.format("B %06x %x\n", wv.a, v)); wv.v = v end
    end
    for _, g in ipairs(gfx) do
      local h, t = fnv_region(g.a, g.len)
      if h ~= g.h then
        local nchg = 0
        if g.last then for i = 1, #t do if t[i] ~= g.last[i] then nchg = nchg + 1 end end end
        out:write(string.format("G %s %08x %d\n", g.name, h, nchg))
        g.h = h; g.last = t
      end
    end
    if f % 50 == 0 then out:flush() end
  end
  if shots[rel] then L.screen:snapshot(string.format("%s_%04d.png", tag, rel)) end
  if rel >= stop then out:close(); manager.machine:exit() end
end)
