-- drive.lua: input-scheduled drive from a cold boot (or CB_LOAD state), with screenshots and RAM dumps.
--   CB_DIR   directory of this lua/ folder (the wrapper of the caller sets it)
--   CB_PLAN  file returning a list of {frame, field, level}; levels are read by the game once per frame,
--            a level set at the end of frame N is what the game sees from N+1 (hold several frames)
--   CB_SHOTS "lo:hi:step" screenshots into the run dir's snap/ ; CB_DUMP "f1,f2,.." work RAM dumps to CB_OUT
--   CB_SAVE  state name saved at CB_SAVE_FRAME ; CB_LOAD state name loaded at frame 1 ; CB_STOP last frame
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local out = os.getenv("CB_OUT") or "."
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local slo, shi, sst = 0, -1, 1
if os.getenv("CB_SHOTS") then slo, shi, sst = os.getenv("CB_SHOTS"):match("(%d+):(%d+):(%d+)"); slo, shi, sst = tonumber(slo), tonumber(shi), tonumber(sst) end
local dump = {}
for n in (os.getenv("CB_DUMP") or ""):gmatch("%d+") do dump[tonumber(n)] = true end
local loaded = false
emu.register_frame_done(function()
  local f = L.frame()
  if os.getenv("CB_LOAD") and not loaded then loaded = true; manager.machine:load(os.getenv("CB_LOAD")); return end
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  if f >= slo and f <= shi and (f - slo) % sst == 0 then L.screen:snapshot(string.format("f%05d.png", f)) end
  if dump[f] then L.write(string.format("%s/ram_%05d.bin", out, f), L.ram()) end
  if os.getenv("CB_SAVE") and f == tonumber(os.getenv("CB_SAVE_FRAME")) then manager.machine:save(os.getenv("CB_SAVE")) end
  if f >= stop then manager.machine:exit() end
end)
