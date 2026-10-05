-- pvp.lua: load a two-player state, apply a plan (frames relative to the load, fields of both players), poke, and log both player records every frame.
--   FF_LOAD state name; FF_PLAN plan file {{rel, field, level}...}; FF_POKES file {{rel, addr, size, value}...}; FF_N frames; FF_LOG log file
--   FF_KILL=1 clears the in-use byte of every pool-2 record at the start (and every frame while FF_KILLALL=1)
--   FF_EXTRA file returning function(f, rel, m, out)
-- Line: "<rel> | P1 st sub ss s5 hp/hp26 b44 b45 b22 b23 b60 b62 b63 b97 b148 b160 b64 b66 b104 b139 b137 b136 x gy y vx vy sc | P2 ... "
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local out = os.getenv("FF_OUT")
local N = tonumber(os.getenv("FF_N") or "600")
local plan = os.getenv("FF_PLAN") and dofile(os.getenv("FF_PLAN")) or {}
local pokes = os.getenv("FF_POKES") and dofile(os.getenv("FF_POKES")) or {}
local extra = os.getenv("FF_EXTRA") and dofile(os.getenv("FF_EXTRA")) or nil
local log = io.open(os.getenv("FF_LOG") or (out .. "/pvp.log"), "w")
local loaded, f0 = false, nil
local u8, u16, u32 = function(a) return m:read_u8(a) end, function(a) return m:read_u16(a) end, function(a) return m:read_u32(a) end
local FIELDS = { { "b0", 0, 1 }, { "st", 2, 1 }, { "sub", 3, 1 }, { "ss", 4, 1 }, { "s5", 5, 1 }, { "hp", 24, 2 }, { "h26", 26, 2 }, { "b44", 44, 1 }, { "b45", 45, 1 }, { "b22", 22, 1 }, { "b23", 23, 1 },
  { "b60", 60, 2 }, { "b62", 62, 1 }, { "b63", 63, 1 }, { "b97", 97, 1 }, { "b148", 148, 1 }, { "b160", 160, 1 }, { "b64", 64, 1 }, { "b66", 66, 1 }, { "b104", 104, 1 }, { "b139", 139, 1 },
  { "b136", 136, 1 }, { "b137", 137, 1 }, { "b46", 46, 1 }, { "x", 6, 2 }, { "gy", 14, 2 }, { "y", 10, 2 }, { "vx", 80, 2 }, { "vy", 84, 2 }, { "sc", 132, 4 }, { "c20", 20, 1 }, { "b54", 54, 1 }, { "b154", 154, 1 }, { "b1", 1, 1 } }
local function rec(P)
  local t = {}
  for _, f in ipairs(FIELDS) do
    local v = f[3] == 1 and u8(P + f[2]) or f[3] == 2 and u16(P + f[2]) or u32(P + f[2])
    t[#t + 1] = string.format("%s=%x", f[1], v)
  end
  return table.concat(t, " ")
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(os.getenv("FF_LOAD")); return end
  if not f0 then
    f0 = f
    if os.getenv("FF_KILL") == "1" then for i = 0, 12 do m:write_u8(0xff86e8 + 0xc0 * i, 0) end end
  end
  local rel = f - f0
  if os.getenv("FF_KILLALL") == "1" then for i = 0, 12 do m:write_u8(0xff86e8 + 0xc0 * i, 0) end end
  if os.getenv("FF_CLR148") == "1" then m:write_u8(0xff8568 + 148, 0); m:write_u8(0xff8628 + 148, 0) end
  local t = {}
  for _, e in ipairs(plan) do t[#t + 1] = { f0 + e[1], e[2], e[3] } end
  L.apply(t, f)
  for _, p in ipairs(pokes) do
    if p[1] == rel then
      if p[3] == 1 then m:write_u8(p[2], p[4]) elseif p[3] == 2 then m:write_u16(p[2], p[4]) else m:write_u32(p[2], p[4]) end
    end
  end
  log:write(string.format("%d | %s | %s | 22195=%02x 290=%02x 21610=%02x 127=%02x i92=%02x i94=%02x i130a=%02x i130b=%02x i131a=%02x i131b=%02x w1=%04x/%04x w2=%04x/%04x\n", rel, rec(0xff8568), rec(0xff8628), u8(0xff8000 + 22195), u8(0xff8000 + 290),
    u8(0xff8000 + 21610), u8(0xff8000 + 127), u8(0xff8000 + 92), u8(0xff8000 + 94), u8(0xff8568 + 130), u8(0xff8628 + 130), u8(0xff8568 + 131), u8(0xff8628 + 131), u16(0xff8000 + 21256), u16(0xff8000 + 21258), u16(0xff8000 + 21360), u16(0xff8000 + 21362)))
  if extra then extra(f, rel, m, log) end
  for a in string.gmatch(os.getenv("FF_SHOTS") or "", "%d+") do if tonumber(a) == rel then L.screen:snapshot(string.format("pvp_%s_%04d.png", os.getenv("FF_TAG") or "x", rel)) end end
  if rel >= N then log:close(); manager.machine:exit() end
end)
