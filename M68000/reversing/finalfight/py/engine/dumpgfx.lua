-- dumpgfx.lua: load a state (DG_LOAD), run DG_N frames, write gfx RAM $900000-$92ffff (DG_OUT) and the work RAM ($ff0000-$ffffff, DG_OUT .. ".ram"); exit.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local loaded, base = false, nil
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(os.getenv("DG_LOAD")); return end
  base = base or f
  if f - base >= tonumber(os.getenv("DG_N") or "0") then
    L.write(os.getenv("DG_OUT"), L.region(0x900000, 0x30000))
    L.write(os.getenv("DG_OUT") .. ".ram", L.ram())
    manager.machine:exit()
  end
end)
