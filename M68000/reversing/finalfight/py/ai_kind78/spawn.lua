-- spawn.lua (agent E): after FF_LOAD=<state>, spawn tag-2 records of chosen kinds through the real tag-2 allocator
-- bookkeeping ($3892: pop the free stack at 20242(A5), count at 20240(A5)) and fill them the way the stage script
-- entry writer $5ee6 does (+0=1, +6 x, +10 y, +18..+21 tag/kind/subtype, +54 frame, +98, +96), then log records.
-- Env (all optional unless noted):
--   FF_SPAWNS   "kind:sub20:sub21:dx:y[:f12[:b96]],..."  dx is relative to Cody's x (hex or dec, signed); y absolute
--   FF_SPAWN_AT frames after the load frame (default 3)
--   FF_KILL     1: clear +0 of every live pool-2 record at the spawn frame (isolates the spawned kinds)
--   FF_HEAL     1: refill Cody's +24/+26 from +28 every frame (he never dies)
--   FF_POKES    "frame:addr:value:width,..." extra pokes (hex addr/value, width 1|2|4)
--   FF_LOG      output file (per frame: header, then every live record of the pool-2/6/4 arrays + Cody, 192 bytes hex)
--   FF_LOG_LO/HI  frame window (relative to the load frame) for the log
--   FF_PLAN2    file returning {frame_rel, field, level} input entries (relative frames)
-- Run: FF_LOAD=ff_enemies FF_STOP=<abs frame> ffrun.sh spawn.lua   (FF_DIR is exported by ffrun.sh)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local A5 = 0xff8000
local base_frame = nil
local spawn_at = tonumber(os.getenv("FF_SPAWN_AT") or "3")
local out = assert(io.open(os.getenv("FF_LOG") or "spawn.log", "w"))
local lo, hi = tonumber(os.getenv("FF_LOG_LO") or "0"), tonumber(os.getenv("FF_LOG_HI") or "100000")
local function num(s) return tonumber(s) or tonumber(s, 16) end
local spawns = {}
for spec in string.gmatch(os.getenv("FF_SPAWNS") or "", "[^,]+") do
  local t = {}
  for p in string.gmatch(spec, "[^:]+") do t[#t + 1] = p end
  spawns[#spawns + 1] = { kind = tonumber(t[1]), s20 = tonumber(t[2] or "0"), s21 = tonumber(t[3] or "0"),
    dx = tonumber(t[4] or "0"), y = tonumber(t[5] or "40"), f12 = tonumber(t[6] or "0"), b96 = tonumber(t[7] or "0") }
end
local pokes = {}
-- "frame:addr:value:width" (hex addr/value) or "frame:@off:value:width" (decimal offset into the first spawned record)
for spec in string.gmatch(os.getenv("FF_POKES") or "", "[^,]+") do
  local f, a, v, w = string.match(spec, "(%d+):(@?%x+):(%x+):(%d)")
  local rel_off = nil
  if a:sub(1, 1) == "@" then rel_off = tonumber(a:sub(2)) end
  pokes[#pokes + 1] = { f = tonumber(f), a = (not rel_off) and tonumber(a, 16) or nil, off = rel_off, v = tonumber(v, 16), w = tonumber(w) }
end
local hudpush = tonumber(os.getenv("FF_HUDPUSH") or "-1")   -- push the last spawned record into the P1 enemy-HUD ring like $28d0 does
local last_spawn, first_spawn = nil, nil
local plan2 = os.getenv("FF_PLAN2") and dofile(os.getenv("FF_PLAN2")) or {}

local function alloc_tag2()
  local cnt = m:read_u16(A5 + 20240)
  if cnt == 0 then return nil end
  local sp = m:read_u32(A5 + 20242)
  local rec = 0xff0000 | m:read_u16(sp)
  m:write_u16(sp, 0)
  m:write_u32(A5 + 20242, sp + 2)
  m:write_u16(A5 + 20240, cnt - 1)
  return rec
end

local function dumprec(a)
  local t = {}
  for i = 0, 191, 2 do t[#t + 1] = string.format("%04x", m:read_u16(a + i)) end
  return table.concat(t)
end

local function do_spawns()
  local cx = m:read_u16(0xff856e) -- Cody x
  if os.getenv("FF_KILL") == "1" then
    for i = 0, 12 do m:write_u8(0xff86e8 + 192 * i, 0) end
  end
  for _, s in ipairs(spawns) do
    local a = alloc_tag2()
    if not a then out:write("SPAWN FAILED no free tag-2 record\n") break end
    last_spawn = a
    first_spawn = first_spawn or a
    m:write_u8(a, 1)
    m:write_u16(a + 6, (cx + s.dx) & 0xffff)
    m:write_u16(a + 10, s.y)
    m:write_u8(a + 18, 2); m:write_u8(a + 19, s.kind); m:write_u8(a + 20, s.s20); m:write_u8(a + 21, s.s21)
    m:write_u8(a + 54, s.f12); m:write_u8(a + 98, 0); m:write_u8(a + 96, s.b96)
    out:write(string.format("SPAWN f=%d rec=%06x kind=%d sub=%d/%d x=%04x y=%04x\n", L.frame(), a, s.kind, s.s20, s.s21, (cx + s.dx) & 0xffff, s.y))
  end
end

-- optional execution counters (needs FF_MAMEARGS="-debug -debugger none"): FF_ADDRS="3c4a2,3c504,...", FF_HIT_OUT=<file>
local hit_started, hit_seen, hit_counts, hit_order = false, 0, {}, {}
if os.getenv("FF_ADDRS") then
  emu.register_periodic(function()
    if not hit_started then
      hit_started = true
      local dbg = manager.machine.debugger
      for a in string.gmatch(os.getenv("FF_ADDRS"), "(%x+)") do
        dbg:command(string.format('bpset %s,1,{printf "H %s\\n"; g}', a, a))
        hit_order[#hit_order + 1] = a
      end
      dbg:command("go")
    end
  end)
end
local function hit_flush()
  local dbg = manager.machine.debugger
  if not dbg then return end
  local log = dbg.consolelog
  for i = hit_seen + 1, #log do
    local a = log[i]:match("^H (%x+)")
    if a then hit_counts[a] = (hit_counts[a] or 0) + 1 end
  end
  hit_seen = #log
end
local function hit_write()
  if not os.getenv("FF_ADDRS") then return end
  hit_flush()
  local h = assert(io.open(os.getenv("FF_HIT_OUT") or "hits.txt", "w"))
  for _, a in ipairs(hit_order) do h:write(string.format("%s %d\n", a, hit_counts[a] or 0)) end
  h:close()
end
emu.register_frame_done(function()
  local f = L.frame()
  if not base_frame then
    if os.getenv("FF_LOAD") then base_frame = tonumber(os.getenv("FF_BASE") or "4150") else base_frame = f end
  end
  local rel = f - base_frame
  if rel < 0 then return end
  if rel == spawn_at then do_spawns() end
  if rel == hudpush and last_spawn then
    local wi = m:read_u16(A5 + 900)
    local e = A5 + 644 + wi
    m:write_u16(e, last_spawn & 0xffff); m:write_u16(e + 2, m:read_u16(last_spawn + 24))
    m:write_u16(e + 4, m:read_u16(last_spawn + 26)); m:write_u16(e + 6, m:read_u16(last_spawn + 28))
    m:write_u16(A5 + 900, (wi + 8) & 0x7f)
  end
  for _, p in ipairs(pokes) do
    if p.f == rel then
      if p.off then p.a = first_spawn + p.off end
      if p.w == 1 then m:write_u8(p.a, p.v) elseif p.w == 2 then m:write_u16(p.a, p.v) else m:write_u32(p.a, p.v) end
    end
  end
  for _, e in ipairs(plan2) do if e[1] == rel then L.F[e[2]]:set_value(e[3]) end end
  -- FF_PIN="rel_from-rel_to:xhex": write the first spawned record's x word every frame in the window (keeps it next to Cody)
  local pin = os.getenv("FF_PIN")
  if pin and first_spawn then
    local a, b, x = string.match(pin, "(%d+)-(%d+):(%x+)")
    if rel >= tonumber(a) and rel <= tonumber(b) then m:write_u16(first_spawn + 6, tonumber(x, 16)) end
  end
  if os.getenv("FF_HEAL") == "1" then
    m:write_u16(0xff8580, m:read_u16(0xff8584)); m:write_u16(0xff8582, m:read_u16(0xff8584))
  end
  if rel >= lo and rel <= hi then
    out:write(string.format("F %d rel=%d cam=%04x,%04x s190=%02x s191=%02x d168=%02x\n", f, rel, m:read_u16(A5 + 1042), m:read_u16(A5 + 1046),
      m:read_u8(A5 + 190), m:read_u8(A5 + 191), m:read_u8(A5 + 168)))
    out:write("C " .. dumprec(0xff8568) .. "\n")
    if os.getenv("FF_P2") == "1" then out:write("C2 " .. dumprec(0xff8628) .. "\n") end
    if os.getenv("FF_SCRIPTREC") == "1" then
      local t = {}
      for i = 0, 63, 2 do t[#t + 1] = string.format("%04x", m:read_u16(0xffb1e8 + i)) end
      out:write("S " .. table.concat(t) .. "\n")
    end
    for i = 0, 12 do
      local a = 0xff86e8 + 192 * i
      if m:read_u8(a) ~= 0 then out:write(string.format("R %06x %s\n", a, dumprec(a))) end
    end
    for i = 0, 5 do
      local a = 0xff90a8 + 192 * i
      if m:read_u8(a) ~= 0 then out:write(string.format("P6 %06x %s\n", a, dumprec(a))) end
    end
    for i = 0, 7 do
      local a = 0xff9528 + 192 * i
      if m:read_u8(a) ~= 0 then out:write(string.format("P4 %06x %s\n", a, dumprec(a))) end
    end
    for i = 0, 15 do
      local a = 0xffb2e8 + 192 * i
      if m:read_u8(a) ~= 0 then out:write(string.format("PA %06x %s\n", a, dumprec(a))) end
    end
    for i = 0, 29 do
      local a = 0xff9b28 + 192 * i
      if m:read_u8(a) ~= 0 then out:write(string.format("P8 %06x %s\n", a, dumprec(a))) end
    end
    if f % 50 == 0 then out:flush() end
  end
  if os.getenv("FF_SHOT_WIN") then
    for a, b in string.gmatch(os.getenv("FF_SHOT_WIN"), "(%d+)-(%d+)") do
      local step = tonumber(os.getenv("FF_SHOT_STEP") or "1")
      if rel >= tonumber(a) and rel <= tonumber(b) and (rel - tonumber(a)) % step == 0 then
        L.screen:snapshot(string.format("%s_%05d.png", os.getenv("FF_TAG") or "spawn", rel))
      end
    end
  end
  if os.getenv("FF_SAVE_AT") and rel == tonumber(os.getenv("FF_SAVE_AT")) then
    local ram = L.ram()
    L.write(string.format("%s/%s_ram.bin", os.getenv("FF_OUT"), os.getenv("FF_SAVE_NAME")), ram)
    manager.machine:save(os.getenv("FF_SAVE_NAME"))
  end
  if os.getenv("FF_ADDRS") then hit_flush() end
  if rel >= tonumber(os.getenv("FF_REL_STOP") or "600") then hit_write(); out:close(); manager.machine:exit() end
end)
-- the stock driver only supplies FF_LOAD handling and FF_STOP; its own schedule is harmless after the load
-- (inputs scheduled for frames below 2200 never fire from frame 4150)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
