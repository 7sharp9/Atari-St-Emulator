-- $50e: writes D0+$4400 to 32 words at $908500, stride 4, when 142(A5)==0, 132(A5)!=0, bit 6 of
-- 100(A5) set (A5 = $ff8000). Expected: 32 mem runs of "4453" in gfx RAM, no register change
-- beyond D0/D7/A0 scratch.
return {
  addr = 0x50e,
  warm = 600,
  regs = { D0 = 0x53, A5 = 0xff8000 },
  pokes = { {0xff808e, 0}, {0xff8084, 1}, {0xff8064, 0x40} },
}
