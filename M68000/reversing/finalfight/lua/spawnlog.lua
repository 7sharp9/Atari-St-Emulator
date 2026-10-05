-- spawnlog.lua: after FF_LOAD, hold Right from FF_WALK_LO..FF_WALK_HI (+ Button 1 pulses), log every write to word +0 (bytes +0,+1)
-- of each 192-byte record in $ff8568..$ffb1a7 and to the 64-byte special records ($ffb1a8..$ffb2ff, words at +0 of each 64 bytes):
--   "f=<frame> pc=<pc> a=<addr> d=<data>"      FF_SP_OUT = file; FF_STOP end frame
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_SP_OUT") or "spawn.txt", "w"))
local m = L.mem
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
local lo, hi = tonumber(os.getenv("FF_WALK_LO") or "2480"), tonumber(os.getenv("FF_WALK_HI") or "9999")
local function logw(offset, data, mask)
  local rel = offset - 0xff8568
  local ok
  if offset < 0xffb1a8 then ok = (rel % 192) < 4 else ok = ((offset - 0xffb1a8) % 64) < 4 end
  if ok then out:write(string.format("f=%d pc=%06x a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, offset, mask, data)) end
end
tapA = m:install_write_tap(0xff8568, 0xffb2ff, "recs", logw)
emu.register_frame_done(function()
  local f = L.frame()
  L.F.right:set_value((f >= lo and f < hi) and 1 or 0)
  L.F.b1:set_value((f >= lo and f % 40 < 4) and 1 or 0)
  if f >= 2200 then out:write(string.format("f=%d CAM x=%04x y=%04x s1ffb1e8=%02x%02x scriptptr=%04x%04x\n", f, m:read_u16(0xff8412), m:read_u16(0xff8416),
    m:read_u8(0xffb1ea), m:read_u8(0xffb1eb), m:read_u16(0xffb1ee), m:read_u16(0xffb1f0))) end
  if f % 200 == 0 then out:flush() end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
