-- kernel_log.lua: run the scripted drive (ffdrive.lua) with a write tap on the task kernel's RAM
-- ($ff1000-$ff11ff: sixteen TCBs, current-task pointer $ff1106, VBL flag $ff1100) and log every write
-- with the PC that made it, the frame and the scanline. No debugger needed (ffrun.sh).
--   FF_KLOG_LO/FF_KLOG_HI  frame window to log (default 1000..2200)
--   FF_KLOG_OUT            output file (default <FF_OUT>/kernel_log.txt)
-- Line: "f=<frame> v=<scanlines after the last frame_done> pc=<CURPC> a=<addr> m=<mask> d=<data>"
-- (the bus is 16 bits wide: mask $ff00 is the even byte only, $00ff the odd byte only)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local lo = tonumber(os.getenv("FF_KLOG_LO") or "1000")
local hi = tonumber(os.getenv("FF_KLOG_HI") or "2200")
local path = os.getenv("FF_KLOG_OUT") or (out .. "/kernel_log.txt")
local fh = assert(io.open(path, "w"))
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local scr = L.screen
local function line() -- scanlines since the last multiple of the frame period (frame_done fires at phase 0)
  local t = manager.machine.time:as_double()
  return ((t % scr.frame_period) / scr.scan_period)
end
local function log(kind, offset, data, mask)
  local fr = L.frame()
  if fr < lo or fr > hi then return end
  fh:write(string.format("f=%d v=%.1f pc=%06x %s a=%06x m=%04x d=%04x\n", fr, line(), pcreg.value,
    kind, offset, mask, data))
end
-- keep the handle in a global: a tap that is garbage collected is silently removed (ffdrive allocates
-- enough to trigger a collection, a short probe does not)
kernel_tap = L.mem:install_write_tap(0xff1000, 0xff11ff, "kernel", function(offset, data, mask)
  local ok, e = pcall(log, "w", offset, data, mask)
  if not ok then print("KLOG ERROR " .. tostring(e)) end
end)
-- FF_KLOG_EXTRA="ff8000-ff8001,ff1288-ff1289": more word ranges to tap, logged as kind "x"
extra_taps = {}
for a, b in string.gmatch(os.getenv("FF_KLOG_EXTRA") or "", "(%x+)-(%x+)") do
  extra_taps[#extra_taps + 1] = L.mem:install_write_tap(tonumber(a, 16), tonumber(b, 16), "extra" .. a,
    function(offset, data, mask)
      local ok, e = pcall(log, "x", offset, data, mask)
      if not ok then print("KLOG ERROR " .. tostring(e)) end
    end)
end
emu.register_frame_done(function()
  local fr = L.frame()
  if fr >= lo and fr <= hi then fh:write(string.format("f=%d FRAME_DONE v=%.1f pc=%06x\n", fr, line(), pcreg.value)) end
  if fr >= hi then fh:close() end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
