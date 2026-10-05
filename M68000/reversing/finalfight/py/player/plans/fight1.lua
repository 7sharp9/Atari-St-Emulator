local t = {}
for f = 10, 700, 14 do t[#t+1] = {f, "b1", 1}; t[#t+1] = {f+5, "b1", 0} end
return t
