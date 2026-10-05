-- FFD_EXTRA: every frame poke the token counter $ff115a, the rank 168(A5) and 127(A5) from a deterministic cycle so that the natural calls of $27b5a sample many (tok, rank, mask) triples.
-- (the poke is applied at frame end; the breakpoint log records the values the routine really saw)
local ranks = { 0, 3, 5, 6, 7, 9, 12, 13, 18, 19, 25, 29, 30, 31 }
local seed = tonumber(os.getenv("FF_FUZZ_SEED") or "1")
local function rnd(n) seed = (seed * 1103515245 + 12345) & 0x7fffffff; return (seed >> 16) % n end
local done = false
return function(f, L, bots)
  if not bots.loaded then return end
  local m = L.mem
  if not done then done = true; local P = 0xff8568; m:write_u8(P + 64, 0); m:write_u8(P + 66, 0); m:write_u8(P + 3, 0); m:write_u8(P + 4, 0) end
  m:write_u16(0xff115a, rnd(9))
  m:write_u16(0xff8000 + 168, ranks[1 + rnd(#ranks)])
  m:write_u8(0xff8000 + 127, (rnd(2) == 0) and 1 or 3)
end
