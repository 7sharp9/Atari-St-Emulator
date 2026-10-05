-- hpbar.lua: per frame, log Cody's record words +24/+26/+28 ($ff8580/82/84), Bred's +24/+26/+28 ($ff9000/02/04),
-- and the HUD tile codes of the P1 bar column ($908590 + 128*k) and the second HUD row ($908598 + 128*k), k=0..19.
-- Run: FF_LOAD=ff_gameplay FF_STOP=<n> FF_HP_OUT=<file> ffrun_a.sh <this>   (wraps ffdrive.lua)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_HP_OUT") or "hpbar.txt", "w"))
local m = L.mem
local function row(base)
  local t = {}
  for k = 0, 19 do t[#t + 1] = string.format("%04x", m:read_u16(base + 128 * k)) end
  return table.concat(t, ",")
end
local press = {}
for a, b in string.gmatch(os.getenv("FF_PRESS") or "", "(%d+)-(%d+)") do press[#press + 1] = { tonumber(a), tonumber(b) } end
emu.register_frame_done(function()
  local f = L.frame()
  local v = 0
  for _, p in ipairs(press) do if f >= p[1] and f < p[2] then v = 1 end end
  if #press > 0 then L.F.b1:set_value(v) end
  out:write(string.format("f=%d cody=%04x,%04x,%04x bred=%04x,%04x,%04x r0=%s r2=%s\n", f,
    m:read_u16(0xff8580), m:read_u16(0xff8582), m:read_u16(0xff8584),
    m:read_u16(0xff9000), m:read_u16(0xff9002), m:read_u16(0xff9004), row(0x908590), row(0x908598)))
  out:flush()
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
