-- lab.lua: controlled experiments on one pool A type.  Loads the saved state lab0 (level 0, frame 1000, P1 standing at x=$187, y=$1c0, no enemies,
-- sx=$100) and executes a plan (Lua file, env CB_PLAN) that spawns records exactly like the script spawner $f388 does (byte 0 = $80, +2 type,
-- +16 variant, +8 x, +12 y, the rest zero), pins P1's position, keeps P1 alive and pokes hit flags.  Log format = enemylog.txt (F/P/R/H lines).
-- plan = { stop = <frames after load>, pin = {x=,y=} (P1 position pinned every frame, optional), god = true,
--          scriptoff = true (point both script lists at their terminators so nothing else spawns),
--          events = { {frame, "spawn", type, var, x, y}, {frame, "hit", slot, value}, {frame, "poke8"|"poke16"|"poke32", addr, value},
--                     {frame, "key", name, 0|1}, {frame, "kill", slot} } }
-- frame numbers are relative to the load (frame 0 = the first frame after the state load).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local plan = dofile(os.getenv("CB_PLAN"))
local out = io.open((os.getenv("CB_OUT") or ".") .. "/enemylog.txt", "w")
local m = L.mem
local function hex(base, n) local t = {} for k = 0, n - 1 do t[#t + 1] = string.format("%02x", m:read_u8(base + k)) end return table.concat(t) end
local nth, f0 = 0, nil
local shots = plan.shots or {}
emu.register_frame_done(function()
  nth = nth + 1
  if nth == 3 then manager.machine:load(plan.state or "lab0"); return end
  if nth < 4 then return end
  local f = L.frame()
  if not f0 then
    f0 = f
    if plan.scriptoff then m:write_u32(0x81e06, 0x6c168); m:write_u32(0x81e0a, 0x6d0e8) end
    if plan.setup then plan.setup(m) end
  end
  local r = f - f0
  for _, e in ipairs(plan.events or {}) do
    if e[1] == r then
      local k = e[2]
      if k == "spawn" then
        for i = 0, 15 do
          local b = 0x81000 + 0x40 * i
          if m:read_u8(b) & 0x80 == 0 then
            for q = 0, 0x3f, 2 do m:write_u16(b + q, 0) end
            m:write_u8(b, 0x80); m:write_u8(b + 2, e[3]); m:write_u8(b + 16, e[4]); m:write_u16(b + 8, e[5]); m:write_u16(b + 12, e[6])
            out:write(string.format("E %d spawn slot %d type %d var %d x %d y %d\n", r, i, e[3], e[4], e[5], e[6]))
            break
          end
        end
      elseif k == "hit" then local b = 0x81000 + 0x40 * e[3]; m:write_u8(b + 6, m:read_u8(b + 6) | e[4]); out:write(string.format("E %d hit slot %d value %02x\n", r, e[3], e[4]))
      elseif k == "poke8" then m:write_u8(e[3], e[4]) elseif k == "poke16" then m:write_u16(e[3], e[4]) elseif k == "poke32" then m:write_u32(e[3], e[4])
      elseif k == "key" then L.F[e[3]]:set_value(e[4])
      elseif k == "kill" then local b = 0x81000 + 0x40 * e[3]; m:write_u8(b, 0) end
    end
  end
  out:write(string.format("F %d %04x %04x %02x%02x lvl=%d s400=%02x%02x%02x%02x e=%02x%02x\n", f, m:read_u16(0x8040a), m:read_u16(0x80406), m:read_u8(0x80040), m:read_u8(0x80041), m:read_u8(0x80046), m:read_u8(0x80400), m:read_u8(0x80401), m:read_u8(0x80402), m:read_u8(0x80403), m:read_u8(0x81e02), m:read_u8(0x81e03)))
  out:write(string.format("P %d %s\n", f, hex(0x80100, 0x80)))
  for i = 0, 15 do local b = 0x81000 + 0x40 * i; if m:read_u8(b) & 0x80 ~= 0 then out:write(string.format("R %d %d %s\n", f, i, hex(b, 64))) end end
  for i = 0, 7 do local b = 0x81c00 + 0x20 * i; if m:read_u8(b) & 0x80 ~= 0 then out:write(string.format("H %d %d %s\n", f, i, hex(b, 32))) end end
  for i = 0, 31 do local b = 0x81400 + 0x40 * i; if m:read_u8(b) & 0x80 ~= 0 and plan.logB then out:write(string.format("B %d %d %s\n", f, i, hex(b, 64))) end end
  if plan.god ~= false then m:write_u8(0x80113, 0x38) end
  if plan.pin then m:write_u16(0x80108, plan.pin.x); m:write_u16(0x8010a, 0); m:write_u16(0x8010c, plan.pin.y); m:write_u16(0x8010e, 0) end
  if shots[r] then L.screen:snapshot(string.format("lab%05d.png", r)) end
  if r >= plan.stop then out:close(); manager.machine:exit() end
end)
