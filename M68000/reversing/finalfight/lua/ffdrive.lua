-- ffdrive.lua: drive Final Fight (ffightuc) from cold boot into stage-1 gameplay with Cody, deterministic.
-- Run through run.sh. Environment (all optional):
--   FF_VARIANT   drive (default) | ctl     ctl omits the walk-test presses (control run)
--   FF_TAG       output tag (default = variant)
--   FF_TRACE     1: write per-frame RAM to tmp/<tag>_frames.bin for frames TRACE_LO..TRACE_HI
--   FF_SAVE      state name to save at FF_SAVE_FRAME (default 2200) and dump RAM/gfx RAM/PNG
--   FF_LOAD      state name to load at frame 1 instead of the whole drive (resume check)
--   FF_STOP      frame at which to exit (default FF_SAVE_FRAME+5)
-- Output: <FF_OUT>/<tag>_trace.txt  lines "frame x ff85dc ff85e4 fnv32(work RAM)" every 10 frames from 1000.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local variant = os.getenv("FF_VARIANT") or "drive"
local tag = os.getenv("FF_TAG") or variant
local out = os.getenv("FF_OUT") or os.getenv("FF_DIR")
local save_frame = tonumber(os.getenv("FF_SAVE_FRAME") or "2200")
local stop_frame = tonumber(os.getenv("FF_STOP") or tostring(save_frame + 5))
local TRACE_LO, TRACE_HI = tonumber(os.getenv("FF_TRACE_LO") or "1790"), tonumber(os.getenv("FF_TRACE_HI") or "1990")

-- Inputs are levels read once per frame by the VBL handler: hold >= several frames.
-- Level set at the end of frame N is what the game sees from frame N+1.
local sched = {
  { 1100, "coin", 1 }, { 1112, "coin", 0 },        -- insert coin (CREDIT=1 appears)
  { 1150, "start1", 1 }, { 1162, "start1", 0 },    -- P1 start -> SELECT PLAYER (cursor on Guy)
  { 1250, "right", 1 }, { 1256, "right", 0 },      -- cursor to Cody
  { 1280, "b1", 1 }, { 1292, "b1", 0 },            -- confirm; scripted stage intro (not controllable until ~1700)
}
if variant == "drive" then
  local t = {
    { 1800, "right", 1 }, { 1860, "right", 0 },
    { 1880, "left", 1 }, { 1920, "left", 0 },
    { 1940, "up", 1 }, { 1970, "up", 0 },
    { 1990, "down", 1 }, { 2010, "down", 0 },
  }
  for _, e in ipairs(t) do sched[#sched + 1] = e end
end
-- both variants: walk right from 2040 until Bred is on screen, release at 2195
sched[#sched + 1] = { 2040, "right", 1 }
sched[#sched + 1] = { 2195, "right", 0 }

local function fnv(s)
  local h = 2166136261
  for i = 1, #s, 4 do
    local a, b, c, d = s:byte(i, i + 3)
    h = ((h ~ a) * 16777619) & 0xffffffff
    h = ((h ~ b) * 16777619) & 0xffffffff
    h = ((h ~ c) * 16777619) & 0xffffffff
    h = ((h ~ d) * 16777619) & 0xffffffff
  end
  return h
end

local trace = io.open(string.format("%s/%s_trace.txt", out, tag), "w")
local frames_bin
if os.getenv("FF_TRACE") == "1" then frames_bin = io.open(string.format("%s/tmp/%s_frames.bin", out, tag), "wb") end
local m = L.mem
local loaded = false
local saved = false
emu.register_frame_done(function()
  local f = L.frame()
  local lf = os.getenv("FF_LOAD")
  if lf and not loaded then
    loaded = true
    manager.machine:load(lf)
    return
  end
  if not lf then L.apply(sched, f) end
  if f >= 1000 and f % 10 == 0 then
    trace:write(string.format("%d %04x %04x %04x %08x\n", f, m:read_u16(0xff856e), m:read_u16(0xff85dc),
      m:read_u16(0xff85e4), fnv(L.ram())))
  end
  if frames_bin and f >= TRACE_LO and f < TRACE_HI then frames_bin:write(L.ram()) end
  if os.getenv("FF_SHOTS") == "1" and f % 50 == 0 and f >= 1000 then L.screen:snapshot(string.format("%s_%05d.png", tag, f)) end
  if f == save_frame and os.getenv("FF_SAVE") then
    L.write(string.format("%s/%s_ram.bin", out, os.getenv("FF_SAVE")), L.ram())
    L.write(string.format("%s/%s_gfxram.bin", out, os.getenv("FF_SAVE")), L.region(0x900000, 0x30000))
    L.screen:snapshot(os.getenv("FF_SAVE") .. ".png")
    manager.machine:save(os.getenv("FF_SAVE"))
    saved = true
  end
  if f >= stop_frame then
    trace:close(); if frames_bin then frames_bin:close() end
    manager.machine:exit()
  end
end)
