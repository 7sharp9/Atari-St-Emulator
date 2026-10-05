-- pdrive.lua: load a saved state, apply an input plan (frames relative to the loaded frame), log the player
-- record every frame. Run through ffrun.sh (FF_DIR = reversing/finalfight/lua).
--   FF_LOAD=<state>      (default ff_enemies)         FF_PLAN=<plan.lua>  returns { {rel, field, level}, ... }
--   FF_POKES=<file.lua>  returns { {rel, addr, size(1|2|4), value}, ... } applied before frame rel runs
--   FF_KILL=1            clear the in-use byte of every tag-2 record at the start (no enemies)
--   FF_N=<frames>        frames to run (default 600)    FF_LOG=<file> (default <FF_OUT>/pd_log.txt)
--   FF_P=<record addr>   player record (default 0xff8568, P1)
--   FF_EXTRA=<file.lua>  returns function(f, rel, mem, out) called every frame for extra logging
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local P = tonumber(os.getenv("FF_P") or "0xff8568")
local N = tonumber(os.getenv("FF_N") or "600")
local loadname = os.getenv("FF_LOAD") or "ff_enemies"
local plan = os.getenv("FF_PLAN") and dofile(os.getenv("FF_PLAN")) or {}
local pokes = os.getenv("FF_POKES") and dofile(os.getenv("FF_POKES")) or {}
local extra = os.getenv("FF_EXTRA") and dofile(os.getenv("FF_EXTRA")) or nil
local log = io.open(os.getenv("FF_LOG") or (out .. "/pd_log.txt"), "w")
local loaded, f0 = false, nil
local u8, u16, u32 = function(a) return m:read_u8(a) end, function(a) return m:read_u16(a) end, function(a) return m:read_u32(a) end
local function s16(v) if v >= 0x8000 then return v - 0x10000 end return v end
local function line(f, rel)
  log:write(string.format("%d %d st=%02x sub=%02x ss=%02x s5=%02x m66=%02x b44=%02x b45=%02x b54=%02x b46=%02x x=%04x y=%04x gy=%04x hp=%04x/%04x in=%02x pv=%02x b22=%02x b23=%02x b62=%02x b63=%02x b64=%02x b40=%02x b41=%02x b30=%02x b97=%02x b74=%02x b99=%02x b142=%02x b148=%02x b151=%02x b154=%02x b160=%02x b161=%02x b164=%02x b165=%02x b166=%02x b169=%02x vx=%04x/%04x vy=%04x/%04x sc=%04x lv=%02x p56=%06x scH=%04x b104=%02x b105=%02x b149=%02x b150=%02x b152=%02x b153=%02x b162=%04x b20=%02x b137=%02x b1=%02x b139=%02x b136=%02x b140=%02x b23=%02x b144=%02x thr=%04x\n",
    f, rel, u8(P + 2), u8(P + 3), u8(P + 4), u8(P + 5), u8(P + 66), u8(P + 44), u8(P + 45), u8(P + 54), u8(P + 46), u16(P + 6), u16(P + 10), u16(P + 14),
    u16(P + 24), u16(P + 28), u8(P + 130), u8(P + 131), u8(P + 22), u8(P + 23), u8(P + 62), u8(P + 63), u8(P + 64), u8(P + 40), u8(P + 41), u8(P + 30), u8(P + 97), u8(P + 74), u8(P + 99),
    u8(P + 142), u8(P + 148), u8(P + 151), u8(P + 154), u8(P + 160), u8(P + 161), u8(P + 164), u8(P + 165), u8(P + 166), u8(P + 169),
    u16(P + 80), u16(P + 82), u16(P + 84), u16(P + 86), u16(P + 134), u8(P + 128), u32(P + 56) & 0xffffff, u16(P + 132), u8(P + 104), u8(P + 105), u8(P + 149), u8(P + 150), u8(P + 152), u8(P + 153), u16(P + 162), u8(P + 20), u8(P + 137), u8(P + 1), u8(P + 139), u8(P + 136), u8(P + 140), u8(P + 23), u8(P + 144), u16(P + 146)))
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then
    loaded = true
    manager.machine:load(loadname)
    return
  end
  if not f0 then
    f0 = f
    if os.getenv("FF_KILL") == "1" then
      local keep = {}
      for k in string.gmatch(os.getenv("FF_KEEP") or "", "%d+") do keep[tonumber(k)] = true end
      for i = 0, 12 do local a = 0xff86e8 + 0xc0 * i; if not keep[i] then m:write_u8(a, 0) end end
      if os.getenv("FF_EHP") then
        local hp = tonumber(os.getenv("FF_EHP"), 16)
        for k in pairs(keep) do if k <= 12 then local a = 0xff86e8 + 0xc0 * k; m:write_u16(a + 24, hp); m:write_u16(a + 26, hp); m:write_u16(a + 28, hp) end end
      end
    end
  end
  local rel = f - f0
  L.apply((function() local t = {} for _, e in ipairs(plan) do t[#t + 1] = { f0 + e[1], e[2], e[3] } end return t end)(), f)
  for _, p in ipairs(pokes) do
    if p[1] == rel then
      if p[3] == 1 then m:write_u8(p[2], p[4]) elseif p[3] == 2 then m:write_u16(p[2], p[4]) else m:write_u32(p[2], p[4]) end
    end
  end
  local heal = tonumber(os.getenv("FF_HEAL") or "0")
  if heal > 0 and rel % heal == 0 and rel > 0 and u16(P + 24) < 0x80 and u8(P + 2) == 2 then m:write_u16(P + 24, 0x90); m:write_u16(P + 26, 0x90) end
  if os.getenv("FF_GOD") == "1" then m:write_u8(P + 97, 0xff) end
  line(f, rel)
  local sl, sh, ss = tonumber(os.getenv("FF_SHOT_LO") or "-1"), tonumber(os.getenv("FF_SHOT_HI") or "-2"), tonumber(os.getenv("FF_SHOT_STEP") or "1")
  if rel >= sl and rel <= sh and (rel - sl) % ss == 0 then L.screen:snapshot(string.format("%s_%05d.png", os.getenv("FF_SHOT_TAG") or "pd", rel)) end
  if extra then extra(f, rel, m, log) end
  if rel >= N then log:close(); manager.machine:exit() end
end)
