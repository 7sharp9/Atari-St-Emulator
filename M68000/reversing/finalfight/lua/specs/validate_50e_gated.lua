-- Negative control for validate_50e.lua: 142(A5) != 0 makes $50e return at once, so the diff
-- must be empty (no gfx RAM writes, A0/D7 untouched).
return {
  addr = 0x50e,
  warm = 600,
  regs = { D0 = 0x53, A5 = 0xff8000 },
  pokes = { {0xff808e, 1}, {0xff8084, 1}, {0xff8064, 0x40} },
}
