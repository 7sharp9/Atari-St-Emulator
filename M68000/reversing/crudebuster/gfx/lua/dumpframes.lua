-- dumpframes.lua: input-scheduled drive (as lua/drive.lua) that, at chosen frames, dumps the complete renderer state
-- plus MAME's own screenshot of the same frame.  Run with cbmame.sh run (no debugger) or script.
--   CB_DIR    reversing/crudebuster/lua (for lib.lua)         CB_PLAN   plan file ({frame, field, level} list)
--   CB_OUT    output dir (frames fNNNNN.bin, ctl_log.txt)     CB_FRAMES "n,lo:hi:step,..." frames to dump
--   CB_POKE   "frame:addr:value[:size[:o|c]],..." big-endian pokes (default size 1 byte) of 68000 space applied at that frame; ":o" ORs, ":c" clears bits
--   CB_STOP   last frame
-- What is dumped (file layout, all big-endian as on the bus), see py/rstate.py:
--   0x0000  chip0 control words 0..7   (16 bytes)   -- write-only on the bus: kept from a write tap, see below
--   0x0010  chip1 control words 0..7   (16 bytes)
--   0x0020  $0a0000-$0ae7ff            (0xe800)     playfield RAM and rowscroll RAM of both chips
--   0x e820 sprite RAM buffer (0x800)  -- the copy MAME's buffered_spriteram16 made at the last write to $bc000
--   0x f020 palette low $0b8000 (0x1000), palette ext $0b9000 (0x1000)
--   0x11020 work RAM $080000 (0x4000)
--   0x15020 trailer (8 bytes): m_pri (u8), 0, m_prot (u16), last $bc004 write (u16), frame&1, frame&0xff
-- The control registers of the deco16ic are not readable on the bus; the device's control_r is not exposed to Lua, so a
-- write tap on $0b5000-$0b500f / $0b6000-$0b600f keeps the last value written per word (from reset: install before frame 1).
local L = dofile(os.getenv("CB_DIR") .. "/lib.lua")
local out = os.getenv("CB_OUT") or "."
local sched = {}
if os.getenv("CB_PLAN") then sched = dofile(os.getenv("CB_PLAN")) end
local stop = tonumber(os.getenv("CB_STOP") or "3000")
local want = {}
for tok in (os.getenv("CB_FRAMES") or ""):gmatch("[^,]+") do
  local lo, hi, st = tok:match("^(%d+):(%d+):(%d+)$")
  if lo then for f = tonumber(lo), tonumber(hi), tonumber(st) do want[f] = true end else want[tonumber(tok)] = true end
end
local pokes = {}
for tok in (os.getenv("CB_POKE") or ""):gmatch("[^,]+") do
  local f, a, v, s, o = tok:match("^(%d+):(%x+):(%x+):?(%d*):?([oc]?)$")
  pokes[#pokes + 1] = { tonumber(f), tonumber(a, 16), tonumber(v, 16), tonumber(s ~= "" and s or "1"), o }
end

local mem = L.mem
local function NOW() return manager.machine.time:as_double() end
local ctl = { [0] = {}, [1] = {} }   -- ctl[chip][word]
for c = 0, 1 do for w = 0, 7 do ctl[c][w] = 0 end end
local sprbuf = string.rep("\0", 0x800)
local log = assert(io.open(out .. "/ctl_log.txt", "w"))
-- tap handles must stay in globals
tap_ctl0 = mem:install_write_tap(0xb5000, 0xb500f, "ctl0", function(off, data, mask)
  local w = (off >> 1) & 7
  local old = ctl[0][w]
  local nv = old
  if mask & 0xff00 ~= 0 then nv = (nv & 0x00ff) | (data & 0xff00) end
  if mask & 0x00ff ~= 0 then nv = (nv & 0xff00) | (data & 0x00ff) end
  ctl[0][w] = nv
  log:write(string.format("%d %.9f %d %d %04x %04x\n", L.frame(), NOW(), 0, 0 * 8 + w, data & 0xffff, mask & 0xffff))
end)
tap_ctl1 = mem:install_write_tap(0xb6000, 0xb600f, "ctl1", function(off, data, mask)
  local w = (off >> 1) & 7
  local nv = ctl[1][w]
  if mask & 0xff00 ~= 0 then nv = (nv & 0x00ff) | (data & 0xff00) end
  if mask & 0x00ff ~= 0 then nv = (nv & 0xff00) | (data & 0x00ff) end
  ctl[1][w] = nv
  log:write(string.format("%d %.9f %d %d %04x %04x\n", L.frame(), NOW(), 0, 8 + w, data & 0xffff, mask & 0xffff))
end)
tap_spr = mem:install_write_tap(0xbc000, 0xbc001, "sprbuf", function(off, data, mask)
  sprbuf = L.region(0xb0000, 0x800)
  log:write(string.format("%d %.9f 0 spr\n", L.frame(), NOW()))
end)

-- $bc004 write (prot_w): m_pri / m_prot are driver state, not on the bus; mirror cbuster_state::prot_w exactly
local prot, pri, lastw = 0, 0, -1
tap_prot = mem:install_write_tap(0xbc004, 0xbc005, "prot", function(off, data, mask)
  local d = data & mask & 0xffff
  lastw = d
  if d == 0x9a00 then prot = 0 end
  if d == 0xaa then prot = 0x74 end
  if d == 0x0200 then prot = 0x63 << 8 end
  if d == 0x9a then prot = 0xe end
  if d == 0x55 then prot = 0x1e end
  if d == 0x0e then prot = 0x0e; pri = 0 end
  if d == 0x00 then prot = 0x0e; pri = 0 end
  if d == 0xf1 then prot = 0x36; pri = 1 end
  if d == 0x80 then prot = 0x2e; pri = 1 end
  if d == 0x40 then prot = 0x1e; pri = 1 end
  if d == 0xc0 then prot = 0x3e; pri = 0 end
  if d == 0xff then prot = 0x76; pri = 1 end
  log:write(string.format("%d %.9f 0 prot %04x pri=%d\n", L.frame(), NOW(), d, pri))
end)

local function word(v) return string.char((v >> 8) & 0xff, v & 0xff) end
local function dump(f)
  local t = {}
  for c = 0, 1 do for w = 0, 7 do t[#t + 1] = word(ctl[c][w]) end end
  t[#t + 1] = L.region(0xa0000, 0xe800)
  t[#t + 1] = sprbuf
  t[#t + 1] = L.region(0xb8000, 0x1000)
  t[#t + 1] = L.region(0xb9000, 0x1000)
  t[#t + 1] = L.ram()
  -- trailer (8 bytes): m_pri, m_prot (u16), last $bc004 write (u16, 0xffff if none), frame number parity byte, frame low byte
  t[#t + 1] = string.char(pri, 0) .. word(prot) .. word(lastw < 0 and 0xffff or lastw) .. string.char(f & 1, f & 0xff)
  L.write(string.format("%s/f%05d.bin", out, f), table.concat(t))
  L.screen:snapshot(string.format("f%05d.png", f))
end

emu.register_frame_done(function()
  local f = L.frame()
  log:write(string.format("%d %.9f 0 vbl\n", f, NOW()))
  for _, e in ipairs(sched) do if e[1] == f then L.F[e[2]]:set_value(e[3]) end end
  for _, p in ipairs(pokes) do
    if p[1] == f then
      for i = 0, p[4] - 1 do
        local b = (p[3] >> (8 * (p[4] - 1 - i))) & 0xff
        if p[5] == "o" then b = b | mem:read_u8(p[2] + i)          -- ":o" suffix: OR into the byte instead of storing
        elseif p[5] == "c" then b = mem:read_u8(p[2] + i) & ~b end  -- ":c": clear those bits
        mem:write_u8(p[2] + i, b)
      end
    end
  end
  if want[f] then dump(f) end
  if f >= stop then log:close(); manager.machine:exit() end
end)
