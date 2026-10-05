-- recdump.lua: after FF_LOAD, write per frame (end of frame) the 192-byte records of Cody ($ff8568) and Bred ($ff8fe8)
-- plus the 8 bytes $ff8000..$ff8007, as frame number (u32 BE) + 8 + 192 + 192 bytes, to FF_REC_OUT.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_REC_OUT") or "rec.bin", "wb"))
local m = L.mem
local function blk(a, n)
  local t = {}
  for i = 0, n - 1, 2 do local v = m:read_u16(a + i); t[#t + 1] = string.char(v >> 8, v & 0xff) end
  return table.concat(t)
end
-- FF_PRESS="2210-2213,2230-2233": hold Button 1 on those frames (level set at the end of frame N is read from N+1)
local press = {}
for a, b in string.gmatch(os.getenv("FF_PRESS") or "", "(%d+)-(%d+)") do press[#press + 1] = { tonumber(a), tonumber(b) } end
emu.register_frame_done(function()
  local f = L.frame()
  local v = 0
  for _, p in ipairs(press) do if f >= p[1] and f < p[2] then v = 1 end end
  if #press > 0 then L.F.b1:set_value(v) end
  if f >= 2201 then
    out:write(string.char((f >> 24) & 255, (f >> 16) & 255, (f >> 8) & 255, f & 255), blk(0xff8000, 8), blk(0xff8568, 192), blk(0xff8fe8, 192))
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
