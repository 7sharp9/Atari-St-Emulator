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

-- p2/b extension: FF_PLAN=<file.lua> returns extra {frame, field, value} entries (levels), FF_CENSUS=<file> logs live records
local plan = os.getenv("FF_PLAN")
if plan then for _, e in ipairs(dofile(plan)) do sched[#sched + 1] = e end end
local census = os.getenv("FF_CENSUS") and io.open(os.getenv("FF_CENSUS"), "w")
local census_lo = tonumber(os.getenv("FF_CENSUS_LO") or "2200")
local function census_dump(f)
  local mm = L.mem
  census:write(string.format("F %d\n", f))
  do -- HUD queue of P1: ring of 8-byte entries {record pointer, hp, shadow, max} at 644(A5), write index 900(A5) (routine $28d0)
    local wi = mm:read_u16(0xff8000 + 900)
    local e = 0xff8000 + 644 + ((wi - 8) & 0x7f)
    census:write(string.format("Q wi=%d ptr=%04x hp=%04x sh=%04x max=%04x\n", wi, mm:read_u16(e), mm:read_u16(e + 2), mm:read_u16(e + 4), mm:read_u16(e + 6)))
  end
  for i = 0, 59 do
    local a = 0xff8568 + 0xc0 * i
    local b0 = mm:read_u8(a)
    local b1 = mm:read_u8(a + 1)
    if b0 ~= 0 or b1 ~= 0 then
      census:write(string.format("R %d %06x b0=%02x b1=%02x pool=%02x b19=%02x b20=%02x x=%04x y=%04x hp=%04x w20=%04x st2=%02x st3=%02x p92=%06x p56=%06x b55=%02x b96=%02x b98=%02x b44=%02x b45=%02x\n", i, a, b0, b1,
        mm:read_u8(a + 18), mm:read_u8(a + 19), mm:read_u8(a + 20), mm:read_u16(a + 6), mm:read_u16(a + 10), mm:read_u16(a + 24),
        mm:read_u16(a + 20), mm:read_u8(a + 2), mm:read_u8(a + 3), mm:read_u32(a + 92) & 0xffffff, mm:read_u32(a + 56) & 0xffffff,
        mm:read_u8(a + 55), mm:read_u8(a + 96), mm:read_u8(a + 98), mm:read_u8(a + 44), mm:read_u8(a + 45)))
    end
  end
end

-- same FNV-1a value as before: the low 32 bits of (h ^ b) * P do not depend on the high bits, so the 32-bit mask is applied once at the end, and string.byte returns 8 bytes per call
local function fnv(s)
  local h = 2166136261
  local byte = string.byte
  for i = 1, #s, 8 do
    local a, b, c, d, e, f, g, k = byte(s, i, i + 7)
    h = (h ~ a) * 16777619
    h = (h ~ b) * 16777619
    h = (h ~ c) * 16777619
    h = (h ~ d) * 16777619
    h = (h ~ e) * 16777619
    h = (h ~ f) * 16777619
    h = (h ~ g) * 16777619
    h = (h ~ k) * 16777619
  end
  return h & 0xffffffff
end

local trace = io.open(string.format("%s/%s_trace.txt", out, tag), "w")
local frames_bin
if os.getenv("FF_TRACE") == "1" then frames_bin = io.open(string.format("%s/tmp/%s_frames.bin", out, tag), "wb") end
local m = L.mem
local loaded = false
local saved = false
local lf = os.getenv("FF_LOAD")
local ru16 = m.read_u16
local scr, frame_number = L.screen, L.screen.frame_number
local do_shots = os.getenv("FF_SHOTS") == "1"
local sl, sh, ss = tonumber(os.getenv("FF_SHOT_LO") or "0"), tonumber(os.getenv("FF_SHOT_HI") or "-1"), tonumber(os.getenv("FF_SHOT_STEP") or "1")
local shot_win = {}
for a, b in string.gmatch(os.getenv("FF_SHOT_WIN") or "", "(%d+)-(%d+)") do shot_win[#shot_win + 1] = { tonumber(a), tonumber(b) } end
local env_save = os.getenv("FF_SAVE")
emu.register_frame_done(function()
  local f = frame_number(scr)
  if lf and not loaded then
    loaded = true
    manager.machine:load(lf)
    return
  end
  L.apply(sched, f)
  if census and f >= census_lo then census_dump(f) end
  if f >= 1000 and f % 10 == 0 then
    trace:write(string.format("%d %04x %04x %04x %08x\n", f, ru16(m, 0xff856e), ru16(m, 0xff85dc),
      ru16(m, 0xff85e4), fnv(L.ram())))
  end
  if frames_bin and f >= TRACE_LO and f < TRACE_HI then frames_bin:write(L.ram()) end
  if do_shots and f % 50 == 0 and f >= 1000 then L.screen:snapshot(string.format("%s_%05d.png", tag, f)) end
  if f >= sl and f <= sh and (f - sl) % ss == 0 then L.screen:snapshot(string.format("%s_%05d.png", tag, f)) end
  for i = 1, #shot_win do
    if f >= shot_win[i][1] and f <= shot_win[i][2] then L.screen:snapshot(string.format("%s_%05d.png", tag, f)) end
  end
  if f == save_frame and env_save then
    L.write(string.format("%s/%s_ram.bin", out, os.getenv("FF_SAVE")), L.ram())
    L.write(string.format("%s/%s_gfxram.bin", out, os.getenv("FF_SAVE")), L.region(0x900000, 0x30000))
    L.screen:snapshot(os.getenv("FF_SAVE") .. ".png")
    manager.machine:save(os.getenv("FF_SAVE"))
    saved = true
  end
  if f >= stop_frame then
    if census then census:close() end
    trace:close(); if frames_bin then frames_bin:close() end
    manager.machine:exit()
  end
end)
