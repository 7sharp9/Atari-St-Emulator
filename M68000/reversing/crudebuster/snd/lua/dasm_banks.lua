-- MAME's own HuC6280 disassembly of every 8 KiB ROM bank (mapped at logical $e000 via MPR7), for check_mame.py.
--   CB_OUT=<dir> cbmame.sh script lua/dasm_banks.lua   -> <dir>/mame_dasm_bank<N>.txt  (N = 0..7)
local out = os.getenv("CB_OUT")
local m = manager.machine
local cpu = m.devices[":audiocpu"]
local d = m.debugger
for b = 0, 7 do
  cpu.state["MPR7"].value = b
  d:command(string.format("dasm %s/mame_dasm_bank%d.txt,e000,2000,1,:audiocpu", out, b))
end
cpu.state["MPR7"].value = 0
print("dasm banks done")
m:exit()
