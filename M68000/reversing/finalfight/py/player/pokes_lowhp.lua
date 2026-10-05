-- Cody hp = FF_CHP (default 3), no grapple link, props removed; dummy handled by extra_dummy
local h = tonumber(os.getenv("FF_CHP") or "3")
return {
 {0, 0xff85a8, 1, 0}, {0, 0xff85aa, 1, 0}, {0, 0xff856b, 1, 0}, {0, 0xff856c, 1, 0},
 {0, 0xff8580, 2, h}, {0, 0xff8582, 2, h},
 {0, 0xffba68, 1, 0}, {0, 0xffbbe8, 1, 0}, {0, 0xffbca8, 1, 0}, {0, 0xffbd68, 1, 0},
}
