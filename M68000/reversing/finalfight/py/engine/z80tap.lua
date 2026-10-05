-- z80tap.lua: pass-5 agent B. Cold boot (ffdrive.lua) with taps on the sound CPU: writes to the YM2151 ($f000 address, $f001 data), the OKI ($f002), the bank/pin registers ($f004/$f006),
-- reads of the latches ($f008 command, $f00a timer), and the 68000 latch writes ($800180/$800188). Lines: "f=<frame> t=<cpu 0|1> ... ". Output FF_TAP_OUT.
-- Then runs ffdrive.lua (FF_STOP, FF_PLAN, FF_LOAD as there) or stagebot.lua when FF_STAGEBOT=1.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local fh = assert(io.open(os.getenv("FF_TAP_OUT"), "w"))
local lo = tonumber(os.getenv("FF_TAP_LO") or "0")
local hi = tonumber(os.getenv("FF_TAP_HI") or "99999999")
local zcpu = manager.machine.devices[":audiocpu"]
local zspace = zcpu.spaces["program"]
local zpc = zcpu.state["CURPC"]
local mpc = manager.machine.devices[":maincpu"].state["CURPC"]
local function ok() local f = L.frame(); return f >= lo and f <= hi end
local ymaddr = 0
taps = {}
taps[#taps + 1] = zspace:install_write_tap(0xf000, 0xf001, "ym", function(off, data, mask)
  if not ok() then return end
  if off == 0xf000 then ymaddr = data & 0xff; if mask & 0xff00 ~= 0 then end end
  fh:write(string.format("f=%d Z ym a=%04x d=%02x m=%02x pc=%04x\n", L.frame(), off, data & 0xff, mask, zpc.value))
end)
taps[#taps + 1] = zspace:install_write_tap(0xf002, 0xf007, "oki", function(off, data, mask)
  if not ok() then return end
  fh:write(string.format("f=%d Z w a=%04x d=%02x pc=%04x\n", L.frame(), off, data & 0xff, zpc.value))
end)
taps[#taps + 1] = zspace:install_read_tap(0xf008, 0xf00b, "latch", function(off, data, mask)
  if not ok() then return end
  fh:write(string.format("f=%d Z r a=%04x d=%02x pc=%04x\n", L.frame(), off, data & 0xff, zpc.value))
end)
taps[#taps + 1] = L.mem:install_write_tap(0x800180, 0x800189, "lat68", function(off, data, mask)
  if not ok() then return end
  fh:write(string.format("f=%d M w a=%06x d=%04x m=%04x pc=%06x\n", L.frame(), off, data, mask, mpc.value))
end)
local n = 0
emu.register_frame_done(function() n = n + 1; if n % 300 == 0 then fh:flush() end end)
if os.getenv("FF_STAGEBOT") == "1" then dofile(os.getenv("FF_DIR") .. "/stagebot.lua") else dofile(os.getenv("FF_DIR") .. "/ffdrive.lua") end
