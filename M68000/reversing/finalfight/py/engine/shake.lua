-- shake.lua: pass-5 agent B. Load a state, run, emulate the call `jsr $1b428` (screen shaker start/restart) at chosen frames and log the camera, the scroll
-- shadows and the CPS-A scroll register writes per frame. $1b428 is emulated with the allocator logic ($3946: pool 8 free stack count 20346(A5), pointer 20348(A5)).
-- Environment: SH_LOAD state name (in <run>/sta/ffightuc), SH_CALLS "frame:stage:area,..." (relative frames after the load, optional pokes of 190/191(A5) just before the call;
-- stage/area -1 = leave), SH_N frames to run (default 80), SH_LOG output file, SH_SHOT=1 snapshots every frame (PNG in the snapshot dir), SH_SAVE name.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local A5 = 0xff8000
local load = assert(os.getenv("SH_LOAD"))
local N = tonumber(os.getenv("SH_N") or "80")
local log = assert(io.open(os.getenv("SH_LOG"), "w"))
local calls = {}
for f, s, a in string.gmatch(os.getenv("SH_CALLS") or "5:-1:-1", "(%d+):(-?%d+):(-?%d+)") do calls[#calls + 1] = { tonumber(f), tonumber(s), tonumber(a) } end
local cpu = manager.machine.devices[":maincpu"]
local pcreg = cpu.state["CURPC"]
local rel = nil
local base = 0
local function s16(v) if v >= 0x8000 then return v - 0x10000 end return v end
taps = {}
-- scroll registers $80010c..$800117 (CPS-A: scroll1 x/y, scroll2 x/y, scroll3 x/y)
local regs = {}
taps[1] = m:install_write_tap(0x80010c, 0x800117, "scr", function(off, data, mask) regs[#regs + 1] = string.format("%x=%04x@%06x", off, data, pcreg.value) end)
-- camera writers
local camw = {}
taps[2] = m:install_write_tap(0xff8416, 0xff8417, "camy", function(off, data, mask) camw[#camw + 1] = string.format("camy=%04x@%06x", data, pcreg.value) end)
local loaded = false
local p20done = false
local function call_1b428()
  local flag = m:read_u8(A5 - 27916)
  if flag == 0 then
    local cnt = m:read_u16(A5 + 20346)
    if cnt == 0 then log:write("# pool 8 empty\n"); return end
    local ptr = m:read_u32(A5 + 20348)
    local a = (0xffff0000 | m:read_u16(ptr)) & 0xffffff
    m:write_u16(ptr, 0); m:write_u32(A5 + 20348, ptr + 2); m:write_u16(A5 + 20346, cnt - 1)
    m:write_u32(A5 - 27920, 0xffff0000 | (a & 0xffff))
    m:write_u8(a, 1); m:write_u8(a + 19, 3); m:write_u16(a + 96, 0); m:write_u8(A5 - 27916, 1)
    log:write(string.format("# call: created record %06x\n", a))
  else
    local rec = m:read_u32(A5 - 27920) & 0xffffff
    m:write_u16(rec + 2, 0)
    local d0 = s16(m:read_u16(rec + 96)); m:write_u16(rec + 96, 0)
    local ch = m:read_u16(rec + 20)
    log:write(string.format("# call: restart rec=%06x +96 was %d ch=%d\n", rec, d0, ch))
    if d0 < 0 then
      d0 = -d0
      if ch == 0 then m:write_u16(A5 + 1046, (m:read_u16(A5 + 1046) + d0) & 0xffff)
      elseif ch == 2 then m:write_u16(A5 + 1046, (m:read_u16(A5 + 1046) + d0) & 0xffff); m:write_u16(A5 + 1174, (m:read_u16(A5 + 1174) + d0) & 0xffff)
      else m:write_u16(A5 + 918, (m:read_u16(A5 + 918) - d0) & 0xffff); m:write_u16(A5 + 1116, (m:read_u16(A5 + 1116) + d0) & 0xffff); m:write_u16(A5 + 1046, (m:read_u16(A5 + 1046) + d0) & 0xffff) end
    end
  end
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(load); return end
  if not rel then rel = 0; base = f end
  local r = f - base
  for _, c in ipairs(calls) do
    if c[1] == r then
      if c[2] >= 0 then m:write_u8(A5 + 190, c[2]) end
      if c[3] >= 0 then m:write_u8(A5 + 191, c[3]) end
      call_1b428()
    end
  end
  local rec = m:read_u32(A5 - 27920) & 0xffffff
  local flag = m:read_u8(A5 - 27916)
  if os.getenv("SH_P20") and flag ~= 0 and m:read_u8(rec + 2) == 2 and not p20done then p20done = true; m:write_u16(rec + 20, tonumber(os.getenv("SH_P20"))); log:write("# poked +20\n") end
  log:write(string.format("r=%d f=%d st=%d/%d cam=%04x,%04x c2y=%04x 918=%04x 1116=%04x sh36=%04x sh44=%04x sh52=%04x flag=%d", r, f, m:read_u8(A5 + 190), m:read_u8(A5 + 191),
    m:read_u16(A5 + 1042), m:read_u16(A5 + 1046), m:read_u16(A5 + 1174), m:read_u16(A5 + 918), m:read_u16(A5 + 1116), m:read_u16(A5 + 36), m:read_u16(A5 + 44), m:read_u16(A5 + 52), flag))
  if flag ~= 0 then
    log:write(string.format(" rec[0=%d 2=%d 19=%d 20=%d 30=%d 31=%d 96=%d]", m:read_u8(rec), m:read_u8(rec + 2), m:read_u8(rec + 19), m:read_u16(rec + 20), m:read_u8(rec + 30), m:read_u8(rec + 31), s16(m:read_u16(rec + 96))))
  end
  log:write(" | " .. table.concat(camw, " ") .. " | " .. table.concat(regs, " ") .. "\n")
  camw = {}; regs = {}
  if os.getenv("SH_SHOT") == "1" then L.screen:snapshot(string.format("sh_%03d.png", r)) end
  if r >= N then log:close(); manager.machine:exit() end
end)
