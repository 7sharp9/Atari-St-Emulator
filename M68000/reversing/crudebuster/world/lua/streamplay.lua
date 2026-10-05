-- streamplay.lua: start a 2-player game at level CB_LEVEL (two coins, 2P start) and, from frame CB_START on, drive both
-- controllers with the decoded demo streams (demo CB_DEMO = 0..2) through the real input ports; log per frame
--   f p1x p1y p2x p2y 8004a 80040 80041 80046 held1 held2
-- env: CB_LEVEL, CB_DEMO, CB_START, CB_STOP, CB_OUT (streamplay_<tag>.csv), CB_TAG, CB_NOFEED=1 (log only)
-- stream model (proven by py/demo_check.py): per frame D0 = (ptr); cnt -= 1; if cnt == 0 then ptr += 2, D0 = (ptr), cnt = count at ptr
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local cpu = manager.machine.devices[":maincpu"]
local want = tonumber(os.getenv("CB_LEVEL") or "1")
local demo = tonumber(os.getenv("CB_DEMO") or "0")
local start = tonumber(os.getenv("CB_START") or "900")
local stop = tonumber(os.getenv("CB_STOP") or "1800")
local tag = os.getenv("CB_TAG") or "x"
local out = io.open((os.getenv("CB_OUT") or ".") .. "/streamplay_" .. tag .. ".csv", "w")
taps = {}
taps[1] = m:install_write_tap(0x80046, 0x80047, "lvl", function(off, data, mask)
  local pc = cpu.state["CURPC"].value
  if pc == 0x146e + 6 or (pc >= 0x1400 and pc < 0x1480) then
    return (data & 0xff) ~= data and data or ((want << 8) | want)
  end
end)
-- ROM streams: read through the program space (ROM is mapped at 0)
local function rb(a) return m:read_u8(a) end
local function expand(base, n)
  local t, ptr = {}, base
  local cnt = rb(ptr + 1)
  for i = 1, n do
    local d0 = rb(ptr); cnt = cnt - 1
    if cnt == 0 then ptr = ptr + 2; d0 = rb(ptr); cnt = rb(ptr + 1) end
    t[i] = d0
  end
  return t
end
local N = 700
local s1, s2 = expand(0x5c000 + 0x400 * demo, N), expand(0x5d000 + 0x400 * demo, N)
local F = L.F
local joined = false
local p1 = { F.up, F.down, F.left, F.right, F.b1, F.b2, F.b3 }
local p2 = { F.p2up, F.p2down, F.p2left, F.p2right, F.p2b1, F.p2b2, F.p2b3 }
local function apply(byte, fields) for i = 1, 7 do fields[i]:set_value(((byte >> (i - 1)) & 1)) end end
emu.register_frame_done(function()
  local f = L.frame()
  if f == 600 or f == 630 then F.coin:set_value(1) elseif f == 612 or f == 642 then F.coin:set_value(0)
  elseif f == 700 then F.start1:set_value(1) elseif f == 712 then F.start1:set_value(0) end
  -- P2 joins like the demo does ($83e sets both flags before $1488): poke the active flag on the first frame of the game
  if not joined and (m:read_u8(0x80040) & 0x80) ~= 0 then m:write_u8(0x80180, 0x80); joined = true end
  -- bytes for frame f+1 are set now (ports are sampled once per frame)
  local i = (f + 1) - start + 1
  if not os.getenv("CB_NOFEED") and i >= 1 and i <= N then apply(s1[i], p1); apply(s2[i], p2)
  elseif not os.getenv("CB_NOFEED") and i == N + 1 then apply(0, p1); apply(0, p2) end
  out:write(string.format("%d,%x,%x,%x,%x,%x,%x,%x,%x,%x,%x\n", f, m:read_u16(0x80108), m:read_u16(0x8010c), m:read_u16(0x80188), m:read_u16(0x8018c),
    m:read_u16(0x8004a), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u8(0x80046), m:read_u8(0x80051), m:read_u8(0x80053)))
  if f >= stop then out:close(); manager.machine:exit() end
end)
