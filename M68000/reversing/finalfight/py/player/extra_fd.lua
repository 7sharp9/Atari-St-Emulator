-- follow-prop + dummy enemy together
local fol = dofile(os.getenv("PD") .. "/extra_follow.lua")
local dum = dofile(os.getenv("PD") .. "/extra_dummy.lua")
return function(f, rel, m, out)
  fol(f, rel, m, out)
  dum(f, rel, m, out)
end
