-- ladderlab.lua: position sweep. Load CB_STATE, then for every (x, y) of CB_XS x CB_YS (space separated lists) reload it, poke P1's position (+8 and +12 words),
--   hold CB_PLAN (default down) for 40 frames and write one line: the poked position, then x, y, action, sub-action, pose, +57 and the scroll y afterwards.
--   A sub-action of 7 with a changed y means the press entered a ladder. Level 4 descent (state saved at the stall at x 1520): y 448 and x 1502..1506 enter it,
--   1501 falls (sub-action 6), 1497..1500 and 1507..1510 do nothing (`player/natural.md`).
--   Needs CB_DIR, CB_OUT, a large seconds_to_run (the saved frame counts from machine start).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/ladderlab.txt", "w")
local xs, ys = {}, {}
for v in (os.getenv("CB_XS")):gmatch("%d+") do xs[#xs + 1] = tonumber(v) end
for v in (os.getenv("CB_YS")):gmatch("%d+") do ys[#ys + 1] = tonumber(v) end
local plan = os.getenv("CB_PLAN") or "down"
local trials = {}
for _, y in ipairs(ys) do for _, x in ipairs(xs) do trials[#trials + 1] = { x, y } end end
local k, phase, t0, loaded = 0, "load", nil, false
local p = 0x80100
emu.register_frame_done(function()
  local f = L.frame()
  m:write_u8(0x80113, 0x38)
  if phase == "load" then
    k = k + 1; if k > #trials then out:close(); manager.machine:exit() return end
    manager.machine:load(os.getenv("CB_STATE")); phase = "poke"; t0 = nil; return
  end
  if t0 == nil then t0 = f end
  local d = f - t0
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  if phase == "poke" then
    if d == 2 then m:write_u16(p + 8, trials[k][1]); m:write_u16(p + 12, trials[k][2]) end
    if d >= 8 then phase = "run"; t0 = f end
    return
  end
  if phase == "run" then
    for n in plan:gmatch("%w+") do L.F[n]:set_value(1) end
    if d == 40 then
      out:write(string.format("poke (%d,%d) plan %s -> x=%d y=%d act=%d sub=%d pose=%d +57=%02x sy=%x\n", trials[k][1], trials[k][2], plan, m:read_u16(p + 8), m:read_u16(p + 12), m:read_u8(p + 4), m:read_u8(p + 5), m:read_u8(p + 24), m:read_u8(p + 57), m:read_u16(0x80406)))
      out:flush(); phase = "load"
    end
  end
end)
