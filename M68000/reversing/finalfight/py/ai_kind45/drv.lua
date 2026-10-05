-- drv.lua: load a saved state and dump the object-pool run per frame (and optionally poke / press buttons).
-- Env: FF_LOAD=<state> FF_N=<frames to run after the load> FF_OUTF=<file> FF_POKES="addr:w:val@frame,..." (hex addr/val, frame is
-- the number of frames after the load at which the poke is applied at frame_done) FF_PLAN=<lua file returning {frame,field,level}>
-- FF_GFXDUMP="k,k": also write gfx RAM $900000-$90ffff at those relative frames to <FF_OUTF>.gfx<k> (read by gate_names.py).
-- Run through run.sh (it sets FF_DIR to reversing/finalfight/lua and the MAME run directory).
-- Record per frame: u32 frame, then work RAM $ff8000..$ffbfff (A5 area + players + pools 2,6,4,8, tag $10 records).
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local n = tonumber(os.getenv("FF_N") or "300")
local outf = assert(os.getenv("FF_OUTF"))
local pokes = {}
for a, w, v, f in string.gmatch(os.getenv("FF_POKES") or "", "(%x+):(%d):(%x+)@(%d+)") do
  pokes[#pokes + 1] = { tonumber(a, 16), tonumber(w), tonumber(v, 16), tonumber(f) }
end
-- FF_SPAWN="kind:sub:b21:lvl:x:y@frame,..." (kind, +20, +21, level byte +96 in hex/decimal as given, x, y words; x<0 means camera-relative offset from Cody)
-- replicates the allocator $3892 and the script spawn $5ee6 (tag 2, +19 kind, +20/+21, +96, +98) and the cap counters of $3e88.
-- FF_KILL="frame,frame": zero byte 0 of every pool-2 record (orphans them; for controlled single-enemy runs).
-- FF_HEAL=1: refill Cody's health word (+24 = $ff8580) to its maximum every 8 frames.
local spawns = {}
for k, s2, b21, lvl, x, y, f in string.gmatch(os.getenv("FF_SPAWN") or "", "(%d+):(%d+):(%d+):(%-?%d+):(%-?%d+):(%d+)@(%d+)") do
  spawns[#spawns + 1] = { tonumber(k), tonumber(s2), tonumber(b21), tonumber(lvl), tonumber(x), tonumber(y), tonumber(f) }
end
local kills = {}
for f in string.gmatch(os.getenv("FF_KILL") or "", "(%d+)") do kills[tonumber(f)] = true end
local heal = os.getenv("FF_HEAL") == "1"
local gfxd = {}
for f in string.gmatch(os.getenv("FF_GFXDUMP") or "", "(%d+)") do gfxd[tonumber(f)] = true end
local shots = {}
for f in string.gmatch(os.getenv("FF_SHOTS") or "", "(%d+)") do shots[tonumber(f)] = true end -- relative frames to snapshot (files in <run>/snap/ffightuc/)
local function do_spawn(p)
  local m = L.mem
  local cnt = m:read_u16(0xff8000 + 20240)
  if cnt == 0 then print("SPAWN: no free pool-2 record"); return end
  local sp = m:read_u32(0xff8000 + 20242)
  local rec = m:read_u16(sp); rec = 0xff0000 | rec
  m:write_u16(sp, 0)
  m:write_u32(0xff8000 + 20242, sp + 2); m:write_u16(0xff8000 + 20240, cnt - 1)
  local kind = p[1]
  if kind >= 3 and kind <= 6 then
    local a = 0xff8000 - 28331 + (kind - 3); m:write_u8(a, m:read_u8(a) + 1)
  elseif kind < 3 then
    local a = 0xff8000 - 28332; m:write_u8(a, m:read_u8(a) + 1)
  end
  local x = p[5]
  if x < 0 then x = m:read_u16(0xff856e) - x end -- negative: offset right of Cody
  m:write_u8(rec, 1); m:write_u16(rec + 6, x); m:write_u16(rec + 10, p[6])
  m:write_u8(rec + 18, 2); m:write_u8(rec + 19, kind); m:write_u8(rec + 20, p[2]); m:write_u8(rec + 21, p[3])
  m:write_u8(rec + 96, p[4])
  print(string.format("SPAWN frame_rel kind %d sub %d b21 %d at record %06x x=%d y=%d", kind, p[2], p[3], rec, x, p[6]))
end
local plan_file = os.getenv("FF_PLAN")
local plan = (plan_file and plan_file ~= "") and dofile(plan_file) or {}
local fh = io.open(outf, "wb")
local loaded, f0 = false, nil
local mem = L.mem
local function region32(base, len) -- same bytes as L.region, 4 per read
  local t, m = {}, L.mem
  for a = base, base + len - 1, 4 do
    local v = m:read_u32(a)
    t[#t + 1] = string.char((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255)
  end
  return table.concat(t)
end
local function put32(v) fh:write(string.char((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255)) end
emu.register_frame_done(function()
  local f = L.frame()
  local lf = os.getenv("FF_LOAD")
  if lf and not loaded then loaded = true; manager.machine:load(lf); return end
  if not f0 then f0 = f end
  local k = f - f0
  put32(f)
  fh:write(region32(0xff8000, 0x4000))
  if shots[k] then L.screen:snapshot(string.format("%s_%05d.png", os.getenv("FF_TAG") or "shot", k)) end
  if os.getenv("FF_SAVE_AT") and tonumber(os.getenv("FF_SAVE_AT")) == k then -- FF_SAVE_NAME=<state>: state saved at the END of this frame, with a work RAM dump beside the trace
    local rf = io.open(outf .. "." .. os.getenv("FF_SAVE_NAME") .. ".ram", "wb"); rf:write(region32(0xff0000, 0x10000)); rf:close()
    manager.machine:save(os.getenv("FF_SAVE_NAME"))
  end
  if gfxd[k] then local gf = io.open(outf .. ".gfx" .. k, "wb"); gf:write(region32(0x900000, 0x10000)); gf:close() end
  for _, sp in ipairs(spawns) do if sp[7] == k then do_spawn(sp) end end
  if kills[k] then for i = 0, 12 do mem:write_u8(0xff86e8 + 0xc0 * i, 0) end end
  if heal and k % 8 == 0 then mem:write_u16(0xff8580, mem:read_u16(0xff8584)) end
  for _, p in ipairs(pokes) do
    if p[4] == k then
      if p[2] == 1 then mem:write_u8(p[1], p[3]) elseif p[2] == 2 then mem:write_u16(p[1], p[3]) else mem:write_u32(p[1], p[3]) end
    end
  end
  for _, e in ipairs(plan) do if e[1] == k then L.F[e[2]]:set_value(e[3]) end end
  if k >= n then fh:close(); manager.machine:exit() end
end)
