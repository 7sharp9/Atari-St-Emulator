-- ptap.lua: write/read taps (FF_W / FF_R word ranges, hex "lo-hi,lo-hi") then run pdrive.lua.  PD = this directory.
-- Line: "f=<frame> rel pc=<CURPC> w|r a=<addr> m=<mask> d=<data>"  to FF_TAP_OUT
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local fh = assert(io.open(os.getenv("FF_TAP_OUT") or (os.getenv("FF_OUT") .. "/ptap.txt"), "w"))
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local function log(kind, offset, data, mask)
  fh:write(string.format("f=%d pc=%06x %s a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, kind, offset, mask, data))
end
taps = {}
for kind, env in pairs({ w = "FF_W", r = "FF_R" }) do
  for a, b in string.gmatch(os.getenv(env) or "", "(%x+)-(%x+)") do
    local f = function(offset, data, mask) local ok, e = pcall(log, kind, offset, data, mask); if not ok then print("TAP ERR " .. tostring(e)) end end
    if kind == "w" then taps[#taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, f)
    else taps[#taps + 1] = L.mem:install_read_tap(tonumber(a, 16), tonumber(b, 16), "r" .. a, f) end
  end
end
emu.register_frame_done(function() fh:flush() end)
dofile(os.getenv("PD") .. "/pdrive.lua")
