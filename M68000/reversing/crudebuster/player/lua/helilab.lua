-- helilab.lua: load a saved state (CB_STATE in $CB_RUN/sta/cbuster/, e.g. nb_stall2 of a level 2 run), walk to x = CB_GOTO, then repeat an attack and log the helicopter.
--   CB_MODE: jab (b1 pulses, standing), jk (jump kick macro of natbot: b2 for 3 frames, b1 at +14..16, period CB_PERIOD frames, default 70),
--            jkr (the same while holding right), jkl (holding left)
--   CB_LEN frames after the load (default 600). Logs every 3 frames: player x y act sub +28 (attack flag), then pool A records of type 28 and 45..50: type:state:x:y:hp.
--   a state loaded at frame F needs F/58 seconds of machine time more (cbmame.sh run <this file> 600).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/helilab.txt", "w")
local mode = os.getenv("CB_MODE") or "jab"
local period = tonumber(os.getenv("CB_PERIOD") or "70")
local goto_ = tonumber(os.getenv("CB_GOTO") or "2160")
local len = tonumber(os.getenv("CB_LEN") or "600")
local loaded, f0 = false, nil
local function heli()
  local t = {}
  for i = 0, 15 do
    local a = 0x81000 + i * 0x40
    if m:read_u8(a) & 0x80 ~= 0 then
      local ty = m:read_u8(a + 2)
      if ty == 28 or (ty >= 45 and ty <= 50) then t[#t + 1] = string.format("%d:%02x:%d:%d:%d", ty, m:read_u8(a + 3), m:read_u16(a + 8), m:read_u16(a + 12), m:read_u8(a + 5)) end
    end
  end
  return table.concat(t, " ")
end
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "nb_stall2"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  m:write_u16(0x80042, 0x0300)
  local p = 0x80100
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  local px = m:read_u16(p + 8)
  if d >= 5 and d < 200 and math.abs(px - goto_) > 3 then
    L.F.right:set_value(px < goto_ and 1 or 0); L.F.left:set_value(px > goto_ and 1 or 0)
  elseif d >= 200 and d < len then
    local k = (d - 200) % period
    if mode == "jab" then if k % 6 < 2 then L.F.b1:set_value(1) end
    else
      if mode == "jkr" then L.F.right:set_value(k < 20 and 1 or 0) elseif mode == "jkl" then L.F.left:set_value(k < 20 and 1 or 0) end
      if k < 3 then L.F.b2:set_value(1) end
      if k >= 14 and k < 17 then L.F.b1:set_value(1) end
    end
  end
  if d % 3 == 0 then out:write(string.format("%d x=%d y=%d act=%d sub=%d atk=%d | %s\n", d, px, m:read_u16(p + 12), m:read_u8(p + 4), m:read_u8(p + 5), m:read_u8(p + 28), heli())) end
  if d > len + 30 then out:close(); manager.machine:exit() end
end)
