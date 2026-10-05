-- Bred (pool-2 record 12) next to player 2 (x + FF_DX, same ground line, facing the player)
local dx = tonumber(os.getenv("FF_DX") or "28")
local B = 0xff8fe8
return { { 0, B + 6, 2, 0xba + dx }, { 0, B + 10, 2, 0x20 }, { 0, B + 14, 2, 0x20 }, { 0, B + 46, 1, 1 } }
