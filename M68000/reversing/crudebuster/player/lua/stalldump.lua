-- stalldump.lua: load a saved state (CB_STATE in $CB_RUN/sta/cbuster/), hold the buttons of CB_PLAN (space separated: up down left right b1 b2 b3) from frame 5 to CB_LEN after the load,
--   then write a screenshot (CB_OUT/dump.png) and list the player record, pool A and pool B records (type, byte 0, state, x, y, hp) to CB_OUT/dump.txt and exit.
--   Used to read why a held direction stops moving (solid pool B records 24..31 with byte 0 bit 2 are part of the terrain probe $ebb0, tiles are in world/py/terrain.py).
--   Run with enough seconds: a state loaded at frame F needs F/58 seconds more.
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local plan = os.getenv("CB_PLAN") or ""
local len = tonumber(os.getenv("CB_LEN") or "100")
local loaded, f0 = false, nil
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "nb_stall1"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  if d >= 5 and d < len then for n in plan:gmatch("%w+") do L.F[n]:set_value(1) end end
  if d == len then
    local out = io.open(os.getenv("CB_OUT") .. "/dump.txt", "w")
    local p = 0x80100
    local t = {} for k = 0, 0x7f do t[#t + 1] = string.format("%02x", m:read_u8(p + k)) end
    out:write(string.format("frame %d scroll x=%x y=%x s400=%02x%02x%02x\nP x=%d y=%d act=%d sub=%d +57=%02x\n  %s\n", f, m:read_u16(0x8040a), m:read_u16(0x80406), m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u16(p + 8), m:read_u16(p + 12), m:read_u8(p + 4), m:read_u8(p + 5), m:read_u8(p + 57), table.concat(t, " ")))
    for _, pl in ipairs { { "A", 0x81000, 16 }, { "B", 0x81400, 32 } } do
      for i = 0, pl[3] - 1 do
        local a = pl[2] + i * 0x40
        if m:read_u8(a) & 0x80 ~= 0 then out:write(string.format("%s type=%d b0=%02x st=%02x x=%d y=%d hp=%d\n", pl[1], m:read_u8(a + 2), m:read_u8(a), m:read_u8(a + 3), m:read_u16(a + 8), m:read_u16(a + 12), m:read_u8(a + 5))) end
      end
    end
    out:close(); L.screen:snapshot("dump.png")
  end
  if d > len + 5 then manager.machine:exit() end
end)
