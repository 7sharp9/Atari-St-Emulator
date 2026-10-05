-- poolrec.lua: after FF_LOAD, write per frame (end of frame): u32 frame, A5 vars $ff8000..$ff87ff (2048 bytes),
-- player records (2 x 192 at $ff8568 .. wait: players are at $ff8568 and $ff8628), pool 2 (13 x 192 at $ff86e8).
-- Layout per frame: 4 + 2048 + 192*2 + 192*13 bytes. Output FF_REC_OUT. Window FF_REC_LO..FF_REC_HI (frame numbers).
-- Optional FF_PRESS="a-b,c-d" Button1, FF_KEYS="field:a-b,..." (right/left/up/down/b1/b2/b3) hold fields.
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local out = assert(io.open(os.getenv("FF_REC_OUT") or "rec.bin", "wb"))
local m = L.mem
local function blk(a, n)
  local t = {}
  for i = 0, n - 1, 2 do local v = m:read_u16(a + i); t[#t + 1] = string.char(v >> 8, v & 0xff) end
  return table.concat(t)
end
local keys = {}
for fld, a, b in string.gmatch(os.getenv("FF_KEYS") or "", "(%a%w*):(%d+)-(%d+)") do keys[#keys + 1] = { fld, tonumber(a), tonumber(b) } end
local lo = tonumber(os.getenv("FF_REC_LO") or "0")
local hi = tonumber(os.getenv("FF_REC_HI") or "999999")
local god = os.getenv('FF_GOD') == '1'
-- FF_WTAP="lo-hi,lo-hi" (hex, word aligned) -> FF_WTAP_OUT lines "f=<frame> pc=<CURPC> a=<addr> m=<mask> d=<data>"
wtaps = {}
if os.getenv("FF_WTAP") then
  local fh = assert(io.open(os.getenv("FF_WTAP_OUT") or "wtap.txt", "w"))
  local pcreg = manager.machine.devices[":maincpu"].state["CURPC"]
  for a, b in string.gmatch(os.getenv("FF_WTAP"), "(%x+)-(%x+)") do
    wtaps[#wtaps + 1] = m:install_write_tap(tonumber(a, 16), tonumber(b, 16), "w" .. a, function(offset, data, mask)
      fh:write(string.format("f=%d pc=%06x a=%06x m=%04x d=%04x\n", L.frame(), pcreg.value, offset, mask, data)) end)
  end
  emu.register_frame_done(function() fh:flush() end)
end
-- FF_COPY="frame:src:dst:len" (hex addrs, decimal len): block copy at the end of that frame
local copies = {}
for fr, sa, da, ln in string.gmatch(os.getenv("FF_COPY") or "", "(%d+):(%x+):(%x+):(%d+)") do copies[#copies + 1] = { tonumber(fr), tonumber(sa, 16), tonumber(da, 16), tonumber(ln) } end
-- FF_POKE="frame:addr:size:value,..." (hex addr/value, size 1/2): written at the end of that frame (the game sees it from frame+1)
local pokes = {}
for fr, ad, sz, vl in string.gmatch(os.getenv("FF_POKE") or "", "(%d+):(%x+):(%d):(%x+)") do pokes[#pokes + 1] = { tonumber(fr), tonumber(ad, 16), tonumber(sz), tonumber(vl, 16) } end
emu.register_frame_done(function()
  local f = L.frame()
  for _, p in ipairs(pokes) do if p[1] == f then if p[3] == 1 then m:write_u8(p[2], p[4]) else m:write_u16(p[2], p[4]) end end end
  for _, c in ipairs(copies) do if c[1] == f then for o = 0, c[4] - 1, 2 do m:write_u16(c[3] + o, m:read_u16(c[2] + o)) end end end
  if god then local hp = m:read_u16(0xff8580); if hp < 0x50 then m:write_u16(0xff8580, 0x90); m:write_u16(0xff8582, 0x90) end end
  local lvl = {}
  for _, k in ipairs(keys) do lvl[k[1]] = lvl[k[1]] or 0; if f >= k[2] and f < k[3] then lvl[k[1]] = 1 end end
  for fld, v in pairs(lvl) do L.F[fld]:set_value(v) end
  if f >= lo and f <= hi then
    out:write(string.char((f >> 24) & 255, (f >> 16) & 255, (f >> 8) & 255, f & 255), blk(0xff8000, 2048), blk(0xff8568, 384), blk(0xff86e8, 192 * 13), blk(0xff1100, 256), blk(0xffb2e8, 192 * 16))
  end
  if f >= hi then out:flush() end
end)
dofile(os.getenv("FF_DIR") .. "/ffdrive.lua")
