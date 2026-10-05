-- resume_check.lua: load a saved state (FF_LOAD, default ff_gameplay) from cold boot, then write the work RAM
-- after each of the next 7 frames to <FF_OUT>/resume_frames.bin and the screen frame numbers to resume_frames.txt
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local name = os.getenv("FF_LOAD") or "ff_gameplay"
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local bin = io.open(out .. "/resume_frames.bin", "wb")
local txt = io.open(out .. "/resume_frames.txt", "w")
local issued, n = false, 0
emu.register_frame_done(function()
  local f = L.frame()
  if not issued then
    issued = true
    txt:write(string.format("load issued at callback frame %d\n", f))
    manager.machine:load(name)
    return
  end
  bin:write(L.ram())
  txt:write(string.format("callback frame_number=%d x=%04x credit=%02x\n", f, L.mem:read_u16(0xff856e), L.mem:read_u8(0xff804d)))
  n = n + 1
  if n == 1 then L.screen:snapshot("resume_first.png") end
  if n >= 7 then bin:close(); txt:close(); manager.machine:exit() end
end)
