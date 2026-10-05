-- seqlab.lua: load a saved state (CB_STATE in $CB_RUN/sta/cbuster/) and play an input sequence, logging the player every frame.
--   CB_SEQ = space separated steps "buttons:frames", buttons joined by "," from up down left right b1 b2 b3, "-" for none, e.g. "right:20 right,b2:14 -:40".
--   Output CB_OUT/seqlab.txt: frame since load, step index, x, y, action (+4), sub-action (+5), +1, +26, +27, +52 (animation counter), +57.
--   A state loaded at frame F needs F/58 seconds of machine time more (cbmame.sh run <this file> 600).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/seqlab.txt", "w")
local steps, total = {}, 0
for b, n in (os.getenv("CB_SEQ") or "-:60"):gmatch("(%S-):(%d+)") do steps[#steps + 1] = { b = b, n = tonumber(n), t0 = total }; total = total + tonumber(n) end
local loaded, f0 = false, nil
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "nb_stall1"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  local si = 0
  for i, s in ipairs(steps) do if d >= s.t0 and d < s.t0 + s.n then si = i; for n in s.b:gmatch("[^,]+") do if L.F[n] then L.F[n]:set_value(1) end end end end
  local p = 0x80100
  out:write(string.format("%d %d x=%d y=%d act=%d sub=%d +1=%02x +26=%02x +27=%02x +52=%02x +57=%02x\n", d, si, m:read_u16(p + 8), m:read_u16(p + 12), m:read_u8(p + 4), m:read_u8(p + 5), m:read_u8(p + 1), m:read_u8(p + 26), m:read_u8(p + 27), m:read_u8(p + 52), m:read_u8(p + 57)))
  if d > total + 10 then out:close(); manager.machine:exit() end
end)
