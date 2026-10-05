-- both players on low lanes: P1 ground line $20, P2 at x + FF_DX, ground line $20 + FF_DY
local dx = tonumber(os.getenv("FF_DX") or "40")
local dy = tonumber(os.getenv("FF_DY") or "0")
local P1, P2 = 0xff8568, 0xff8628
return { { 0, P1 + 14, 2, 0x20 }, { 0, P1 + 10, 2, 0x20 }, { 0, P2 + 6, 2, 0xca + dx }, { 0, P2 + 14, 2, 0x20 + dy }, { 0, P2 + 10, 2, 0x20 + dy }, { 0, P2 + 46, 1, 1 } }
