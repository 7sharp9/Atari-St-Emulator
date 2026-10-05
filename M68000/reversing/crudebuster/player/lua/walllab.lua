-- walllab.lua: load a saved state (CB_STATE, in $CB_RUN/sta/cbuster/), optionally walk to x = CB_GOTO (or right to x 435 when CB_GOTO is unset and CB_NOWALK is unset),
--   then hold the buttons of CB_PLAN (space separated: up down left right b1 b2 b3) until frame CB_LEN after the load; CB_PULSE=n presses them 2 frames in every n.
--   Logs every 6 frames: x, y, action (+4), sub-action (+5), +1, +57, scroll x/y, and the pool B type 28 records (x:byte0,hp(+5),state,+6,+17).
--   Used to show that a lock wall (pool B type 28) is removed by jabs: CB_PLAN="right b1" CB_PULSE=6 CB_LEN=900, and that up/down do nothing at the level 1 rubble.
--   Run with a large seconds_to_run: a state loaded at frame F needs F/58 seconds more (cbmame.sh run <this file> 600).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/walllab.txt", "w")
local function wallinfo() local t = {} for i = 0, 31 do local a = 0x81400 + i*0x40; if m:read_u8(a) & 0x80 ~= 0 and m:read_u8(a+2) == 28 then t[#t+1] = string.format("%d:b0=%02x,hp=%02x,st=%02x,+6=%02x,+17=%02x", m:read_u16(a+8), m:read_u8(a), m:read_u8(a+5), m:read_u8(a+3), m:read_u8(a+6), m:read_u8(a+17)) end end return table.concat(t, " ") end
local loaded, f0 = false, nil
local plan = os.getenv("CB_PLAN") or "up"   -- hold this direction after frame 20
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "nb_fetch"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  local p = 0x80100
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  local px0 = m:read_u16(p+8)
  local goto_ = tonumber(os.getenv('CB_GOTO') or '0')
  if goto_ > 0 and d >= 20 and d < 150 and px0 ~= goto_ then L.F.right:set_value(px0 < goto_ and 1 or 0); L.F.left:set_value(px0 > goto_ and 1 or 0)
  elseif not os.getenv('CB_NOWALK') and d >= 20 and d < 100 and px0 < 435 then L.F.right:set_value(1)
  elseif d >= (os.getenv('CB_NOWALK') and (goto_ > 0 and 150 or 20) or 100) and d < (tonumber(os.getenv("CB_LEN") or "400")) then
    if os.getenv("CB_PULSE") then local pl = tonumber(os.getenv("CB_PULSE")); if d % pl < 2 then for n in plan:gmatch("%w+") do L.F[n]:set_value(1) end end
    else for n in plan:gmatch("%w+") do L.F[n]:set_value(1) end end end
  if d % 6 == 0 then out:write(string.format("%d x=%d y=%d act=%d sub=%d +1=%02x +57=%02x sx=%x sy=%x wall=%s\n", d, m:read_u16(p+8), m:read_u16(p+12), m:read_u8(p+4), m:read_u8(p+5), m:read_u8(p+1), m:read_u8(p+57), m:read_u16(0x8040a), m:read_u16(0x80406), wallinfo())) end
  if d > (tonumber(os.getenv('CB_LEN') or '400')) + 60 then out:close(); manager.machine:exit() end
end)
