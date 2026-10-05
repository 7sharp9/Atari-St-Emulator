-- pcprobe.lua: wraps fdrive.lua, logs CURPC and A6/D7 at the end of each frame in [FF_PC_LO, FF_PC_HI] to FF_PC_OUT
local cpu = manager.machine.devices[":maincpu"]
local out = assert(io.open(os.getenv("FF_PC_OUT") or "pc.txt", "w"))
local lo, hi = tonumber(os.getenv("FF_PC_LO") or "0"), tonumber(os.getenv("FF_PC_HI") or "0")
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
emu.register_frame_done(function()
  local f = L.frame()
  if f >= lo and f <= hi then
    out:write(string.format("f=%d pc=%06x a6=%08x a4=%08x d0=%08x d7=%08x sr=%04x\n", f, cpu.state["CURPC"].value, cpu.state["A6"].value, cpu.state["A4"].value, cpu.state["D0"].value, cpu.state["D7"].value, cpu.state["SR"].value))
  end
  if f >= hi then out:flush() end
end)
dofile(os.getenv("FF_AI123") .. "/fdrive.lua")
