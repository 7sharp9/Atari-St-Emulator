-- P2 next to P1 at x + FF_DX, ground line (and y) + FF_DY (signed)
local dx = tonumber(os.getenv("FF_DX") or "40")
local dy = tonumber(os.getenv("FF_DY") or "0")
local P2 = 0xff8628
return { { 0, P2 + 6, 2, 0xca + dx }, { 0, P2 + 14, 2, 0x3c + dy }, { 0, P2 + 10, 2, 0x3c + dy }, { 0, P2 + 46, 1, 1 } }
