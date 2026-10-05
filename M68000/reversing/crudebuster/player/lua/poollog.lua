-- poollog.lua: load a saved state (CB_STATE in $CB_RUN/sta/cbuster/), hold CB_PLAN buttons (as walllab.lua; CB_PULSE=n presses them 2 frames in every n) from frame 5, and every CB_EVERY frames (default 30) until CB_LEN (default 600)
--   write the scroll, the flags, the player and every live pool A and pool B record to CB_OUT/poollog.txt: "frame | P x y act sub | A type:state:x:y:hp:f<+6>,<+17>,<+51> ... | B type:b0:x:y ...".
--   A state loaded at frame F needs F/58 seconds of machine time more (cbmame.sh run <this file> 600).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local m = L.mem
local out = io.open(os.getenv("CB_OUT") .. "/poollog.txt", "w")
local plan = os.getenv("CB_PLAN") or ""
local every = tonumber(os.getenv("CB_EVERY") or "30")
local len = tonumber(os.getenv("CB_LEN") or "600")
local loaded, f0 = false, nil
emu.register_frame_done(function()
  if not loaded then loaded = true; manager.machine:load(os.getenv("CB_STATE") or "nb_stall1"); return end
  local f = L.frame(); if not f0 then f0 = f end
  local d = f - f0
  m:write_u8(0x80113, 0x38)
  m:write_u16(0x80042, 0x0300)
  for _, n in ipairs { "up", "down", "left", "right", "b1", "b2", "b3" } do L.F[n]:set_value(0) end
  if d >= 5 and (not os.getenv("CB_PULSE") or d % tonumber(os.getenv("CB_PULSE")) < 2) then for n in plan:gmatch("%w+") do L.F[n]:set_value(1) end end
  if d % every == 0 then
    local p = 0x80100
    local A, B = {}, {}
    for i = 0, 15 do local a = 0x81000 + i * 0x40; if m:read_u8(a) & 0x80 ~= 0 then A[#A + 1] = string.format("%d:%02x:%d:%d:%d:f%02x,%02x,%02x", m:read_u8(a + 2), m:read_u8(a + 3), m:read_u16(a + 8), m:read_u16(a + 12), m:read_u8(a + 5), m:read_u8(a + 6), m:read_u8(a + 17), m:read_u8(a + 51)) end end
    for i = 0, 31 do local a = 0x81400 + i * 0x40; if m:read_u8(a) & 0x80 ~= 0 then local t = m:read_u8(a + 2); if t ~= 43 and t ~= 50 and t ~= 53 then B[#B + 1] = string.format("%d:%02x:%d:%d", t, m:read_u8(a), m:read_u16(a + 8), m:read_u16(a + 12)) end end end
    out:write(string.format("%d sx=%x f40=%02x%02x f400=%02x%02x%02x hp=%d | P %d %d %d %d | A %s | B %s\n", f, m:read_u16(0x8040a), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u8(p + 19), m:read_u16(p + 8), m:read_u16(p + 12), m:read_u8(p + 4), m:read_u8(p + 5), table.concat(A, " "), table.concat(B, " ")))
    out:flush()
  end
  if d > len then out:close(); manager.machine:exit() end
end)
