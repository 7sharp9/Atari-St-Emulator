#!/bin/bash
# usage: census.sh <snap>   (from M68000/) hits census of the fsm15 handler entries over 60M steps; writes $WORK/census/<dir>_<snap>.txt
mkdir -p scratchpad/pm141/agents/fsm15/census
s=$1; n=$(basename $s .snap); d=$(basename $(dirname $s))
echo "hits 60000000 14ff8 1501a 15042 150b0 150c0 15122 1515c 15170 1518a 151a8 151c2 15200 15264 15282 152f8 15302 1533c 153b2 153cc 1540c 1547e 15518 15598 155ac 15680 156be 156e0 15724 15736 15740 15754 15772 1578c 157a0 157ba 157e6 158da 1597a 15a0e 15a60 15a80 15ad2 15b5e 15b94 15bec 15bfc 15c46 15d66 15ddc 15e30 15eb0 15eee 15f80 15f96 16044 16048 1605a 160d6 160e0 160e4 160f2 16176 161b2 161bc 159a4 159de 15fa8 160f8 16808 16848" | ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume $s repl --disk-a scratchpad/powermonger.st > scratchpad/pm141/agents/fsm15/census/${d}_$n.txt 2>&1
