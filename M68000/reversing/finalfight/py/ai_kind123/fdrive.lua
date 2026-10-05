-- fdrive.lua (agent B, p3): run ffdrive.lua from a saved state with extras. Environment (all optional, plus everything ffdrive.lua takes):
--   FF_SPAWN="f:kind:sub20:b21:dx:dy:lvl,..."  at the end of frame f allocate a tag-2 record through the free stack (as $3892 does) and fill it as
--       the spawner $5ee6 does: x = Cody.x + dx, y = Cody.y + dy (signed words), +18..+21 = 2, kind, sub20, b21, +96 = lvl (negative: 169(A5)),
--       and bump the grunt counter ($ff1154 for kinds 0-2, $ff1155+kind-3 for kinds >= 3) like the throttle $3e88 does.
--   FF_KILL="f" at the end of frame f zero byte 0 of every live pool-2 record that was not spawned by FF_SPAWN and zero the throttle counters
--   FF_KEEPHP=1  every frame refill Cody's +24/+26 to +28 when it drops below half
--   FF_POKE="f:addr:value:width,..."  hex addr/value, width 1|2|4
--   FF_RECHUD=1 adds "H f <hex of the 160 bytes at $ff1314>" (the HUD enemy-name object); FF_RECPROPS=1 adds "Q f idx <hex>" for live tag-$a props; FF_COPYP2=<frame> FF_P2DX=<dx> clones player 1 into player 2; FF_NOSCRIPT=1 parks the stage script; FF_HOLD=lo-hi:addr:value:width pokes every frame
--   FF_REC=<file> FF_REC_LO=<frame>  per frame: "G f <hex of A5+0..A5+511>", "P f idx <hex of the 192-byte record>" for Cody and every pool-2 record with b0 or b1 non-zero
--   FF_WATCH="addr-addr,..." write taps (word aligned) logged to FF_WATCH_OUT as "W f pc addr data mask"
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local A5 = 0xff8000
local POOL2, N2 = 0xff86e8, 13
local spawns, pokes, killf = {}, {}, tonumber(os.getenv("FF_KILL") or "-1")
for f, k, s20, b21, dx, dy, lvl in string.gmatch(os.getenv("FF_SPAWN") or "", "(%d+):(%d+):(%d+):(%d+):(%-?%d+):(%-?%d+):(%-?%d+)") do
  spawns[#spawns + 1] = { f = tonumber(f), kind = tonumber(k), s20 = tonumber(s20), b21 = tonumber(b21), dx = tonumber(dx), dy = tonumber(dy), lvl = tonumber(lvl) }
end
for f, a, v, w in string.gmatch(os.getenv("FF_POKE") or "", "(%d+):(%x+):(%x+):(%d)") do
  pokes[#pokes + 1] = { f = tonumber(f), a = tonumber(a, 16), v = tonumber(v, 16), w = tonumber(w) }
end
local holds = {}
for a, b, ad, v, w in string.gmatch(os.getenv("FF_HOLD") or "", "(%d+)%-(%d+):(%x+):(%x+):(%d)") do
  holds[#holds + 1] = { lo = tonumber(a), hi = tonumber(b), a = tonumber(ad, 16), v = tonumber(v, 16), w = tonumber(w) }
end
local copyp2 = tonumber(os.getenv("FF_COPYP2") or "-1")   -- frame at which player 1's record is copied to player 2's record (x shifted by FF_P2DX, default 0)
local spawned = {}
local rec = os.getenv("FF_REC") and io.open(os.getenv("FF_REC"), "w")
local rec_lo = tonumber(os.getenv("FF_REC_LO") or "0")
local function s16(v) if v >= 0x8000 then return v - 0x10000 end return v end
local function hexblk(a, n)
  local t = {}
  for i = 0, n - 1 do t[#t + 1] = string.format("%02x", m:read_u8(a + i)) end
  return table.concat(t)
end
local function do_spawn(s)
  local cnt = m:read_u16(A5 + 20240)
  if cnt == 0 then print("SPAWN FAIL: free stack empty"); return end
  local a1 = m:read_u32(A5 + 20242)
  local w = m:read_u16(a1)
  local rec_addr = 0xff0000 | w
  m:write_u16(a1, 0)
  m:write_u32(A5 + 20242, a1 + 2)
  m:write_u16(A5 + 20240, cnt - 1)
  for i = 0, 127 do if i ~= 78 and i ~= 79 then m:write_u8(rec_addr + i, 0) end end  -- $3a1c clears +0..+127 and keeps +78 (effect group handle)
  local cx, cy = m:read_u16(0xff856e), m:read_u16(0xff8572)
  m:write_u8(rec_addr, 1)
  m:write_u16(rec_addr + 6, (cx + s.dx) & 0xffff)
  m:write_u16(rec_addr + 10, (cy + s.dy) & 0xffff)
  m:write_u8(rec_addr + 18, 2)
  m:write_u8(rec_addr + 19, s.kind)
  m:write_u8(rec_addr + 20, s.s20)
  m:write_u8(rec_addr + 21, s.b21)
  local lvl = s.lvl
  if lvl < 0 then lvl = m:read_u8(A5 + 169) end
  m:write_u8(rec_addr + 96, lvl)
  if s.kind < 3 then
    m:write_u8(0xff1154, m:read_u8(0xff1154) + 1)
  elseif s.kind < 7 then
    local a = 0xff1155 + s.kind - 3
    m:write_u8(a, m:read_u8(a) + 1)
  end
  spawned[rec_addr] = true
  print(string.format("SPAWN f=%d kind=%d sub=%d at %06x x=%04x y=%04x lvl=%d", L.frame(), s.kind, s.s20, rec_addr, (cx + s.dx) & 0xffff, (cy + s.dy) & 0xffff, lvl))
end
if os.getenv("FF_WATCH") then
  local wout = assert(io.open(os.getenv("FF_WATCH_OUT") or "watch.txt", "w"))
  local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
  wtaps = {}
  for a, b in string.gmatch(os.getenv("FF_WATCH"), "(%x+)-(%x+)") do
    wtaps[#wtaps + 1] = m:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, function(off, data, mask)
      wout:write(string.format("W f=%d pc=%06x a=%06x d=%04x m=%04x\n", L.frame(), pcreg.value, off, data, mask))
    end)
  end
  emu.register_frame_done(function() wout:flush() end)
end
emu.register_frame_done(function()
  local f = L.frame()
  local lf = os.getenv("FF_LOAD")
  if lf and f < 4000 then return end
  if f == copyp2 then
    for i = 0, 191 do m:write_u8(0xff8628 + i, m:read_u8(0xff8568 + i)) end
    m:write_u16(0xff8628 + 6, (m:read_u16(0xff8568 + 6) + tonumber(os.getenv("FF_P2DX") or "0")) & 0xffff)
    print("COPYP2 at frame", f)
  end
  for _, s in ipairs(spawns) do if s.f == f then do_spawn(s) end end
  if f == killf then
    for i = 0, N2 - 1 do
      local a = POOL2 + 0xc0 * i
      if m:read_u8(a) ~= 0 and not spawned[a] then m:write_u8(a, 0); m:write_u8(a + 1, 0) end
    end
    for a = 0xff1154, 0xff115b do m:write_u8(a, 0) end  -- grunt count, kind 3.. counters, attacker-token word $ff115a
    for k = 0, 8 do if k < 3 then end end
    local g = 0
    for rec_addr in pairs(spawned) do
      local kind = m:read_u8(rec_addr + 19)
      if kind < 3 then m:write_u8(0xff1154, m:read_u8(0xff1154) + 1) elseif kind < 7 then local a = 0xff1155 + kind - 3; m:write_u8(a, m:read_u8(a) + 1) end
    end
  end
  for _, p in ipairs(pokes) do
    if p.f == f then
      if p.w == 1 then m:write_u8(p.a, p.v) elseif p.w == 2 then m:write_u16(p.a, p.v) else m:write_u32(p.a, p.v) end
    end
  end
  for _, p in ipairs(holds) do
    if f >= p.lo and f <= p.hi then
      if p.w == 1 then m:write_u8(p.a, p.v) elseif p.w == 2 then m:write_u16(p.a, p.v) else m:write_u32(p.a, p.v) end
    end
  end
  if os.getenv("FF_NOSCRIPT") == "1" and f >= killf then m:write_u8(0xffb1ea, 6) end  -- stage script record $ffb1e8: state 6 = idle ($5da4 rts), so no further group spawns
  if os.getenv("FF_KEEPHP") == "1" then
    local mx = m:read_u16(0xff8568 + 28)
    if m:read_u16(0xff8568 + 24) < mx // 2 and s16(m:read_u16(0xff8568 + 24)) > 0 then m:write_u16(0xff8568 + 24, mx); m:write_u16(0xff8568 + 26, mx) end
  end
  if os.getenv("FF_KEEPEHP") == "1" then
    for rec_addr in pairs(spawned) do
      local h, sh, mx = m:read_u16(rec_addr + 24), m:read_u16(rec_addr + 26), m:read_u16(rec_addr + 28)
      if h == sh and h < mx // 2 and m:read_u8(rec_addr + 2) == 2 then m:write_u16(rec_addr + 24, mx); m:write_u16(rec_addr + 26, mx) end
    end
  end
  if rec and f >= rec_lo then
    rec:write(string.format("G %d %s\n", f, hexblk(A5, 512)))
    rec:write(string.format("P %d c %s\n", f, hexblk(0xff8568, 192)))
    if os.getenv("FF_RECHUD") == "1" then rec:write(string.format("H %d %s\n", f, hexblk(0xff1314, 160))) end  -- P1 enemy-bar object -27884(A5): +18..+20 copy of the tracked record, +148 long = name entry
    if os.getenv("FF_RECPROPS") == "1" then
      for i = 0, 15 do
        local a = 0xffb2e8 + 0xc0 * i
        if m:read_u8(a) ~= 0 then rec:write(string.format("Q %d %d %s\n", f, i, hexblk(a, 64))) end
      end
    end
    for i = 0, N2 - 1 do
      local a = POOL2 + 0xc0 * i
      if m:read_u8(a) ~= 0 or m:read_u8(a + 1) ~= 0 then rec:write(string.format("P %d %d %s\n", f, i, hexblk(a, 192))) end
    end
  end
  if f >= tonumber(os.getenv("FF_STOP") or "0") - 1 and rec then rec:flush() end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
