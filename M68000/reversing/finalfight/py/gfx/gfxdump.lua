-- gfxdump.lua: load a saved state, then for each of the next FF_FRAMES frames (default 3) write
--   <FF_OUT>/<tag>_<k>_gfxram.bin  (gfx RAM $900000-$92ffff, 0x30000)
--   <FF_OUT>/<tag>_<k>_ram.bin     (work RAM $ff0000-$ffffff)
--   <FF_OUT>/<tag>_<k>_regs.bin    (CPS-A $800100-$80013f then CPS-B $800140-$80017f as the chip holds them, 32+32
--                                   big-endian words, read from the driver's shared regs m_cps_a_regs/m_cps_b_regs)
--   <FF_OUT>/<tag>_<k>_pens.bin    (the live palette, 0xc00 x RGB bytes, from MAME's palette device)
--   snapshot <tag>_<k>.png         (MAME screenshot, 384x224, into the -snapshot_directory)
-- k=1 is the frame of the state itself (resume_check.lua: the first callback after a load shows the saved frame).
-- Env: FF_POKE (see below), FF_DIR (lua dir with lib.lua), FF_OUT, FF_LOAD (state name), FF_TAG, FF_FRAMES.
-- Run: FF_LOAD=ff_gameplay FF_TAG=gp ../../ffrun.sh $PWD/gfxdump.lua 400   (seconds must exceed state frame / 59.6)
local L = dofile(os.getenv("FF_DIR") .. "/lib.lua")
local name = assert(os.getenv("FF_LOAD"), "FF_LOAD")
local tag = os.getenv("FF_TAG") or name
local out = assert(os.getenv("FF_OUT"), "FF_OUT")
local nframes = tonumber(os.getenv("FF_FRAMES") or "3")
local sh = manager.machine.memory.shares
local ra, rb = sh[":cps_a_regs"], sh[":cps_b_regs"]
assert(ra and rb, "cps regs shares not found")
local function regs()
  local t = {}
  for i = 0, 31 do local v = ra:read_u16(i * 2); t[#t + 1] = string.char(v >> 8, v & 0xff) end
  for i = 0, 31 do local v = rb:read_u16(i * 2); t[#t + 1] = string.char(v >> 8, v & 0xff) end
  return table.concat(t)
end
local pdev = manager.machine.palettes[":palette"]
assert(pdev, "palette device not found")
local function pens()   -- the chip's real palette: 0xc00 pens as 3 bytes R,G,B (what cps1_build_palette last installed)
  local t = {}
  for i = 0, 0xbff do
    local c = pdev.palette:entry_color(i)
    t[#t + 1] = string.char((c >> 16) & 0xff, (c >> 8) & 0xff, c & 0xff)
  end
  return table.concat(t)
end
-- FF_POKE="ff806e=12c8,ff8070=12c8": u16 pokes into the main space, applied once after the load (frame k=1)
local pokes = {}
for a, v in string.gmatch(os.getenv("FF_POKE") or "", "(%x+)=(%x+)") do pokes[#pokes + 1] = {tonumber(a, 16), tonumber(v, 16)} end
local issued, n = false, 0
emu.register_frame_done(function()
  if not issued then
    issued = true
    manager.machine:load(name)
    return
  end
  n = n + 1
  if n == 1 then for _, e in ipairs(pokes) do L.mem:write_u16(e[1], e[2]) end end
  local p = string.format("%s/%s_%d", out, tag, n)
  L.write(p .. "_gfxram.bin", L.region(0x900000, 0x30000))
  L.write(p .. "_ram.bin", L.ram())
  L.write(p .. "_regs.bin", regs())
  L.write(p .. "_pens.bin", pens())
  L.screen:snapshot(string.format("%s_%d.png", tag, n))
  if n >= nframes then manager.machine:exit() end
end)
