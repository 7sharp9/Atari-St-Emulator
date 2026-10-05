-- Dump MAME's own gfx regions (tiles1, tiles2, sprites) as loaded from the zip: ground truth for the ROM interleave.
--   CB_OUT=<dir> cbmame.sh script lua/dump_regions.lua
local out = os.getenv("CB_OUT") or "."
local regs = manager.machine.memory.regions
for _, name in ipairs({":tiles1", ":tiles2", ":sprites"}) do
  local r = regs[name]
  local f = assert(io.open(out .. "/region" .. name:gsub(":", "_") .. ".bin", "wb"))
  local t = {}
  for a = 0, r.size - 1 do t[#t + 1] = string.char(r:read_u8(a)) if #t >= 65536 then f:write(table.concat(t)); t = {} end end
  f:write(table.concat(t)); f:close()
  print(name, r.size, r.endianness, r.bitwidth)
end
manager.machine:exit()
