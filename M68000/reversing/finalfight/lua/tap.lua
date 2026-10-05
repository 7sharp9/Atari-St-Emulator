-- tap.lua: write AND read taps on word ranges with PC and frame, then run ffdrive.lua (honours FF_LOAD, FF_STOP...).
--   FF_W="ff8580-ff8585,ff9000-ff9005"  write taps      FF_R="..." read taps
--   FF_TAP_OUT  output file;  FF_TAP_LO/HI frame window
-- Line: "f=<frame> pc=<CURPC> w|r a=<addr> m=<mask> d=<data>"
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local lo = tonumber(os.getenv("FF_TAP_LO") or "0")
local hi = tonumber(os.getenv("FF_TAP_HI") or "99999")
local fh = assert(io.open(os.getenv("FF_TAP_OUT") or (os.getenv("FF_OUT") .. "/tap.txt"), "w"))
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local function log(kind, offset, data, mask)
  local fr = L.frame()
  if fr < lo or fr > hi then return end
  fh:write(string.format("f=%d pc=%06x %s a=%06x m=%04x d=%04x\n", fr, pcreg.value, kind, offset, mask, data))
end
taps = {}
for kind, env in pairs({ w = "FF_W", r = "FF_R" }) do
  for a, b in string.gmatch(os.getenv(env) or "", "(%x+)-(%x+)") do
    local f = function(offset, data, mask) local ok, e = pcall(log, kind, offset, data, mask); if not ok then print("TAP ERR " .. tostring(e)) end end
    if kind == "w" then taps[#taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, f)
    else taps[#taps + 1] = L.mem:install_read_tap(tonumber(a, 16), tonumber(b, 16), "r" .. a, f) end
  end
end
local hiF = hi
emu.register_frame_done(function() if L.frame() >= hiF then fh:flush() end end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
