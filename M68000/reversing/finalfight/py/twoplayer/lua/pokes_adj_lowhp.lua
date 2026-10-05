local dx = tonumber(os.getenv("FF_DX") or "40")
local P2 = 0xff8628
return { { 0, P2 + 6, 2, 0xca + dx }, { 0, P2 + 14, 2, 0x3c }, { 0, P2 + 10, 2, 0x3c }, { 0, P2 + 46, 1, 1 }, { 0, P2 + 24, 2, 0 }, { 0, P2 + 26, 2, 0 } }
