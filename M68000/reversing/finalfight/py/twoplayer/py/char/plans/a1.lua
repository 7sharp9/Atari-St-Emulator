-- a1: no enemies. move set on the ground and in the air
local t = {}
local function hold(f, fields, n) for _, fl in ipairs(type(fields)=="table" and fields or {fields}) do t[#t+1] = {f, fl, 1}; t[#t+1] = {f+n, fl, 0} end end
hold(20, "b1", 4)                      -- single punch
hold(60, "b1", 4); hold(72, "b1", 4); hold(84, "b1", 4); hold(96, "b1", 4); hold(108, "b1", 4); hold(120,"b1",4) -- chain at 12 frame intervals
hold(200, "b2", 4)                     -- vertical jump
hold(280, {"b2","right"}, 4); hold(280,"right",50) -- jump right
hold(380, {"b2"}, 4); hold(400, "b1", 4)   -- jump, then attack in air (neutral)
hold(480, {"b2","right"}, 4); hold(480,"right",50); hold(500, "b1", 4) -- forward jump kick
hold(600, "b2", 4); hold(615,"down",30); hold(620, "b1", 4)  -- jump, down, attack
hold(720, {"b1","b2"}, 4)             -- special
hold(820, "b1", 4); hold(826, "b2", 4)  -- b1 then b2 within frames: special?
hold(920, "b2", 4); hold(925, "b1", 4)
return t
