-- terr.lua: pass-5 agent B. Load a state, list the live pool-8 kind $22 markers and the 80-tile attribute blocks they wrote, optionally clear the terrain bits of those blocks (TR_CLEAR=1),
-- hold a direction (TR_KEY=left|right, from TR_FROM to TR_TO relative frames), log player x, camera x, and count the reads of the marker blocks by pc (read taps).
-- Environment: TR_LOAD, TR_N (frames), TR_KEY, TR_FROM, TR_TO, TR_CLEAR, TR_LOG, TR_SHOTS="rel,rel,.." (snapshots), TR_GOD=1 (health poke, reported)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local m = L.mem
local A5 = 0xff8000
local N = tonumber(os.getenv("TR_N") or "300")
local log = assert(io.open(os.getenv("TR_LOG"), "w"))
local key = os.getenv("TR_KEY")
local kfrom, kto = tonumber(os.getenv("TR_FROM") or "0"), tonumber(os.getenv("TR_TO") or "0")
local clear = os.getenv("TR_CLEAR") == "1"
local setbits = os.getenv("TR_SETBITS")   -- "x:y:code" write terrain code into the 80-tile block at x,y like $1fa5a
local shots = {}
for r in string.gmatch(os.getenv("TR_SHOTS") or "", "(%d+)") do shots[tonumber(r)] = true end
local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
local loaded, base = false, nil
local blocks = {}
local rtaps = {}
local reads = {}
local function blockaddr(x, y)   -- $477a
  local d1 = (~y) & 0xffff
  local d2 = d1
  d1 = ((d1 & 0x300) << 4) & 0xffff
  d2 = (d2 & 0xf0) >> 2
  d1 = d1 + d2
  local d0 = ((x & 0x3f0) << 2) + d1
  return 0x90c000 + (d0 & 0xffff)
end
emu.register_frame_done(function()
  local f = L.frame()
  if not loaded then loaded = true; manager.machine:load(os.getenv("TR_LOAD")); return end
  if not base then
    base = f
    for i = 0, 29 do
      local a = 0xff9b28 + 0xc0 * i
      if m:read_u8(a) ~= 0 and m:read_u8(a + 19) == 0x22 then
        local x, y, ch = m:read_u16(a + 6), m:read_u16(a + 10), m:read_u16(a + 20)
        local b = blockaddr(x, y)
        blocks[#blocks + 1] = { rec = a, x = x, y = y, ch = ch, addr = b }
        log:write(string.format("# marker rec %06x ch=%d x=%04x y=%04x state=%d block=%06x\n", a, ch, x, y, m:read_u8(a + 2), b))
      end
    end
    -- every attribute word of every written block: dump and optionally clear
    for _, b in ipairs(blocks) do
      local words = {}
      for col = 0, 4 do for row = 0, 15 do
        local a = b.addr + 4 * 0 + col * 4 * 0 -- placeholder, filled below
      end end
      -- $1fa5a writes: for col in 0..4 { for row in 0..15 { attr(A0+2) ...; A0 += 4 } } with A0 continuing row-major in the tile map (consecutive 4-byte entries): 5*16 = 80 consecutive entries
      local vals = {}
      for k = 0, 79 do vals[#vals + 1] = string.format("%04x", m:read_u16(b.addr + 4 * k + 2)) end
      log:write(string.format("# block %06x attrs: %s\n", b.addr, table.concat(vals, " ")))
      if clear then for k = 0, 79 do local a = b.addr + 4 * k + 2; m:write_u16(a, m:read_u16(a) & 0x3ff) end log:write("# cleared terrain bits\n") end
      reads[b.addr] = {}
      local lo, hi = b.addr, b.addr + 4 * 79 + 3
      rtaps[#rtaps + 1] = m:install_read_tap(lo, hi, "rd" .. b.addr, function(off, data, mask)
        local k = string.format("%06x", pcreg.value); reads[b.addr][k] = (reads[b.addr][k] or 0) + 1
      end)
    end
    for a in string.gmatch(os.getenv("TR_CLRADDR") or "", "(%x+)") do
      local b = tonumber(a, 16)
      for k = 0, 79 do local x = b + 4 * k + 2; m:write_u16(x, m:read_u16(x) & 0x3ff) end
      log:write(string.format("# cleared terrain bits of 80 entries at %06x\n", b))
    end
    for sx, sy, sc in string.gmatch(setbits or "", "(%x+):(%x+):(%x+)") do
      local b = blockaddr(tonumber(sx, 16), tonumber(sy, 16))
      for k = 0, 79 do local a = b + 4 * k + 2; m:write_u16(a, (m:read_u16(a) & 0x3ff) | (tonumber(sc, 16) << 10)) end
      log:write(string.format("# set terrain code %s on 80 entries at %06x (x=%s y=%s)\n", sc, b, sx, sy))
    end
  end
  local r = f - base
  if key then L.F[key]:set_value((r >= kfrom and r < kto) and 1 or 0) end
  if os.getenv("TR_GOD") == "1" then m:write_u16(A5 + 0x568 + 24, m:read_u16(A5 + 0x568 + 28)) m:write_u8(A5 + 0x568 + 128, 5) end
  if r % 10 == 0 then
    log:write(string.format("r=%d f=%d px=%04x py=%04x cam=%04x st=%d/%d hp=%04x\n", r, f, m:read_u16(0xff856e), m:read_u16(0xff8572), m:read_u16(A5 + 1042), m:read_u8(A5 + 190), m:read_u8(A5 + 191), m:read_u16(0xff8580)))
  end
  if shots[r] then L.screen:snapshot(string.format("tr_%04d.png", r)) end
  if r >= N then
    for _, b in ipairs(blocks) do
      local t = {}
      for pc, n in pairs(reads[b.addr]) do t[#t + 1] = string.format("%s:%d", pc, n) end
      table.sort(t)
      log:write(string.format("# reads of block %06x by pc: %s\n", b.addr, table.concat(t, " ")))
    end
    log:close(); manager.machine:exit()
  end
end)
