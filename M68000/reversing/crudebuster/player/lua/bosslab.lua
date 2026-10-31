-- bosslab.lua: load a saved state with a level 2 final boss (type 16 or 36) alive (CB_STATE in $CB_RUN/sta/cbuster/), play a fight policy
--   (CB_POLICY) and log P1 and the boss every frame, to test the grab rule of the brain leaf $26d7a (enemies1.md 4.3).
--   Policies: idle (no input); pulse (b1 2 frames in every CB_PULSE, default 5, never a direction); face (as pulse, but when the boss is on the
--   other side a single frame of the horizontal direction turns the player first); jk (b2 for 2 frames, b1 at air frame CB_JKF (default 10),
--   then idle until landing, repeated; the direction toward the boss is held while airborne only when CB_JKDIR=1); face0 (pulse, and a standing
--   player facing away from the boss is turned at once); roll (face0, and a standing player within 64 px of the boss rolls away from it: down + the
--   direction away + b2, at most every 30 frames).
--   God mode and the level timer are refilled as in natbot.lua. Output CB_OUT/bosslab.txt, one line per frame:
--   d px py act sub pose var p88 php | boss type state x y hp +1 | dx flags$80040 facing (summary: py/bosslab_sum.py).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/bosslab.txt", "w")
local policy = os.getenv("CB_POLICY") or "idle"
local pulse = tonumber(os.getenv("CB_PULSE") or "5")
local jkf = tonumber(os.getenv("CB_JKF") or "10")
local jkdir = os.getenv("CB_JKDIR") == "1"
local len = tonumber(os.getenv("CB_LEN") or "3000")
local loaded, f0 = false, nil
local jk0, roll0 = -100, -100
local function boss()
  for i = 0, 15 do
    local a = 0x81000 + i * 0x40
    local t = m:read_u8(a + 2)
    if m:read_u8(a) & 0x80 ~= 0 and (t == 16 or t == 36) then return a, t end
  end
end
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "boss2"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  if m:read_u16(0x80042) < 0x100 then m:write_u16(0x80042, 0x0300) end
  local p = 0x80100
  local px, py = m:read_u16(p + 8), m:read_u16(p + 12)
  local ba, bt = boss()
  local bx = ba and m:read_u16(ba + 8) or px
  local press = {}
  if policy == "pulse" or policy == "face" then
    local facing = m:read_u8(p + 7) -- 0 right
    local want = (bx >= px) and 0 or 1
    if policy == "face" and ba and facing ~= want and m:read_u8(p + 4) == 8 and d % pulse == 0 then press[want == 0 and "right" or "left"] = true
    elseif (policy == "face0" or policy == "roll") and ba and facing ~= want and m:read_u8(p + 4) == 8 then press[want == 0 and "right" or "left"] = true
    elseif policy == "roll" and ba and math.abs(bx - px) < 64 and m:read_u8(p + 4) == 8 and m:read_u8(p + 5) == 0 and d - roll0 > 30 then
      roll0 = d; press.down = true; press[want == 0 and "left" or "right"] = true; press.b2 = true
    elseif d % pulse < 2 then press.b1 = true end
    if policy == "roll" and d - roll0 < 3 then press.down = true; press[want == 0 and "left" or "right"] = true; press.b2 = d - roll0 < 2; press.b1 = nil end
  elseif policy == "jk" then
    local airborne = m:read_u8(p + 57) & 0x80 ~= 0
    local act, sub = m:read_u8(p + 4), m:read_u8(p + 5)
    if not airborne and sub ~= 3 and d - jk0 > 6 then jk0 = d end
    local k = d - jk0
    if k < 2 then press.b2 = true end
    if k == jkf or k == jkf + 1 then press.b1 = true end
    if jkdir and k < 40 and ba then press[(bx >= px) and "right" or "left"] = true end
  end
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(press[n] and 1 or 0) end
  local bs = ba and string.format("%d %x %d %d %d %02x", bt, m:read_u8(ba + 3), bx, m:read_u16(ba + 12), m:read_u8(ba + 5), m:read_u8(ba + 1)) or "- - - - - -"
  out:write(string.format("%d %d %d %x %d %x %d %02x %d | %s | %d %02x %d\n", d, px, py, m:read_u8(p + 4), m:read_u8(p + 5), m:read_u8(p + 24), m:read_u8(p + 25),
    m:read_u8(p + 88), m:read_u8(p + 19), bs, bx - px, m:read_u8(0x80040), m:read_u8(p + 7)))
  if d >= len then out:close(); manager.machine:exit() end
end)
