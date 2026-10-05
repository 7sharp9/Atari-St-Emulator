-- FFD_EXTRA: from the loaded state, set 127(A5) to FF_P127 (hex) once, clear Cody's grapple fields left in ff_enemies (+64, +66, +3, +4)
local v = tonumber(os.getenv("FF_P127") or "", 16)
local done = false
return function(f, L, bots)
  if not bots.loaded or done then return end
  done = true
  if v then L.mem:write_u8(0xff8000 + 127, v) end
  local P = 0xff8568
  L.mem:write_u8(P + 64, 0); L.mem:write_u8(P + 66, 0); L.mem:write_u8(P + 3, 0); L.mem:write_u8(P + 4, 0)
end
