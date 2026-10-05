local mem = manager.machine.devices[":maincpu"].spaces["program"]
local f = io.open(os.getenv("FF_OUT") .. "/ff_main.bin", "wb")
for a = 0, 0x0fffff do f:write(string.char(mem:read_u8(a))) end
f:close()
local sp = manager.machine.devices[":audiocpu"].spaces["program"]
local g = io.open(os.getenv("FF_OUT") .. "/ff_z80.bin", "wb")
for a = 0, 0x7fff do g:write(string.char(sp:read_u8(a))) end
g:close()
print("dumped")
manager.machine:exit()
