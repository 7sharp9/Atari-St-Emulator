-- forcespawn.lua: load a level state, poke one pool B/C record of a given type next to / on top of the player, run, and log.
--   env: CB_STATE (state name under CB_RUN/sta/cbuster, e.g. lv0), CB_POOL (B|C), CB_TYPES "0-83" or "1,5,9", CB_MODES "free,on"
--        CB_FRAMES (run length, default 120), CB_VAR (variant byte, default 0), CB_OUT, CB_SHOTS "4,30,100" (frames to screenshot)
--   log lines: CASE pool type mode var | R n hex(record) | N n pool slot hex | D n (record died) | P n score1 hp1 lives1 score2 hp2 (on change)
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local state = os.getenv("CB_STATE") or "lv0"
local pool = os.getenv("CB_POOL") or "B"
local frames = tonumber(os.getenv("CB_FRAMES") or "120")
local var = tonumber(os.getenv("CB_VAR") or "0")
local tag = os.getenv("CB_TAG") or (state .. "_" .. pool)
local out = io.open((os.getenv("CB_OUT") or ".") .. "/force_" .. tag .. ".txt", "w")
local function parse(s, default)
  local t = {}
  for a, b in (s or default):gmatch("(%d+)%-?(%d*)") do
    local lo, hi = tonumber(a), tonumber(b ~= "" and b or a)
    for i = lo, hi do t[#t + 1] = i end
  end
  return t
end
local types = parse(os.getenv("CB_TYPES"), pool == "B" and "0-83" or "0-43")
local modes = {}
for w in (os.getenv("CB_MODES") or "free,on"):gmatch("%a+") do modes[#modes + 1] = w end
local shots = {}
for n in (os.getenv("CB_SHOTS") or "4,40"):gmatch("%d+") do shots[tonumber(n)] = true end
local cases = {}
if os.getenv("CB_CASES") then -- "43:0,43:1,49:2": type:variant
  for t, v in os.getenv("CB_CASES"):gmatch("(%d+):(%d+)") do for _, md in ipairs(modes) do cases[#cases + 1] = { tonumber(t), md, tonumber(v) } end end
else
  for _, t in ipairs(types) do for _, md in ipairs(modes) do cases[#cases + 1] = { t, md, var } end end
end
local base, stride, cnt = 0x81400, 0x40, 32
if pool == "C" then base, stride, cnt = 0x81c00, 0x20, 8 end
if pool == "A" then base, stride, cnt = 0x81000, 0x40, 16 end
local slot = (pool == "B") and 12 or ((pool == "A") and 9 or 3)
local ci, phase, n = 1, "load", 0
local act = {}
local prevp
local function recs() -- activation snapshot of all pools
  local r = {}
  for p, d in ipairs({ { 0x81000, 0x40, 16 }, { 0x81400, 0x40, 32 }, { 0x81c00, 0x20, 8 } }) do
    for i = 0, d[3] - 1 do r[#r + 1] = (m:read_u8(d[1] + d[2] * i) & 0x80) ~= 0 end
  end
  return r
end
local function hexrec(a, len) local t = {} for i = 0, len - 1 do t[#t + 1] = string.format("%02x", m:read_u8(a + i)) end return table.concat(t) end
local function reset_watch() act = recs() end
local died, lastr
emu.register_frame_done(function()
  if ci > #cases then out:close(); manager.machine:exit(); return end
  if phase == "load" then
    manager.machine:load(state); phase = "settle"; n = 0; return
  end
  n = n + 1
  local c = cases[ci]
  if phase == "settle" then
    if n < 3 then return end
    local sx = m:read_u16(0x8040a)
    local px, py = m:read_u16(0x80108), m:read_u16(0x8010c)
    local a = base + stride * slot
    for i = 0, stride - 1 do m:write_u8(a + i, 0) end
    if c[1] ~= 255 then m:write_u8(a, 0x80); m:write_u8(a + 2, c[1]) end
    local x, y
    if os.getenv("CB_HP") then m:write_u8(0x80113, tonumber(os.getenv("CB_HP"))) end
    local face = m:read_u8(0x80107)
    if c[2] == "free" then x, y = sx + 0xc0, py
    elseif c[2] == "hit" or c[2] == "hit2" then x, y = px + (face == 0 and 0x1c or -0x1c), py
    else x, y = px, py end
    if c[1] ~= 255 then m:write_u16(a + 8, x); m:write_u16(a + 12, y)
      if pool == "A" then m:write_u8(a + 16, c[3]); m:write_u32(a + 60, 0x80100)
      elseif pool == "B" then m:write_u8(a + 16, c[3]) else m:write_u32(a + 28, 0x80100) end end
    out:write(string.format("CASE %s %d %s var=%d sx=%04x p=%04x,%04x at=%04x,%04x lvl=%d\n", pool, c[1], c[2], c[3], sx, px, py, x, y, m:read_u8(0x80046)))
    reset_watch(); died = false; lastr = nil
    prevp = nil
    phase = "run"; n = 0
    return
  end
  -- run
  if string.sub(c[2], 1, 3) == "hit" then
    local w = (n % 20) >= 5 and (n % 20) < 10 and n >= 5
    L.F.b1:set_value(w and 1 or 0)
    if c[2] == "hit2" then L.F.b2:set_value(w and 1 or 0) end
  end
  local a = base + stride * slot
  local on = (m:read_u8(a) & 0x80) ~= 0
  if n == 1 or n == 3 or n == 8 or n == 20 or n == 45 or n == 80 or n == frames then
    local h = hexrec(a, stride); if h ~= lastr then out:write(string.format("R %d %s\n", n, h)); lastr = h end
  end
  if (not on) and not died then died = true; out:write(string.format("D %d\n", n)) end
  -- children
  local now = recs()
  local k = 0
  for p, d in ipairs({ { 0x81000, 0x40, 16, "A" }, { 0x81400, 0x40, 32, "B" }, { 0x81c00, 0x20, 8, "C" } }) do
    for i = 0, d[3] - 1 do
      k = k + 1
      if now[k] and not act[k] and not (d[4] == pool and (d[1] + d[2] * i) == a) then
        out:write(string.format("N %d %s %d %s\n", n, d[4], i, hexrec(d[1] + d[2] * i, d[2])))
      end
    end
  end
  act = now
  local sc1, hp1, sc2, hp2 = m:read_u32(0x8013c), m:read_u8(0x80113), m:read_u32(0x801bc), m:read_u8(0x80193)
  local key = string.format("%08x %02x %02x %08x %02x", sc1, hp1, m:read_u8(0x80114), sc2, hp2)
  if key ~= prevp then out:write(string.format("P %d %s\n", n, key)); prevp = key end
  if shots[n] then L.screen:snapshot(string.format("fs_%s_%s%d_v%d_%s_%d.png", state, pool, c[1], c[3], c[2], n)) end
  if n >= frames then ci = ci + 1; phase = "load"; L.F.b1:set_value(0); L.F.b2:set_value(0) end
end)
