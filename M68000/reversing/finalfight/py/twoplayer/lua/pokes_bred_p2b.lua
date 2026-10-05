local dx = tonumber(os.getenv("FF_DX") or "28")
local B = 0xff8fe8
return { { 0, B + 6, 2, 0x1a6 + dx }, { 0, B + 10, 2, 0x3b }, { 0, B + 14, 2, 0x3b }, { 0, B + 46, 1, 1 }, { 0, 0xff8628 + 46, 1, 0 } }
