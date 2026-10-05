-- extra_hag.lua (pdrive.lua FF_EXTRA): as extra_dummy3.lua, plus write taps logged to $HAG_TAPS:
--   the dummy (pool-2 record FF_DUMMY) health words +24/+26 (pc, value), the shaker flag/record words ($ff12f0-$ff12f5), camera y 1046(A5), the shaker record +2/+96 when live.
local base = dofile(os.getenv("PD") .. "/extra_dummy3.lua")
local idx = tonumber(os.getenv("FF_DUMMY") or "12")
local tf = assert(io.open(os.getenv("HAG_TAPS"), "w"))
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local mm = L.mem
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
local a = 0xff86e8 + 0xc0 * idx
taps = {}
local function tap(lo, hi, name)
  taps[#taps + 1] = mm:install_write_tap(lo, hi, name, function(off, data, mask) tf:write(string.format("f=%d pc=%06x %s a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, name, off, mask, data)) end)
end
tap(a + 24, a + 25, "hp"); tap(a + 26, a + 27, "hp26"); tap(a + 2, a + 3, "st")
tap(0xff12f0, 0xff12f5, "shk"); tap(0xff8416, 0xff8417, "camy")
tap(0xff8568 + 24, 0xff8568 + 25, "p1hp")
return function(f, rel, m, out) tf:flush(); return base(f, rel, m, out) end
