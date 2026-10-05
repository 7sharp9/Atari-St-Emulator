-- ramdump.lua: load FF_LOAD, let the load apply (3 frame callbacks, no game frame runs in between that the state does not contain), write work RAM to FF_RAMOUT and exit
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local n = 0
emu.register_frame_done(function()
  n = n + 1
  if n == 2 then
    L.write(os.getenv("FF_RAMOUT"), L.ram())
    manager.machine:exit()
  end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
