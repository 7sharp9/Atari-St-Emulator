#!/bin/zsh
# usage: census_walk.sh <census snap> <world index hex 2 digits>   (run from M68000/, ATARI_NOTRACE=1)
# From a poke-warped room snapshot: health poked full (labelled), then real input: hold right (joystick bit 3) and
# snapshot every 600000 steps, three times, to catch the objects the spawner brings in as the camera advances.
S=$1; B=${S:t:r}; W=scratchpad/impossamole/agents/world12
D="scratchpad/impossamole/impossamole cr replicants - emotion cr replicants.st"
{ printf 'w bb74 1212%s00\nkbd ff\nkbd 08\n' $2
  for i in 1 2 3; do printf 's 600000\nsnap %s/census2/%s_w%s.snap\n' $W $B $i; done
  printf 'kbd ff\nkbd 00\nq\n'; } | dotnet exec bin/Debug/net8.0/M68000.dll resume $S repl --disk-a "$D" > /dev/null 2>&1
