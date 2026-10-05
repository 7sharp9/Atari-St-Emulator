-- Dump the decrypted program ROM and the HuC6280 code of the running set.
--   CB_OUT=<dir> cbmame.sh script lua/dumprom.lua
local out = os.getenv("CB_OUT")
local set = manager.machine.system.name
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local f = io.open(out .. "/" .. set .. "_main.bin", "wb")
for a = 0, 0x7ffff do f:write(string.char(mem:read_u8(a))) end
f:close()
local sp = manager.machine.devices[":audiocpu"].spaces["program"]
local g = io.open(out .. "/" .. set .. "_huc.bin", "wb")
for a = 0, 0xffff do g:write(string.char(sp:read_u8(a))) end
g:close()
-- ioport field names for the input scripts
local h = io.open(out .. "/" .. set .. "_ioport.txt", "w")
for tag, p in pairs(manager.machine.ioport.ports) do
  for name, fld in pairs(p.fields) do h:write(string.format("%s\t%s\tmask=%04x\n", tag, name, fld.mask)) end
end
h:close()
print("dumped " .. set)
manager.machine:exit()
