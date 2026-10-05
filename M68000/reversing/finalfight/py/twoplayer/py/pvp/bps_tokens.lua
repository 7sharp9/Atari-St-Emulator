-- breakpoints on the token request $27b5a: entry (rank 168(A5) = $ff80a8, 127(A5) = $ff807f, tokens $ff115a) and the three exits (D0 = 0 refused at $27b74/$27b84, granted through $27c1e)
return {
  { "27b5a", 'w@ff80a8, b@ff807f, w@ff115a', "E rank=%d m127=%d tok=%d" },
  { "27b74", nil, "R0 1P" },
  { "27b84", nil, "R0 2P" },
  { "27c1e", 'd0', "R1 d0=%d" },
}
