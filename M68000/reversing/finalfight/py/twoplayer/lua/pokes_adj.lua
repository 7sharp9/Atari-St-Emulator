-- P2 next to P1 on the same ground line: x + FF_DX (default 40), facing left
local dx = tonumber(os.getenv("FF_DX") or "40")
local P1, P2 = 0xff8568, 0xff8628
return { { 0, P2 + 6, 2, 0xca + dx }, { 0, P2 + 14, 2, 0x3c }, { 0, P2 + 10, 2, 0x3c }, { 0, P2 + 46, 1, 1 } }
