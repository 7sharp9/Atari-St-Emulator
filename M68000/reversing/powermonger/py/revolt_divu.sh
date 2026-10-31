#!/usr/bin/env bash
# usage: revolt_divu.sh   (run from M68000/; output in ${PM_WORK:-scratchpad/pm168}/divu/)
# The heartbeat revolt's side, $158b6: move.b 8(A1),D0 / divu #4,D0 sets only D0's low byte, so a high word >= 4
# overflows the quotient, D0 stays as it was and the side handed to $550e is (high word + 1) & $ff. On the heartbeat
# path that high word is 0 (mulu at $15806) unless the Ruin rebuild $15846 ran on the same pulse (D0 = cell/10 : cell%10).
# From rand1 + 90,080,900 steps, stop at $15826 (man $53d94, settlement $4fe14, cell 4513, lord 12 at $4e694), poke:
#   settlement byte 7 := $0a (a Ruin, $4fe18 00 04 02 0b -> 00 04 02 0a), lord loyalty := 600 ($4e6a0 0000012c -> 00000258),
#   man byte 14 := $1f (14(A1)&3 = 3: no jsr $5cde on the fed arm; $53da0 ead71d00 -> ead71f00),
#   settlement byte 16 := $77 (test: the rebuild completes this pulse) or $70 (control).
# Expect test: D0 $01c30021 at $158ba, side $c4 at $158cc, lord byte 0 and settlement byte 5 $c4; control: side 2.
D=${PM_WORK:-scratchpad/pm168}/divu; mkdir -p $D
run() { ATARI_NOTRACE=1 dotnet exec bin/Debug/net8.0/M68000.dll resume "$1" repl --disk-a scratchpad/powermonger.st < "$2" > "$3" 2>&1; }
printf 's 90080900\nbp 15826 2000\nsnap %s/p15826.snap\nq\n' $D > $D/stop.repl
run scratchpad/pm142/rand1.snap $D/stop.repl $D/stop.out
for arm in test ctl; do
  c=77; [ $arm = ctl ] && c=70
  printf 'w 4fe18 0004020a\nw 4fe24 %s000000\nw 4e6a0 00000258\nw 53da0 ead71f00\nbp 158ba 2000\nbp 158cc 200\nu 158d2 200000\nm 4e694 1\nm 4fe14 8\nhits 20000000 6522\nm 4e694 1\nq\n' $c > $D/$arm.repl
  run $D/p15826.snap $D/$arm.repl $D/$arm.out
  echo "$arm: D0 at 158ba $(grep -A8 'breakpoint $000158ba' $D/$arm.out | grep -o 'D0:[0-9a-f]*'), at 158cc $(grep -A8 'breakpoint $000158cc' $D/$arm.out | grep -o 'D0:[0-9a-f]*');" \
       "lord byte 0, settlement bytes 0..7, ticks over 20M, lord byte 0 after:" $(grep -E '^[0-9a-f]{2}( [0-9a-f]{2})*$|^  \$006522' $D/$arm.out | tr '\n' '|')
done
