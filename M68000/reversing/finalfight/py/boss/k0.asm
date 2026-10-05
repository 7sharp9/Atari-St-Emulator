L3d3d6:
  $03d3d6: move.b 2(A6),D0
  $03d3da: move.w 6(PC,D0.w) == $3d3e2+D0,D1
  $03d3de: jmp 2(PC,D1.w) == $3d3e2+D1
  ; ---- gap 3d3e2..3d3ea (8 bytes) ----
L3d3ea:
  $03d3ea: move.b 3(A6),D0
  $03d3ee: move.w 6(PC,D0.w) == $3d3f6+D0,D1
  $03d3f2: jmp 2(PC,D1.w) == $3d3f6+D1
  ; ---- gap 3d3f6..3d3fe (8 bytes) ----
L3d3fe:
  $03d3fe: cmpi.w #$aa0,1042(A5)
  $03d404: bcs $3d428
  $03d406: move.w A6,302(A5)
  $03d40a: addq.b #2,3(A6)
  $03d40e: jsr $3946.w
  $03d412: bne $3d428
  $03d414: move.b #$1,0(A4)
  $03d41a: move.b #$1e,19(A4)
  $03d420: move.l A6,128(A4)
  $03d424: clr.b -27896(A5)
L3d428:
  $03d428: rts
L3d42a:
  $03d42a: addq.b #2,3(A6)
  $03d42e: move.b #$40,30(A6)
  $03d434: move.l 10(A6),14(A6)
  $03d43a: move.b #$1,46(A6)
  $03d440: move.b #$1,-27936(A5)
  $03d446: move.w 168(A5),D0
  $03d44a: move.b D0,96(A6)
  $03d44e: bsr $40a8c
  $03d452: jsr $2fa2.w
  $03d456: move.w #$12c,D1
  $03d45a: move.b 21610(A5),D0
  $03d45e: cmpi.b #$3,D0
  $03d462: bne $3d468
  $03d464: move.w #$1c2,D1
L3d468:
  $03d468: move.w D1,28(A6)
  $03d46c: move.w D1,26(A6)
  $03d470: move.w D1,24(A6)
  $03d474: move.b D0,163(A6)
  $03d478: clr.b 149(A6)
  $03d47c: clr.b 148(A6)
  $03d480: clr.b 169(A6)
  $03d484: clr.b 160(A6)
  $03d488: clr.b 174(A6)
  $03d48c: clr.b 161(A6)
  $03d490: clr.b 164(A6)
  $03d494: clr.b 165(A6)
  $03d498: clr.b 168(A6)
  $03d49c: move.b #$28,97(A6)
  $03d4a2: move.w #$17,D0
  $03d4a6: jsr $9e4.w
  $03d4aa: move.b #$1,D2
  $03d4ae: move.w #$b90,D3
  $03d4b2: move.w #$98,D4
  $03d4b6: jsr $466a.w
  $03d4ba: move.b #$0,D2
  $03d4be: move.w #$ba0,D3
  $03d4c2: move.w #$98,D4
  $03d4c6: jsr $466a.w
  $03d4ca: move.b #$1,D2
  $03d4ce: move.w #$b78,D3
  $03d4d2: move.w #$78,D4
  $03d4d6: jsr $466a.w
  $03d4da: move.b #$0,D2
  $03d4de: move.w #$bb8,D3
  $03d4e2: move.w #$78,D4
  $03d4e6: jsr $466a.w
  $03d4ea: bsr $3f2aa
  $03d4ee: bra $3f322
L3d4f2:
  $03d4f2: jsr $3b3c.w
  $03d4f6: tst.b 41(A6)
  $03d4fa: bne $3d50a
  $03d4fc: move.b 167(A5),D0
  $03d500: andi.b #$1,D0
  $03d504: bne $3d50e
  $03d506: jmp $32a2.w
L3d50a:
  $03d50a: addq.b #2,3(A6)
L3d50e:
  $03d50e: rts
L3d510:
  $03d510: addq.b #2,2(A6)
  $03d514: move.b #$2,3(A6)
  $03d51a: move.b 163(A6),D0
  $03d51e: add.w D0,D0
  $03d520: move.w 14(PC,D0.w) == $3d530+D0,D1
  $03d524: jsr 10(PC,D1.w) == $3d530+D1
  $03d528: bsr $3f2bc
  $03d52c: jmp $32a2.w
  ; ---- gap 3d530..3d538 (8 bytes) ----
L3d538:
  $03d538: clr.b 2(A6)
  $03d53c: move.b #$6,3(A6)
  $03d542: rts
L3d544:
  $03d544: clr.b 138(A6)
  $03d548: lea 1384(A5),A0
  $03d54c: move.l A0,128(A6)
  $03d550: rts
L3d552:
  $03d552: move.b #$1,138(A6)
  $03d558: lea 1576(A5),A0
  $03d55c: move.l A0,128(A6)
  $03d560: rts
L3d562:
  $03d562: bsr $40922
  $03d566: move.b D3,138(A6)
  $03d56a: move.l A0,128(A6)
  $03d56e: rts
L3d570:
  $03d570: jsr $412a.w
  $03d574: tst.b 66(A6)
  $03d578: bne $3ea38
  $03d57c: move.b 3(A6),D0
  $03d580: move.w 54(PC,D0.w) == $3d5b8+D0,D1
  $03d584: jsr 50(PC,D1.w) == $3d5b8+D1
  $03d588: bsr $3ed58
  $03d58c: move.b 167(A5),D0
  $03d590: andi.b #$f,D0
  $03d594: bne $3d5a2
  $03d596: bsr $40a8c
  $03d59a: jsr $2fd4.w
  $03d59e: bsr $408ec
L3d5a2:
  $03d5a2: move.w 168(A5),D0
  $03d5a6: move.b D0,96(A6)
  $03d5aa: tst.b 97(A6)
  $03d5ae: beq $3d5b4
  $03d5b0: subq.b #1,97(A6)
L3d5b4:
  $03d5b4: jmp $32aa.w
  ; ---- gap 3d5b8..3d5d2 (26 bytes) ----
L3d5d2:
  $03d5d2: move.b 4(A6),D0
  $03d5d6: move.w -18(PC,D0.w) == $3d5c6+D0,D1
  $03d5da: jsr -22(PC,D1.w) == $3d5c6+D1
  $03d5de: moveq #0,D0
  $03d5e0: move.b 21610(A5),D0
  $03d5e4: add.w D0,D0
  $03d5e6: move.w 18(PC,D0.w) == $3d5fa+D0,D1
  $03d5ea: jsr 14(PC,D1.w) == $3d5fa+D1
  $03d5ee: tst.b 174(A6)
  $03d5f2: bne $3d5f8
  $03d5f4: bra $3edbe
L3d5f8:
  $03d5f8: rts
  ; ---- gap 3d5fa..3d602 (8 bytes) ----
L3d602:
  $03d602: rts
L3d604:
  $03d604: move.b #$b4,136(A6)
  $03d60a: move.b #$f0,137(A6)
  $03d610: tst.b 138(A6)
  $03d614: beq $3d624
  $03d616: move.b #$0,138(A6)
  $03d61c: lea 1384(A5),A0
  $03d620: move.l A0,128(A6)
L3d624:
  $03d624: rts
L3d626:
  $03d626: move.b #$b4,136(A6)
  $03d62c: move.b #$f0,137(A6)
  $03d632: tst.b 138(A6)
  $03d636: bne $3d646
  $03d638: move.b #$1,138(A6)
  $03d63e: lea 1576(A5),A0
  $03d642: move.l A0,128(A6)
L3d646:
  $03d646: rts
L3d648:
  $03d648: move.b 167(A5),D0
  $03d64c: andi.b #$f,D0
  $03d650: bne $3d658
  $03d652: bsr $40aa6
  $03d656: bne $3d674
L3d658:
  $03d658: tst.b 136(A6)
  $03d65c: beq $3d664
  $03d65e: subq.b #1,136(A6)
  $03d662: bne $3d692
L3d664:
  $03d664: tst.b 137(A6)
  $03d668: beq $3d670
  $03d66a: subq.b #1,137(A6)
  $03d66e: bne $3d692
L3d670:
  $03d670: bsr $40922
L3d674:
  $03d674: move.b #$b4,136(A6)
  $03d67a: cmp.b 138(A6),D3
  $03d67e: bne $3d684
  $03d680: clr.b 136(A6)
L3d684:
  $03d684: move.b D3,138(A6)
  $03d688: move.l A0,128(A6)
  $03d68c: move.b #$f0,137(A6)
L3d692:
  $03d692: rts
L3d694:
  $03d694: addq.b #2,4(A6)
  $03d698: bsr $3f2bc
  $03d69c: bra $40940
L3d6a0:
  $03d6a0: addq.b #2,4(A6)
  $03d6a4: jsr $3c26.w
  $03d6a8: andi.w #$1f,D0
  $03d6ac: move.b 22(PC,D0.w) == $3d6c4+D0,D0
  $03d6b0: move.b D0,140(A6)
  $03d6b4: add.w D0,D0
  $03d6b6: move.w 44(PC,D0.w) == $3d6e4+D0,D0
  $03d6ba: lea 40(PC,D0.w) == $3d6e4+D0,A0
  $03d6be: move.l A0,142(A6)
  $03d6c2: rts
  ; ---- gap 3d6c4..3d732 (110 bytes) ----
L3d732:
  $03d732: movea.l 142(A6),A0
  $03d736: move.b (A0)+,141(A6)
  $03d73a: bpl $3d742
  $03d73c: addq.b #4,4(A6)
  $03d740: rts
L3d742:
  $03d742: addq.b #2,4(A6)
  $03d746: move.l A0,142(A6)
  $03d74a: rts
L3d74c:
  $03d74c: move.b 141(A6),D0
  $03d750: move.w 6(PC,D0.w) == $3d758+D0,D1
  $03d754: jmp 2(PC,D1.w) == $3d758+D1
  ; ---- gap 3d758..3d760 (8 bytes) ----
L3d760:
  $03d760: move.b 5(A6),D0
  $03d764: move.w 6(PC,D0.w) == $3d76c+D0,D1
  $03d768: jmp 2(PC,D1.w) == $3d76c+D1
  ; ---- gap 3d76c..3d778 (12 bytes) ----
L3d778:
  $03d778: addq.b #2,5(A6)
  $03d77c: move.b #$1,174(A6)
  $03d782: move.b #$1,-27896(A5)
  $03d788: bra $3f2c4
L3d78c:
  $03d78c: jsr $3b3c.w
  $03d790: tst.b 41(A6)
  $03d794: bne $3d7a8
  $03d796: addq.b #2,5(A6)
  $03d79a: move.l #$3f26a,50(A6)
  $03d7a2: move.w #$340,86(A6)
L3d7a8:
  $03d7a8: rts
L3d7aa:
  $03d7aa: bsr $40bac
  $03d7ae: moveq #0,D0
  $03d7b0: move.w 86(A6),D0
  $03d7b4: lsl.l #8,D0
  $03d7b6: add.l D0,10(A6)
  $03d7ba: subi.w #$50,86(A6)
  $03d7c0: bpl $3d7ca
  $03d7c2: clr.w 86(A6)
  $03d7c6: addq.b #2,5(A6)
L3d7ca:
  $03d7ca: bsr $40b5e
  $03d7ce: jmp $3b3c.w
L3d7d2:
  $03d7d2: bsr $40bac
  $03d7d6: moveq #0,D0
  $03d7d8: move.w 86(A6),D0
  $03d7dc: lsl.l #8,D0
  $03d7de: sub.l D0,10(A6)
  $03d7e2: addi.w #$50,86(A6)
  $03d7e8: cmpi.w #$600,86(A6)
  $03d7ee: bls $3d7f6
  $03d7f0: move.w #$600,86(A6)
L3d7f6:
  $03d7f6: bsr $40b5e
  $03d7fa: move.w 10(A6),D0
  $03d7fe: cmp.w 14(A6),D0
  $03d802: bhi $3d81a
  $03d804: addq.b #2,5(A6)
  $03d808: move.l 14(A6),10(A6)
  $03d80e: clr.b -27896(A5)
  $03d812: clr.b 174(A6)
  $03d816: bra $3f2bc
L3d81a:
  $03d81a: jmp $3b3c.w
L3d81e:
  $03d81e: move.b 5(A6),D0
  $03d822: move.w 6(PC,D0.w) == $3d82a+D0,D1
  $03d826: jmp 2(PC,D1.w) == $3d82a+D1
  ; ---- gap 3d82a..3d838 (14 bytes) ----
L3d838:
  $03d838: addq.b #2,5(A6)
  $03d83c: move.b #$1,174(A6)
  $03d842: move.b #$1,-27896(A5)
  $03d848: bra $3f2cc
L3d84c:
  $03d84c: jsr $3b3c.w
  $03d850: tst.b 41(A6)
  $03d854: bne $3d868
  $03d856: addq.b #2,5(A6)
  $03d85a: move.l #$3f22a,50(A6)
  $03d862: move.w #$5c0,86(A6)
L3d868:
  $03d868: rts
L3d86a:
  $03d86a: bsr $40bac
  $03d86e: moveq #0,D0
  $03d870: move.w 86(A6),D0
  $03d874: lsl.l #8,D0
  $03d876: add.l D0,10(A6)
  $03d87a: subi.w #$50,86(A6)
  $03d880: bpl $3d88a
  $03d882: clr.w 86(A6)
  $03d886: addq.b #2,5(A6)
L3d88a:
  $03d88a: bsr $40b5e
  $03d88e: jmp $3b3c.w
L3d892:
  $03d892: bsr $40bac
  $03d896: moveq #0,D0
  $03d898: move.w 86(A6),D0
  $03d89c: lsl.l #8,D0
  $03d89e: sub.l D0,10(A6)
  $03d8a2: addi.w #$50,86(A6)
  $03d8a8: cmpi.w #$600,86(A6)
  $03d8ae: bls $3d8b6
  $03d8b0: move.w #$600,86(A6)
L3d8b6:
  $03d8b6: bsr $40b5e
  $03d8ba: move.w 10(A6),D0
  $03d8be: cmp.w 14(A6),D0
  $03d8c2: bhi $3d8da
  $03d8c4: addq.b #2,5(A6)
  $03d8c8: move.l 14(A6),10(A6)
  $03d8ce: clr.b -27896(A5)
  $03d8d2: clr.b 174(A6)
  $03d8d6: bra $3f2d4
L3d8da:
  $03d8da: jmp $3b3c.w
L3d8de:
  $03d8de: jsr $3b3c.w
  $03d8e2: tst.b 41(A6)
  $03d8e6: beq $3d8f0
  $03d8e8: addq.b #2,5(A6)
  $03d8ec: bra $3f2bc
L3d8f0:
  $03d8f0: rts
L3d8f2:
  $03d8f2: move.b 5(A6),D0
  $03d8f6: move.w 6(PC,D0.w) == $3d8fe+D0,D1
  $03d8fa: jmp 2(PC,D1.w) == $3d8fe+D1
  ; ---- gap 3d8fe..3d906 (8 bytes) ----
L3d906:
  $03d906: addq.b #2,5(A6)
  $03d90a: move.b #$3c,30(A6)
  $03d910: rts
L3d912:
  $03d912: move.b 5(A6),D0
  $03d916: move.w 6(PC,D0.w) == $3d91e+D0,D1
  $03d91a: jmp 2(PC,D1.w) == $3d91e+D1
  ; ---- gap 3d91e..3d926 (8 bytes) ----
L3d926:
  $03d926: addq.b #2,5(A6)
  $03d92a: move.b #$78,30(A6)
  $03d930: rts
L3d932:
  $03d932: subq.b #1,30(A6)
  $03d936: beq $3d94e
  $03d938: move.b 167(A5),D0
  $03d93c: andi.b #$f,D0
  $03d940: bne $3d946
  $03d942: bsr $40b92
L3d946:
  $03d946: bsr $4083a
  $03d94a: bne $3d94e
  $03d94c: rts
L3d94e:
  $03d94e: addq.b #2,5(A6)
  $03d952: rts
L3d954:
  $03d954: bsr $40b92
  $03d958: movea.l 142(A6),A0
  $03d95c: tst.b (A0)
  $03d95e: bmi $3d99a
  $03d960: addq.b #2,5(A6)
  $03d964: jsr $3c26.w
  $03d968: andi.w #$1f,D0
  $03d96c: move.b 6(PC,D0.w) == $3d974+D0,30(A6)
  $03d972: rts
  ; ---- gap 3d974..3d994 (32 bytes) ----
L3d994:
  $03d994: subq.b #1,30(A6)
  $03d998: bne $3d9a8
L3d99a:
  $03d99a: clr.b 5(A6)
  $03d99e: move.b #$4,4(A6)
  $03d9a4: bsr $40954
L3d9a8:
  $03d9a8: rts
L3d9aa:
  $03d9aa: move.b 5(A6),D0
  $03d9ae: move.w 6(PC,D0.w) == $3d9b6+D0,D1
  $03d9b2: jmp 2(PC,D1.w) == $3d9b6+D1
  ; ---- gap 3d9b6..3d9ba (4 bytes) ----
L3d9ba:
  $03d9ba: addq.b #2,5(A6)
  $03d9be: jsr $3c26.w
  $03d9c2: andi.w #$1f,D0
  $03d9c6: move.b 6(PC,D0.w) == $3d9ce+D0,30(A6)
  $03d9cc: rts
  ; ---- gap 3d9ce..3d9ee (32 bytes) ----
L3d9ee:
  $03d9ee: subq.b #1,30(A6)
  $03d9f2: bne $3da18
  $03d9f4: addq.b #2,4(A6)
  $03d9f8: clr.b 5(A6)
  $03d9fc: lea 28(PC) == $3da1a,A1
  $03da00: tst.b 148(A6)
  $03da04: beq $3da0a
  $03da06: lea 82(PC) == $3da5a,A1
L3da0a:
  $03da0a: jsr $3c26.w
  $03da0e: andi.w #$3e,D0
  $03da12: move.w 0(A1,D0.w),146(A6)
L3da18:
  $03da18: rts
  ; ---- gap 3da1a..3da9a (128 bytes) ----
L3da9a:
  $03da9a: move.b 5(A6),D0
  $03da9e: move.w 44(PC,D0.w) == $3dacc+D0,D1
  $03daa2: jsr 40(PC,D1.w) == $3dacc+D1
  $03daa6: move.b 167(A5),D0
  $03daaa: andi.b #$f,D0
  $03daae: bne $3dab4
  $03dab0: bsr $40b92
L3dab4:
  $03dab4: subq.w #1,146(A6)
  $03dab8: bne $3daca
  $03daba: clr.b 5(A6)
  $03dabe: clr.b 4(A6)
  $03dac2: move.b #$2,3(A6)
  $03dac8: rts
L3daca:
  $03daca: rts
  ; ---- gap 3dacc..3dad2 (6 bytes) ----
L3dad2:
  $03dad2: addq.b #2,5(A6)
  $03dad6: move.b #$1,30(A6)
  $03dadc: rts
L3dade:
  $03dade: subq.b #1,30(A6)
  $03dae2: bne $3db08
  $03dae4: clr.b 5(A6)
  $03dae8: jsr $3c26.w
  $03daec: andi.b #$f,D0
  $03daf0: move.w #$ffff,D1
  $03daf4: btst D0,D1
  $03daf6: beq $3db08
  $03daf8: move.b #$4,5(A6)
  $03dafe: move.b #$78,30(A6)
  $03db04: bra $3f2ec
L3db08:
  $03db08: rts
L3db0a:
  $03db0a: subq.b #1,30(A6)
  $03db0e: bne $3db18
  $03db10: clr.b 5(A6)
  $03db14: bra $3f2bc
L3db18:
  $03db18: jmp $3b3c.w
  ; ---- gap 3db1c..3db26 (10 bytes) ----
L3db26:
  $03db26: tst.b 23(A6)
  $03db2a: beq $3db36
  $03db2c: subi.b #$1,23(A6)
  $03db32: beq $3db36
  $03db34: rts
L3db36:
  $03db36: move.b 4(A6),D0
  $03db3a: move.w -32(PC,D0.w) == $3db1c+D0,D1
  $03db3e: jsr -36(PC,D1.w) == $3db1c+D1
  $03db42: tst.w 150(A6)
  $03db46: beq $3db4e
  $03db48: subq.w #1,150(A6)
  $03db4c: bne $3db56
L3db4e:
  $03db4e: tst.b 174(A6)
  $03db52: beq $3dfae
L3db56:
  $03db56: rts
  ; ---- gap 3db58..3db98 (64 bytes) ----
L3db98:
  $03db98: addq.b #2,4(A6)
  $03db9c: jsr $3c26.w
  $03dba0: andi.w #$3e,D0
  $03dba4: move.w -78(PC,D0.w) == $3db58+D0,150(A6)
  $03dbaa: jsr $3c26.w
  $03dbae: andi.w #$1f,D0
  $03dbb2: move.w D0,D1
  $03dbb4: move.b 148(A6),D0
  $03dbb8: lsl.w #5,D0
  $03dbba: add.w D1,D0
  $03dbbc: move.b 28(PC,D0.w) == $3dbda+D0,D0
  $03dbc0: move.b D0,153(A6)
  $03dbc4: add.w D0,D0
  $03dbc6: move.w 82(PC,D0.w) == $3dc1a+D0,D0
  $03dbca: lea 78(PC,D0.w) == $3dc1a+D0,A0
  $03dbce: move.l A0,154(A6)
  $03dbd2: move.b #$1,149(A6)
  $03dbd8: rts
  ; ---- gap 3dbda..3dc40 (102 bytes) ----
L3dc40:
  $03dc40: tst.b 160(A6)
  $03dc44: beq $3dc4c
  $03dc46: addq.b #2,4(A6)
  $03dc4a: rts
L3dc4c:
  $03dc4c: move.b 5(A6),D0
  $03dc50: move.w 6(PC,D0.w) == $3dc58+D0,D1
  $03dc54: jmp 2(PC,D1.w) == $3dc58+D1
  ; ---- gap 3dc58..3dc5c (4 bytes) ----
L3dc5c:
  $03dc5c: addq.b #2,5(A6)
  $03dc60: move.w #$40,D0
  $03dc64: movea.l 128(A6),A0
  $03dc68: move.w 6(A0),D1
  $03dc6c: cmp.w 6(A6),D1
  $03dc70: bcs $3dc74
  $03dc72: neg.w D0
L3dc74:
  $03dc74: move.w D0,158(A6)
  $03dc78: add.w D1,D0
  $03dc7a: move.w D0,132(A6)
  $03dc7e: move.w 14(A0),134(A6)
  $03dc84: move.w 132(A6),D3
  $03dc88: move.w 134(A6),D4
  $03dc8c: bsr $40c4e
  $03dc90: beq $3dcaa
  $03dc94: neg.w 158(A6)
  $03dc98: add.w 158(A6),D1
  $03dc9c: move.w D1,132(A6)
  $03dca0: move.w D1,D3
  $03dca2: bsr $40c4e
  $03dca6: bne $3dfae
L3dcaa:
  $03dcaa: bsr $40b92
  $03dcae: bra $3f2bc
L3dcb2:
  $03dcb2: move.b 167(A5),D0
  $03dcb6: andi.b #$7,D0
  $03dcba: bne $3dd14
  $03dcbc: bsr $40b92
  $03dcc0: cmpi.b #$3,21610(A5)
  $03dcc6: bne $3dcd6
  $03dcc8: bsr $40aa6
  $03dccc: beq $3dcd6
  $03dcce: move.b D3,138(A6)
  $03dcd2: move.l A0,128(A6)
L3dcd6:
  $03dcd6: movea.l 128(A6),A0
  $03dcda: move.w 6(A0),D0
  $03dcde: add.w 158(A6),D0
  $03dce2: move.w D0,132(A6)
  $03dce6: move.w 14(A0),134(A6)
  $03dcec: move.w 132(A6),D3
  $03dcf0: move.w 134(A6),D4
  $03dcf4: bsr $40c4e
  $03dcf8: beq $3dd14
  $03dcfc: neg.w 158(A6)
  $03dd00: move.w 6(A0),D0
  $03dd04: add.w 158(A6),D0
  $03dd08: move.w D0,132(A6)
  $03dd0c: bsr $40c4e
  $03dd10: bne $3dfae
L3dd14:
  $03dd14: bsr $40728
  $03dd18: bne $3dd2a
  $03dd1a: bsr $40bda
  $03dd1e: beq $3dd2a
  $03dd20: clr.b 5(A6)
  $03dd24: addq.b #2,4(A6)
  $03dd28: rts
L3dd2a:
  $03dd2a: bra $40c06
L3dd2e:
  $03dd2e: movea.l 128(A6),A0
  $03dd32: tst.b 137(A0)
  $03dd36: bne $3dfae
  $03dd3a: movea.l 154(A6),A0
  $03dd3e: move.b (A0)+,152(A6)
  $03dd42: bpl $3dd4a
  $03dd44: addq.b #4,4(A6)
  $03dd48: rts
L3dd4a:
  $03dd4a: addq.b #2,4(A6)
  $03dd4e: move.l A0,154(A6)
  $03dd52: bra $40b92
L3dd56:
  $03dd56: move.b 152(A6),D0
  $03dd5a: move.w 6(PC,D0.w) == $3dd62+D0,D1
  $03dd5e: jmp 2(PC,D1.w) == $3dd62+D1
  ; ---- gap 3dd62..3dd6c (10 bytes) ----
L3dd6c:
  $03dd6c: move.b 5(A6),D0
  $03dd70: move.w 6(PC,D0.w) == $3dd78+D0,D1
  $03dd74: jmp 2(PC,D1.w) == $3dd78+D1
  ; ---- gap 3dd78..3dd80 (8 bytes) ----
L3dd80:
  $03dd80: addq.b #2,5(A6)
  $03dd84: bra $3f322
L3dd88:
  $03dd88: tst.b 41(A6)
  $03dd8c: bpl $3dd9a
  $03dd8e: addq.b #2,5(A6)
  $03dd92: bsr $40b92
  $03dd96: bra $3f2bc
L3dd9a:
  $03dd9a: jmp $3b3c.w
L3dd9e:
  $03dd9e: move.b 5(A6),D0
  $03dda2: move.w 6(PC,D0.w) == $3ddaa+D0,D1
  $03dda6: jmp 2(PC,D1.w) == $3ddaa+D1
  ; ---- gap 3ddaa..3ddb2 (8 bytes) ----
L3ddb2:
  $03ddb2: addq.b #2,5(A6)
  $03ddb6: bra $3f32a
L3ddba:
  $03ddba: tst.b 41(A6)
  $03ddbe: bpl $3ddcc
  $03ddc0: addq.b #2,5(A6)
  $03ddc4: bsr $40b92
  $03ddc8: bra $3f2bc
L3ddcc:
  $03ddcc: jmp $3b3c.w
L3ddd0:
  $03ddd0: move.b 5(A6),D0
  $03ddd4: move.w 6(PC,D0.w) == $3dddc+D0,D1
  $03ddd8: jmp 2(PC,D1.w) == $3dddc+D1
  ; ---- gap 3dddc..3dde4 (8 bytes) ----
L3dde4:
  $03dde4: addq.b #2,5(A6)
  $03dde8: bra $3f332
L3ddec:
  $03ddec: tst.b 41(A6)
  $03ddf0: bpl $3ddfe
  $03ddf2: addq.b #2,5(A6)
  $03ddf6: bsr $40b92
  $03ddfa: bra $3f2bc
L3ddfe:
  $03ddfe: jmp $3b3c.w
L3de02:
  $03de02: move.b 5(A6),D0
  $03de06: move.w 6(PC,D0.w) == $3de0e+D0,D1
  $03de0a: jmp 2(PC,D1.w) == $3de0e+D1
  ; ---- gap 3de0e..3de16 (8 bytes) ----
L3de16:
  $03de16: addq.b #2,5(A6)
  $03de1a: bra $3f33a
L3de1e:
  $03de1e: tst.b 41(A6)
  $03de22: bpl $3de30
  $03de24: addq.b #2,5(A6)
  $03de28: bsr $40b92
  $03de2c: bra $3f2bc
L3de30:
  $03de30: jmp $3b3c.w
L3de34:
  $03de34: move.b 5(A6),D0
  $03de38: move.w 6(PC,D0.w) == $3de40+D0,D1
  $03de3c: jmp 2(PC,D1.w) == $3de40+D1
  ; ---- gap 3de40..3de4a (10 bytes) ----
L3de4a:
  $03de4a: addq.b #2,5(A6)
  $03de4e: move.l 10(A6),14(A6)
  $03de54: move.w #$780,84(A6)
  $03de5a: move.w #$66,86(A6)
  $03de60: move.w #$5,82(A6)
  $03de66: move.w #$1aa,80(A6)
  $03de6c: tst.b 46(A6)
  $03de70: beq $3de7a
  $03de72: neg.w 80(A6)
  $03de76: neg.w 82(A6)
L3de7a:
  $03de7a: bra $3f342
L3de7e:
  $03de7e: jsr $3b3c.w
  $03de82: tst.b 41(A6)
  $03de86: bne $3de98
  $03de88: addq.b #2,5(A6)
  $03de8c: move.b #$1,-27896(A5)
  $03de92: move.b #$1,174(A6)
L3de98:
  $03de98: rts
L3de9a:
  $03de9a: jsr $30aa.w
  $03de9e: bsr $40b5e
  $03dea2: beq $3deac
  $03dea4: clr.w 80(A6)
  $03dea8: clr.w 82(A6)
L3deac:
  $03deac: move.w 10(A6),D0
  $03deb0: cmp.w 14(A6),D0
  $03deb4: bhi $3ded0
  $03deb6: move.l 14(A6),10(A6)
  $03debc: addq.b #2,5(A6)
  $03dec0: clr.b -27896(A5)
  $03dec4: clr.b 174(A6)
  $03dec8: bsr $40b92
  $03decc: bra $3f2bc
L3ded0:
  $03ded0: jmp $3b3c.w
L3ded4:
  $03ded4: movea.l 154(A6),A0
  $03ded8: tst.b (A0)
  $03deda: bmi $3df40
  $03dede: addq.b #2,5(A6)
  $03dee2: jsr $3c26.w
  $03dee6: andi.w #$1f,D0
  $03deea: move.b 6(PC,D0.w) == $3def2+D0,30(A6)
  $03def0: rts
  ; ---- gap 3def2..3df12 (32 bytes) ----
L3df12:
  $03df12: subq.b #1,30(A6)
  $03df16: bne $3df4a
L3df18:
  $03df18: movea.l 128(A6),A0
  $03df1c: move.w 6(A0),D3
  $03df20: add.w 158(A6),D3
  $03df24: move.w D3,132(A6)
  $03df28: move.w 14(A6),D4
  $03df2c: move.w D4,134(A6)
  $03df30: bsr $40c4e
  $03df34: bne $3dfae
  $03df38: bsr $40bda
  $03df3c: beq $3dfae
L3df40:
  $03df40: clr.b 5(A6)
  $03df44: move.b #$4,4(A6)
L3df4a:
  $03df4a: rts
L3df4c:
  $03df4c: move.b 5(A6),D0
  $03df50: move.w 6(PC,D0.w) == $3df58+D0,D1
  $03df54: jmp 2(PC,D1.w) == $3df58+D1
  ; ---- gap 3df58..3df5c (4 bytes) ----
L3df5c:
  $03df5c: addq.b #2,5(A6)
  $03df60: jsr $3c26.w
  $03df64: andi.w #$1f,D0
  $03df68: move.b 8(PC,D0.w) == $3df72+D0,30(A6)
  $03df6e: bra $3f2bc
  ; ---- gap 3df72..3df92 (32 bytes) ----
L3df92:
  $03df92: subq.b #1,30(A6)
  $03df96: bne $3dfc2
  $03df98: bsr $406f2
  $03df9c: beq $3dfae
  $03df9e: clr.b 5(A6)
  $03dfa2: clr.b 4(A6)
  $03dfa6: move.b #$2,3(A6)
  $03dfac: rts
L3dfae:
  $03dfae: clr.b 160(A6)
  $03dfb2: clr.b 149(A6)
  $03dfb6: clr.b 3(A6)
  $03dfba: clr.b 4(A6)
  $03dfbe: clr.b 5(A6)
L3dfc2:
  $03dfc2: rts
L3dfc4:
  $03dfc4: move.b 4(A6),D0
  $03dfc8: move.w 6(PC,D0.w) == $3dfd0+D0,D1
  $03dfcc: jmp 2(PC,D1.w) == $3dfd0+D1
  ; ---- gap 3dfd0..3dfd6 (6 bytes) ----
L3dfd6:
  $03dfd6: addq.b #2,4(A6)
  $03dfda: move.b 63(A6),162(A6)
  $03dfe0: move.b 62(A6),46(A6)
  $03dfe6: clr.b 99(A6)
  $03dfea: eori.b #$1,46(A6)
  $03dff0: clr.b 160(A6)
  $03dff4: clr.b 174(A6)
  $03dff8: rts
L3dffa:
  $03dffa: move.b 162(A6),D0
  $03dffe: add.w D0,D0
  $03e000: move.w 6(PC,D0.w) == $3e008+D0,D1
  $03e004: jmp 2(PC,D1.w) == $3e008+D1
  ; ---- gap 3e008..3e01a (18 bytes) ----
L3e01a:
  $03e01a: move.b 5(A6),D0
  $03e01e: move.w 6(PC,D0.w) == $3e026+D0,D1
  $03e022: jmp 2(PC,D1.w) == $3e026+D1
  ; ---- gap 3e026..3e02e (8 bytes) ----
L3e02e:
  $03e02e: addq.b #2,5(A6)
  $03e032: bra $3f34a
L3e036:
  $03e036: jsr $3b3c.w
  $03e03a: tst.b 41(A6)
  $03e03e: bne $3e044
  $03e040: addq.b #2,5(A6)
L3e044:
  $03e044: rts
L3e046:
  $03e046: tst.b 23(A6)
  $03e04a: beq $3e052
  $03e04c: subq.b #1,23(A6)
  $03e050: bne $3e056
L3e052:
  $03e052: addq.b #2,5(A6)
L3e056:
  $03e056: rts
L3e058:
  $03e058: move.b 5(A6),D0
  $03e05c: move.w 6(PC,D0.w) == $3e064+D0,D1
  $03e060: jmp 2(PC,D1.w) == $3e064+D1
  ; ---- gap 3e064..3e06c (8 bytes) ----
L3e06c:
  $03e06c: addq.b #2,5(A6)
  $03e070: bra $3f352
L3e074:
  $03e074: jsr $3b3c.w
  $03e078: moveq #0,D0
  $03e07a: move.b 40(A6),D0
  $03e07e: add.b D0,D0
  $03e080: move.w 26(PC,D0.w) == $3e09c+D0,D1
  $03e084: add.w D1,48(A6)
  $03e088: tst.b 41(A6)
  $03e08c: bpl $3e09a
  $03e08e: addq.b #2,4(A6)
  $03e092: clr.b 5(A6)
  $03e096: bra $3f2bc
L3e09a:
  $03e09a: rts
  ; ---- gap 3e09c..3e0ce (50 bytes) ----
L3e0ce:
  $03e0ce: move.b 5(A6),D0
  $03e0d2: move.w 6(PC,D0.w) == $3e0da+D0,D1
  $03e0d6: jmp 2(PC,D1.w) == $3e0da+D1
  ; ---- gap 3e0da..3e0e6 (12 bytes) ----
L3e0e6:
  $03e0e6: addq.b #2,5(A6)
  $03e0ea: bra $3f35a
L3e0ee:
  $03e0ee: tst.b 23(A6)
  $03e0f2: beq $3e0fa
  $03e0f4: subq.b #1,23(A6)
  $03e0f8: bne $3e128
L3e0fa:
  $03e0fa: addq.b #2,5(A6)
  $03e0fe: clr.b 30(A6)
  $03e102: move.w #$200,80(A6)
  $03e108: move.w #$380,84(A6)
  $03e10e: move.w #$48,86(A6)
  $03e114: tst.b 46(A6)
  $03e118: bne $3e11e
  $03e11a: neg.w 80(A6)
L3e11e:
  $03e11e: addi.w #$10,10(A6)
  $03e124: bra $3f35a
L3e128:
  $03e128: rts
L3e12a:
  $03e12a: jsr $3b3c.w
  $03e12e: tst.b 30(A6)
  $03e132: beq $3e13a
  $03e134: subq.b #1,30(A6)
  $03e138: bne $3e128
L3e13a:
  $03e13a: jsr $30d4.w
  $03e13e: bsr $40b5e
  $03e142: beq $3e15c
  $03e144: jsr $aaa.w
  $03e148: move.b #$5,30(A6)
  $03e14e: clr.w 80(A6)
  $03e152: tst.w 84(A6)
  $03e156: bmi $3e15c
  $03e158: clr.w 84(A6)
L3e15c:
  $03e15c: move.w 10(A6),D1
  $03e160: cmp.w 14(A6),D1
  $03e164: bhi $3e198
  $03e166: jsr $aaa.w
  $03e16a: addq.b #2,5(A6)
  $03e16e: move.l 14(A6),10(A6)
  $03e174: move.w #$280,80(A6)
  $03e17a: move.w #$280,84(A6)
  $03e180: move.w #$48,86(A6)
  $03e186: tst.b 46(A6)
  $03e18a: bne $3e190
  $03e18c: neg.w 80(A6)
L3e190:
  $03e190: jsr $44d0.w
  $03e194: bra $3f372
L3e198:
  $03e198: rts
L3e19a:
  $03e19a: jsr $30d4.w
  $03e19e: bsr $40b5e
  $03e1a2: beq $3e1a8
  $03e1a4: clr.w 80(A6)
L3e1a8:
  $03e1a8: move.w 10(A6),D0
  $03e1ac: cmp.w 14(A6),D0
  $03e1b0: bhi $3e1d6
  $03e1b2: addq.b #2,5(A6)
  $03e1b6: move.l 14(A6),10(A6)
  $03e1bc: move.w #$100,80(A6)
  $03e1c2: move.w #$14,82(A6)
  $03e1c8: tst.b 46(A6)
  $03e1cc: bne $3e1d6
  $03e1ce: neg.w 80(A6)
  $03e1d2: neg.w 82(A6)
L3e1d6:
  $03e1d6: jmp $3b3c.w
L3e1da:
  $03e1da: jsr $315c.w
  $03e1de: beq $3e1f0
  $03e1e0: bsr $40af4
  $03e1e4: move.l 10(A6),14(A6)
  $03e1ea: tst.b D6
  $03e1ec: bne $3e1f0
  $03e1ee: rts
L3e1f0:
  $03e1f0: addq.b #2,5(A6)
  $03e1f4: bra $3f314
L3e1f8:
  $03e1f8: tst.b 41(A6)
  $03e1fc: beq $3e20a
  $03e1fe: clr.b 99(A6)
  $03e202: clr.b 5(A6)
  $03e206: addq.b #2,4(A6)
L3e20a:
  $03e20a: jmp $3b3c.w
L3e20e:
  $03e20e: move.b 5(A6),D0
  $03e212: move.w 6(PC,D0.w) == $3e21a+D0,D1
  $03e216: jmp 2(PC,D1.w) == $3e21a+D1
  ; ---- gap 3e21a..3e222 (8 bytes) ----
L3e222:
  $03e222: tst.b 23(A6)
  $03e226: beq $3e22e
  $03e228: subq.b #1,23(A6)
  $03e22c: bne $3e25e
L3e22e:
  $03e22e: addq.b #2,5(A6)
  $03e232: clr.b 30(A6)
  $03e236: move.w #$280,80(A6)
  $03e23c: move.w #$380,84(A6)
  $03e242: move.w #$48,86(A6)
  $03e248: move.b 62(A6),46(A6)
  $03e24e: eori.b #$1,46(A6)
  $03e254: bne $3e25a
  $03e256: neg.w 80(A6)
L3e25a:
  $03e25a: jmp $44d0.w
L3e25e:
  $03e25e: rts
L3e260:
  $03e260: tst.b 30(A6)
  $03e264: beq $3e26e
  $03e266: subq.b #1,30(A6)
  $03e26a: bra $3e2d2
L3e26e:
  $03e26e: jsr $30d4.w
  $03e272: bsr $40b5e
  $03e276: beq $3e290
  $03e278: jsr $aaa.w
  $03e27c: clr.w 80(A6)
  $03e280: move.b #$4,30(A6)
  $03e286: tst.w 84(A6)
  $03e28a: bmi $3e290
  $03e28c: clr.w 84(A6)
L3e290:
  $03e290: move.w 10(A6),D0
  $03e294: cmp.w 14(A6),D0
  $03e298: bhi $3e2d2
  $03e29c: jsr $aaa.w
  $03e2a0: addq.b #2,5(A6)
  $03e2a4: move.l 14(A6),10(A6)
  $03e2aa: eori.b #$1,46(A6)
  $03e2b0: bsr $3f372
  $03e2b4: move.w #$100,80(A6)
  $03e2ba: move.w #$14,82(A6)
  $03e2c0: tst.b 46(A6)
  $03e2c4: beq $3e2ce
  $03e2c6: neg.w 80(A6)
  $03e2ca: neg.w 82(A6)
L3e2ce:
  $03e2ce: jsr $44d0.w
L3e2d2:
  $03e2d2: rts
L3e2d4:
  $03e2d4: jsr $3b3c.w
  $03e2d8: jsr $315c.w
  $03e2dc: beq $3e2ec
  $03e2de: bsr $40af4
  $03e2e2: move.l 10(A6),14(A6)
  $03e2e8: tst.b D6
  $03e2ea: beq $3e30e
L3e2ec:
  $03e2ec: tst.w 24(A6)
  $03e2f0: bpl $3e306
  $03e2f2: addq.b #2,2(A6)
  $03e2f6: move.b #$2,3(A6)
  $03e2fc: clr.b 4(A6)
  $03e300: clr.b 5(A6)
  $03e304: rts
L3e306:
  $03e306: addq.b #2,5(A6)
  $03e30a: bra $3f314
L3e30e:
  $03e30e: rts
L3e310:
  $03e310: jsr $3b3c.w
  $03e314: tst.b 41(A6)
  $03e318: beq $3e322
  $03e31a: addq.b #2,4(A6)
  $03e31e: clr.b 5(A6)
L3e322:
  $03e322: rts
L3e324:
  $03e324: move.b 5(A6),D0
  $03e328: move.w 6(PC,D0.w) == $3e330+D0,D1
  $03e32c: jmp 2(PC,D1.w) == $3e330+D1
  ; ---- gap 3e330..3e338 (8 bytes) ----
L3e338:
  $03e338: tst.b 23(A6)
  $03e33c: beq $3e344
  $03e33e: subq.b #1,23(A6)
  $03e342: bne $3e374
L3e344:
  $03e344: addq.b #2,5(A6)
  $03e348: clr.b 30(A6)
  $03e34c: move.w #$200,80(A6)
  $03e352: move.w #$300,84(A6)
  $03e358: move.w #$48,86(A6)
  $03e35e: move.b 62(A6),46(A6)
  $03e364: eori.b #$1,46(A6)
  $03e36a: beq $3e370
  $03e36c: neg.w 80(A6)
L3e370:
  $03e370: jmp $44d0.w
L3e374:
  $03e374: rts
L3e376:
  $03e376: tst.b 30(A6)
  $03e37a: beq $3e384
  $03e37c: subq.b #1,30(A6)
  $03e380: bra $3e3e8
L3e384:
  $03e384: jsr $30d4.w
  $03e388: bsr $40b5e
  $03e38c: beq $3e3aa
  $03e38e: jsr $aaa.w
  $03e392: clr.w 80(A6)
  $03e396: clr.w 82(A6)
  $03e39a: move.b #$4,30(A6)
  $03e3a0: tst.w 84(A6)
  $03e3a4: bmi $3e3aa
  $03e3a6: clr.w 84(A6)
L3e3aa:
  $03e3aa: move.w 10(A6),D0
  $03e3ae: cmp.w 14(A6),D0
  $03e3b2: bhi $3e3e8
  $03e3b6: jsr $aaa.w
  $03e3ba: move.l 14(A6),10(A6)
  $03e3c0: addq.b #2,5(A6)
  $03e3c4: eori.b #$1,46(A6)
  $03e3ca: bsr $3f372
  $03e3ce: move.w #$100,80(A6)
  $03e3d4: move.w #$14,82(A6)
  $03e3da: tst.b 46(A6)
  $03e3de: bne $3e3e8
  $03e3e0: neg.w 80(A6)
  $03e3e4: neg.w 82(A6)
L3e3e8:
  $03e3e8: rts
L3e3ea:
  $03e3ea: jsr $3b3c.w
  $03e3ee: jsr $315c.w
  $03e3f2: beq $3e402
  $03e3f4: bsr $40af4
  $03e3f8: move.l 10(A6),14(A6)
  $03e3fe: tst.b D6
  $03e400: beq $3e424
L3e402:
  $03e402: tst.w 24(A6)
  $03e406: bpl $3e41c
  $03e408: addq.b #2,2(A6)
  $03e40c: move.b #$2,3(A6)
  $03e412: clr.b 4(A6)
  $03e416: clr.b 5(A6)
  $03e41a: rts
L3e41c:
  $03e41c: addq.b #2,5(A6)
  $03e420: bra $3f314
L3e424:
  $03e424: rts
L3e426:
  $03e426: jsr $3b3c.w
  $03e42a: tst.b 41(A6)
  $03e42e: beq $3e438
  $03e430: addq.b #2,4(A6)
  $03e434: clr.b 5(A6)
L3e438:
  $03e438: rts
L3e43a:
  $03e43a: move.b 5(A6),D0
  $03e43e: move.w 6(PC,D0.w) == $3e446+D0,D1
  $03e442: jmp 2(PC,D1.w) == $3e446+D1
  ; ---- gap 3e446..3e452 (12 bytes) ----
L3e452:
  $03e452: addq.b #2,5(A6)
  $03e456: move.b #$1,99(A6)
  $03e45c: bra $3f35a
L3e460:
  $03e460: clr.b 5(A6)
  $03e464: addq.b #2,4(A6)
  $03e468: bra $3f2bc
L3e46c:
  $03e46c: tst.b 168(A6)
  $03e470: bne $3e4aa
  $03e472: bsr $4088c
  $03e476: tst.b 164(A6)
  $03e47a: beq $3e488
  $03e47c: move.b #$1,168(A6)
  $03e482: clr.b 164(A6)
  $03e486: bra $3e4aa
L3e488:
  $03e488: tst.b 149(A6)
  $03e48c: beq $3e498
  $03e48e: move.b #$2,3(A6)
  $03e494: bra $3df18
L3e498:
  $03e498: clr.b 4(A6)
  $03e49c: clr.b 5(A6)
  $03e4a0: move.b #$0,3(A6)
  $03e4a6: bra $3f2bc
L3e4aa:
  $03e4aa: move.b #$c,3(A6)
  $03e4b0: clr.b 4(A6)
  $03e4b4: clr.b 5(A6)
  $03e4b8: move.b #$1,168(A6)
  $03e4be: bra $3f2bc
L3e4c2:
  $03e4c2: move.b 4(A6),D0
  $03e4c6: move.w 6(PC,D0.w) == $3e4ce+D0,D1
  $03e4ca: jmp 2(PC,D1.w) == $3e4ce+D1
  ; ---- gap 3e4ce..3e4d2 (4 bytes) ----
L3e4d2:
  $03e4d2: tst.b 168(A6)
  $03e4d6: bne $3e4aa
  $03e4d8: bsr $4088c
  $03e4dc: tst.b 164(A6)
  $03e4e0: beq $3e4ee
  $03e4e2: move.b #$1,168(A6)
  $03e4e8: clr.b 164(A6)
  $03e4ec: bra $3e4aa
L3e4ee:
  $03e4ee: addq.b #2,4(A6)
  $03e4f2: jsr $3c26.w
  $03e4f6: andi.w #$1f,D0
  $03e4fa: move.b 6(PC,D0.w) == $3e502+D0,30(A6)
  $03e500: rts
  ; ---- gap 3e502..3e522 (32 bytes) ----
L3e522:
  $03e522: subq.b #1,30(A6)
  $03e526: bne $3e53e
  $03e528: tst.b 149(A6)
  $03e52c: beq $3e53a
  $03e530: move.b #$2,3(A6)
  $03e536: bra $3dfae
L3e53a:
  $03e53a: bra $3e498
L3e53e:
  $03e53e: move.b 167(A5),D0
  $03e542: andi.b #$7,D0
  $03e546: bne $3e54c
  $03e548: bra $40b92
L3e54c:
  $03e54c: rts
L3e54e:
  $03e54e: move.b 4(A6),D0
  $03e552: move.w 6(PC,D0.w) == $3e55a+D0,D1
  $03e556: jmp 2(PC,D1.w) == $3e55a+D1
  ; ---- gap 3e55a..3e562 (8 bytes) ----
L3e562:
  $03e562: addq.b #2,4(A6)
  $03e566: move.w #$0,84(A6)
  $03e56c: move.w #$0,80(A6)
  $03e572: move.w #$48,86(A6)
  $03e578: rts
L3e57a:
  $03e57a: jsr $30d4.w
  $03e57e: move.w 10(A6),D0
  $03e582: cmp.w 14(A6),D0
  $03e586: bhi $3e5b2
  $03e588: addq.b #2,4(A6)
  $03e58c: move.l 14(A6),10(A6)
  $03e592: tst.b 168(A6)
  $03e596: bne $3e4aa
  $03e59a: bsr $4088c
  $03e59e: tst.b 164(A6)
  $03e5a2: beq $3e5b2
  $03e5a4: move.b #$1,168(A6)
  $03e5aa: clr.b 164(A6)
  $03e5ae: bra $3e4aa
L3e5b2:
  $03e5b2: rts
L3e5b4:
  $03e5b4: addq.b #2,4(A6)
  $03e5b8: move.b #$39,30(A6)
  $03e5be: bra $3f30c
L3e5c2:
  $03e5c2: subq.b #1,30(A6)
  $03e5c6: bne $3e5de
  $03e5c8: tst.b 149(A6)
  $03e5cc: beq $3e5da
  $03e5d0: move.b #$2,3(A6)
  $03e5d6: bra $3dfae
L3e5da:
  $03e5da: bra $3e498
L3e5de:
  $03e5de: rts
L3e5e0:
  $03e5e0: move.b 4(A6),D0
  $03e5e4: move.w 6(PC,D0.w) == $3e5ec+D0,D1
  $03e5e8: jmp 2(PC,D1.w) == $3e5ec+D1
  ; ---- gap 3e5ec..3e5f6 (10 bytes) ----
L3e5f6:
  $03e5f6: addq.b #2,4(A6)
  $03e5fa: clr.b 30(A6)
  $03e5fe: clr.b 170(A6)
  $03e602: move.w #$400,80(A6)
  $03e608: move.w #$400,84(A6)
  $03e60e: move.w #$48,86(A6)
  $03e614: tst.b 46(A6)
  $03e618: beq $3e61e
  $03e61a: neg.w 80(A6)
L3e61e:
  $03e61e: bra $3f37a
L3e622:
  $03e622: tst.b 23(A6)
  $03e626: beq $3e62e
  $03e628: subq.b #1,23(A6)
  $03e62c: rts
L3e62e:
  $03e62e: tst.b 30(A6)
  $03e632: beq $3e63c
  $03e634: subq.b #1,30(A6)
  $03e638: bra $3e6b8
L3e63c:
  $03e63c: jsr $30d4.w
  $03e640: tst.w 80(A6)
  $03e644: beq $3e64a
  $03e646: jsr $6c96.w
L3e64a:
  $03e64a: bsr $40b5e
  $03e64e: beq $3e672
  $03e650: jsr $aaa.w
  $03e654: tst.b 170(A6)
  $03e658: bne $3e672
  $03e65a: bsr $3e6bc
  $03e65e: clr.w 80(A6)
  $03e662: move.b #$4,30(A6)
  $03e668: tst.w 84(A6)
  $03e66c: bmi $3e672
  $03e66e: clr.w 84(A6)
L3e672:
  $03e672: move.w 10(A6),D0
  $03e676: cmp.w 14(A6),D0
  $03e67a: bhi $3e6b8
  $03e67c: jsr $aaa.w
  $03e680: bsr $3f372
  $03e684: tst.b 170(A6)
  $03e688: bne $3e68e
  $03e68a: bsr $3e6bc
L3e68e:
  $03e68e: addq.b #2,4(A6)
  $03e692: move.l 14(A6),10(A6)
  $03e698: move.w #$100,80(A6)
  $03e69e: move.w #$400,84(A6)
  $03e6a4: move.w #$48,86(A6)
  $03e6aa: tst.b 46(A6)
  $03e6ae: beq $3e6b4
  $03e6b0: neg.w 80(A6)
L3e6b4:
  $03e6b4: jsr $44d0.w
L3e6b8:
  $03e6b8: jmp $3b3c.w
L3e6bc:
  $03e6bc: jsr $3f7a.w
  $03e6c0: move.b #$1,170(A6)
  $03e6c6: jsr $28b4.w
  $03e6ca: move.w 24(A6),26(A6)
  $03e6d0: bpl $3e6dc
  $03e6d2: move.b #$1,161(A6)
  $03e6d8: jmp $b8a.w
L3e6dc:
  $03e6dc: rts
L3e6de:
  $03e6de: jsr $30d4.w
  $03e6e2: bsr $40b5e
  $03e6e6: beq $3e6ec
  $03e6e8: clr.w 80(A6)
L3e6ec:
  $03e6ec: move.w 10(A6),D0
  $03e6f0: cmp.w 14(A6),D0
  $03e6f4: bhi $3e71a
  $03e6f6: move.l 14(A6),10(A6)
  $03e6fc: addq.b #2,4(A6)
  $03e700: move.w #$100,80(A6)
  $03e706: move.w #$10,82(A6)
  $03e70c: tst.b 46(A6)
  $03e710: beq $3e71a
  $03e712: neg.w 80(A6)
  $03e716: neg.w 82(A6)
L3e71a:
  $03e71a: jmp $3b3c.w
L3e71e:
  $03e71e: jsr $3b3c.w
  $03e722: jsr $315c.w
  $03e726: beq $3e736
  $03e728: bsr $40af4
  $03e72c: move.l 10(A6),14(A6)
  $03e732: tst.b D6
  $03e734: beq $3e75e
L3e736:
  $03e736: tst.b 161(A6)
  $03e73a: beq $3e752
  $03e73c: move.b #$4,2(A6)
  $03e742: move.b #$2,3(A6)
  $03e748: clr.b 4(A6)
  $03e74c: clr.b 5(A6)
  $03e750: rts
L3e752:
  $03e752: addq.b #2,4(A6)
  $03e756: bsr $40b92
  $03e75a: bra $3f314
L3e75e:
  $03e75e: rts
L3e760:
  $03e760: jsr $3b3c.w
  $03e764: tst.b 41(A6)
  $03e768: beq $3e79c
  $03e76a: tst.b 168(A6)
  $03e76e: bne $3e4aa
  $03e772: bsr $4088c
  $03e776: tst.b 164(A6)
  $03e77a: beq $3e78a
  $03e77c: move.b #$1,168(A6)
  $03e782: clr.b 164(A6)
  $03e786: bra $3e4aa
L3e78a:
  $03e78a: tst.b 149(A6)
  $03e78e: beq $3e498
  $03e792: move.b #$2,3(A6)
  $03e798: bra $3df18
L3e79c:
  $03e79c: rts
L3e79e:
  $03e79e: move.b 4(A6),D0
  $03e7a2: move.w 6(PC,D0.w) == $3e7aa+D0,D1
  $03e7a6: jmp 2(PC,D1.w) == $3e7aa+D1
  ; ---- gap 3e7aa..3e7b4 (10 bytes) ----
L3e7b4:
  $03e7b4: move.b 5(A6),D0
  $03e7b8: move.w 6(PC,D0.w) == $3e7c0+D0,D1
  $03e7bc: jmp 2(PC,D1.w) == $3e7c0+D1
  ; ---- gap 3e7c0..3e7c6 (6 bytes) ----
L3e7c6:
  $03e7c6: addq.b #2,5(A6)
  $03e7ca: bsr $40b92
  $03e7ce: move.b #$1,-27896(A5)
  $03e7d4: move.b #$1,174(A6)
  $03e7da: move.w #$c60,D0
  $03e7de: sub.w 6(A6),D0
  $03e7e2: asl.w #2,D0
  $03e7e4: move.w D0,80(A6)
  $03e7e8: move.w #$30,D0
  $03e7ec: sub.w 10(A6),D0
  $03e7f0: asl.w #2,D0
  $03e7f2: move.w D0,84(A6)
  $03e7f6: move.w #$400,86(A6)
  $03e7fc: bra $3f2dc
L3e800:
  $03e800: bsr $3e87c
  $03e804: moveq #0,D0
  $03e806: move.w 86(A6),D0
  $03e80a: lsl.l #8,D0
  $03e80c: add.l D0,10(A6)
  $03e810: subi.w #$20,86(A6)
  $03e816: bpl $3e820
  $03e818: clr.w 86(A6)
  $03e81c: addq.b #2,5(A6)
L3e820:
  $03e820: jmp $3b3c.w
L3e824:
  $03e824: bsr $3e87c
  $03e828: moveq #0,D0
  $03e82a: move.w 86(A6),D0
  $03e82e: lsl.l #8,D0
  $03e830: sub.l D0,10(A6)
  $03e834: addi.w #$20,86(A6)
  $03e83a: cmpi.w #$600,86(A6)
  $03e840: bls $3e848
  $03e842: move.w #$600,86(A6)
L3e848:
  $03e848: move.w 10(A6),D0
  $03e84c: cmpi.w #$30,D0
  $03e850: bhi $3e878
  $03e852: addq.b #2,4(A6)
  $03e856: clr.b 5(A6)
  $03e85a: clr.b -27896(A5)
  $03e85e: move.w #$28,14(A6)
  $03e864: move.w #$30,10(A6)
  $03e86a: move.b #$1e,30(A6)
  $03e870: bsr $3f2fc
  $03e874: bra $40b92
L3e878:
  $03e878: jmp $3b3c.w
L3e87c:
  $03e87c: moveq #0,D0
  $03e87e: move.w 80(A6),D0
  $03e882: swap D0
  $03e884: asr.l #8,D0
  $03e886: add.l D0,6(A6)
  $03e88a: moveq #0,D0
  $03e88c: move.w 84(A6),D0
  $03e890: swap D0
  $03e892: asr.l #8,D0
  $03e894: add.l D0,10(A6)
  $03e898: add.l D0,14(A6)
  $03e89c: rts
L3e89e:
  $03e89e: subq.b #1,30(A6)
  $03e8a2: bne $3e8ac
  $03e8a4: addq.b #2,4(A6)
  $03e8a8: bra $3f304
L3e8ac:
  $03e8ac: rts
L3e8ae:
  $03e8ae: jsr $3b3c.w
  $03e8b2: cmpi.b #$2,41(A6)
  $03e8b8: bne $3e8c2
  $03e8ba: move.w #$27,D0
  $03e8be: jsr $9e4.w
L3e8c2:
  $03e8c2: cmpi.b #$1,41(A6)
  $03e8c8: bne $3e8e0
  $03e8ca: addq.b #2,4(A6)
  $03e8ce: bsr $3f2fc
  $03e8d2: jsr $5f9e.w
  $03e8d6: move.w #$12c,166(A6)
  $03e8dc: clr.b 175(A6)
L3e8e0:
  $03e8e0: rts
L3e8e2:
  $03e8e2: move.b 5(A6),D0
  $03e8e6: move.w 22(PC,D0.w) == $3e8fe+D0,D1
  $03e8ea: jsr 18(PC,D1.w) == $3e8fe+D1
  $03e8ee: subq.w #1,166(A6)
  $03e8f2: bne $3e8fc
  $03e8f4: addq.b #2,4(A6)
  $03e8f8: clr.b 5(A6)
L3e8fc:
  $03e8fc: rts
  ; ---- gap 3e8fe..3e902 (4 bytes) ----
L3e902:
  $03e902: tst.b 175(A6)
  $03e906: bne $3e92e
  $03e908: lea 1384(A5),A0
  $03e90c: tst.b 137(A0)
  $03e910: bne $3e91c
  $03e912: lea 1576(A5),A0
  $03e916: tst.b 137(A0)
  $03e91a: beq $3e92e
L3e91c:
  $03e91c: addq.b #2,5(A6)
  $03e920: move.b #$78,30(A6)
  $03e926: move.w #$28,D0
  $03e92a: jmp $9e4.w
L3e92e:
  $03e92e: rts
L3e930:
  $03e930: subq.b #1,30(A6)
  $03e934: bne $3e93e
  $03e936: clr.b 5(A6)
  $03e93a: bra $3f2fc
L3e93e:
  $03e93e: jmp $3b3c.w
L3e942:
  $03e942: move.b 5(A6),D0
  $03e946: move.w 6(PC,D0.w) == $3e94e+D0,D1
  $03e94a: jmp 2(PC,D1.w) == $3e94e+D1
  ; ---- gap 3e94e..3e954 (6 bytes) ----
L3e954:
  $03e954: addq.b #2,5(A6)
  $03e958: bsr $40b92
  $03e95c: move.b #$1,-27896(A5)
  $03e962: move.b #$1,174(A6)
  $03e968: movea.l 128(A6),A0
  $03e96c: move.w 6(A0),D0
  $03e970: sub.w 6(A6),D0
  $03e974: asl.w #2,D0
  $03e976: move.w D0,80(A6)
  $03e97a: move.w 14(A0),D0
  $03e97e: move.w D0,172(A6)
  $03e982: sub.w 10(A6),D0
  $03e986: asl.w #2,D0
  $03e988: move.w D0,84(A6)
  $03e98c: move.w #$400,86(A6)
  $03e992: bra $3f2e4
L3e996:
  $03e996: bsr $3e87c
  $03e99a: moveq #0,D0
  $03e99c: move.w 86(A6),D0
  $03e9a0: lsl.l #8,D0
  $03e9a2: add.l D0,10(A6)
  $03e9a6: subi.w #$20,86(A6)
  $03e9ac: bpl $3e9b6
  $03e9ae: clr.w 86(A6)
  $03e9b2: addq.b #2,5(A6)
L3e9b6:
  $03e9b6: jmp $3b3c.w
L3e9ba:
  $03e9ba: tst.b 23(A6)
  $03e9be: beq $3e9ca
  $03e9c0: subi.b #$1,23(A6)
  $03e9c6: beq $3e9ca
  $03e9c8: rts
L3e9ca:
  $03e9ca: bsr $3e87c
  $03e9ce: moveq #0,D0
  $03e9d0: move.w 86(A6),D0
  $03e9d4: lsl.l #8,D0
  $03e9d6: sub.l D0,10(A6)
  $03e9da: addi.w #$20,86(A6)
  $03e9e0: cmpi.w #$600,86(A6)
  $03e9e6: bls $3e9ee
  $03e9e8: move.w #$600,86(A6)
L3e9ee:
  $03e9ee: move.w 10(A6),D0
  $03e9f2: cmp.w 172(A6),D0
  $03e9f6: bhi $3ea32
  $03e9f8: clr.b 3(A6)
  $03e9fc: clr.b 4(A6)
  $03ea00: clr.b 5(A6)
  $03ea04: move.l 14(A6),10(A6)
  $03ea0a: clr.b -27896(A5)
  $03ea0e: clr.b 168(A6)
  $03ea12: clr.b 174(A6)
  $03ea16: move.b #$28,97(A6)
  $03ea1c: bsr $3f2bc
  $03ea20: bsr $40af4
  $03ea24: move.l 10(A6),14(A6)
  $03ea2a: beq $3ea36
  $03ea2c: move.l 14(A6),10(A6)
L3ea32:
  $03ea32: jmp $3b3c.w
L3ea36:
  $03ea36: rts
L3ea38:
  $03ea38: move.b 3(A6),D0
  $03ea3c: move.w 24(PC,D0.w) == $3ea56+D0,D1
  $03ea40: jsr 20(PC,D1.w) == $3ea56+D1
  $03ea44: bsr $3ea94
  $03ea48: tst.b 64(A6)
  $03ea4c: bpl $3ea52
  $03ea4e: jmp $32be.w
L3ea52:
  $03ea52: jmp $32aa.w
  ; ---- gap 3ea56..3ea5a (4 bytes) ----
L3ea5a:
  $03ea5a: addq.b #2,3(A6)
  $03ea5e: jsr $4234.w
  $03ea62: bne $3eb4c
L3ea66:
  $03ea66: jsr $41ba.w
  $03ea6a: beq $3ea8c
  $03ea6c: bpl $3eb4c
  $03ea70: clr.b 64(A6)
  $03ea74: clr.b 66(A6)
  $03ea78: clr.b 160(A6)
  $03ea7c: move.b #$a,3(A6)
  $03ea82: clr.b 4(A6)
  $03ea86: clr.b 5(A6)
  $03ea8a: rts
L3ea8c:
  $03ea8c: bsr $3f39a
  $03ea90: bra $3eb46
L3ea94:
  $03ea94: move.w 24(A6),D0
  $03ea98: cmp.w 26(A6),D0
  $03ea9c: bne $3eaa0
  $03ea9e: rts
L3eaa0:
  $03eaa0: move.w D0,26(A6)
  $03eaa4: moveq #0,D0
  $03eaa6: move.b 63(A6),D0
  $03eaaa: add.w D0,D0
  $03eaac: move.w 6(PC,D0.w) == $3eab4+D0,D1
  $03eab0: jmp 2(PC,D1.w) == $3eab4+D1
  ; ---- gap 3eab4..3eac6 (18 bytes) ----
L3eac6:
  $03eac6: tst.w 24(A6)
  $03eaca: bmi $3eb18
  $03eacc: rts
L3eace:
  $03eace: tst.w 24(A6)
  $03ead2: bmi $3eb18
  $03ead4: clr.b 64(A6)
  $03ead8: clr.b 66(A6)
  $03eadc: move.b #$4,3(A6)
  $03eae2: clr.b 4(A6)
  $03eae6: clr.b 5(A6)
  $03eaea: rts
L3eaec:
  $03eaec: rts
L3eaee:
  $03eaee: tst.w 24(A6)
  $03eaf2: bpl $3eafe
  $03eaf4: move.b #$1,161(A6)
  $03eafa: jsr $b8a.w
L3eafe:
  $03eafe: clr.b 64(A6)
  $03eb02: clr.b 66(A6)
  $03eb06: move.b #$4,3(A6)
  $03eb0c: clr.b 4(A6)
  $03eb10: clr.b 5(A6)
  $03eb14: rts
L3eb16:
  $03eb16: bra $3eace
L3eb18:
  $03eb18: clr.b 99(A6)
  $03eb1c: cmpi.b #$8,63(A6)
  $03eb22: bne $3eb2a
  $03eb24: move.b #$1,99(A6)
L3eb2a:
  $03eb2a: clr.b 64(A6)
  $03eb2e: clr.b 66(A6)
  $03eb32: addq.b #2,2(A6)
  $03eb36: clr.b 3(A6)
  $03eb3a: clr.b 4(A6)
  $03eb3e: clr.b 5(A6)
  $03eb42: jmp $b8a.w
L3eb46:
  $03eb46: jsr $4166.w
  $03eb4a: bne $3eb80
L3eb4c:
  $03eb4c: clr.b 64(A6)
  $03eb50: clr.b 66(A6)
  $03eb54: bsr $3f2bc
  $03eb58: move.b #$32,97(A6)
  $03eb5e: clr.b 160(A6)
  $03eb62: move.b #$6,D2
  $03eb66: move.w 10(A6),D1
  $03eb6a: cmp.w 14(A6),D1
  $03eb6e: bls $3eb78
  $03eb70: move.b #$8,D2
  $03eb74: bsr $3f382
L3eb78:
  $03eb78: move.b D2,3(A6)
  $03eb7c: clr.w 4(A6)
L3eb80:
  $03eb80: rts
L3eb82:
  $03eb82: move.b 3(A6),D0
  $03eb86: move.w 10(PC,D0.w) == $3eb92+D0,D1
  $03eb8a: jsr 6(PC,D1.w) == $3eb92+D1
  $03eb8e: jmp $32a2.w
  ; ---- gap 3eb92..3eb98 (6 bytes) ----
L3eb98:
  $03eb98: move.b 4(A6),D0
  $03eb9c: move.w 6(PC,D0.w) == $3eba4+D0,D1
  $03eba0: jmp 2(PC,D1.w) == $3eba4+D1
  ; ---- gap 3eba4..3ebac (8 bytes) ----
L3ebac:
  $03ebac: subq.b #1,23(A6)
  $03ebb0: bne $3ebe0
  $03ebb2: addq.b #2,4(A6)
  $03ebb6: clr.b 30(A6)
  $03ebba: move.w #$400,80(A6)
  $03ebc0: move.w #$300,84(A6)
  $03ebc6: move.w #$48,86(A6)
  $03ebcc: tst.b 46(A6)
  $03ebd0: bne $3ebd6
  $03ebd2: neg.w 80(A6)
L3ebd6:
  $03ebd6: addi.w #$10,10(A6)
  $03ebdc: bra $3f35a
L3ebe0:
  $03ebe0: rts
L3ebe2:
  $03ebe2: jsr $3b3c.w
  $03ebe6: tst.b 30(A6)
  $03ebea: beq $3ebf2
  $03ebec: subq.b #1,30(A6)
  $03ebf0: bne $3ec50
L3ebf2:
  $03ebf2: jsr $30d4.w
  $03ebf6: bsr $40b5e
  $03ebfa: beq $3ec14
  $03ebfc: jsr $aaa.w
  $03ec00: move.b #$5,30(A6)
  $03ec06: clr.w 80(A6)
  $03ec0a: tst.w 84(A6)
  $03ec0e: bmi $3ec14
  $03ec10: clr.w 84(A6)
L3ec14:
  $03ec14: move.w 10(A6),D1
  $03ec18: cmp.w 14(A6),D1
  $03ec1c: bhi $3ec50
  $03ec1e: jsr $aaa.w
  $03ec22: addq.b #2,4(A6)
  $03ec26: move.l 14(A6),10(A6)
  $03ec2c: move.w #$100,80(A6)
  $03ec32: move.w #$400,84(A6)
  $03ec38: move.w #$48,86(A6)
  $03ec3e: tst.b 46(A6)
  $03ec42: bne $3ec48
  $03ec44: neg.w 80(A6)
L3ec48:
  $03ec48: jsr $44d0.w
  $03ec4c: bra $3f372
L3ec50:
  $03ec50: rts
L3ec52:
  $03ec52: jsr $30d4.w
  $03ec56: bsr $40b5e
  $03ec5a: beq $3ec60
  $03ec5c: clr.w 80(A6)
L3ec60:
  $03ec60: move.w 10(A6),D0
  $03ec64: cmp.w 14(A6),D0
  $03ec68: bhi $3ec8e
  $03ec6a: addq.b #2,4(A6)
  $03ec6e: move.l 14(A6),10(A6)
  $03ec74: move.w #$100,80(A6)
  $03ec7a: move.w #$10,82(A6)
  $03ec80: tst.b 46(A6)
  $03ec84: bne $3ec8e
  $03ec86: neg.w 80(A6)
  $03ec8a: neg.w 82(A6)
L3ec8e:
  $03ec8e: jmp $3b3c.w
L3ec92:
  $03ec92: jsr $315c.w
  $03ec96: beq $3eca8
  $03ec98: bsr $40af4
  $03ec9c: move.l 10(A6),14(A6)
  $03eca2: tst.b D6
  $03eca4: bne $3eca8
  $03eca6: rts
L3eca8:
  $03eca8: addq.b #2,3(A6)
  $03ecac: clr.b 4(A6)
  $03ecb0: rts
L3ecb2:
  $03ecb2: move.b 4(A6),D0
  $03ecb6: move.w 6(PC,D0.w) == $3ecbe+D0,D1
  $03ecba: jmp 2(PC,D1.w) == $3ecbe+D1
  ; ---- gap 3ecbe..3ecc2 (4 bytes) ----
L3ecc2:
  $03ecc2: addq.b #2,4(A6)
  $03ecc6: move.b #$1,299(A5)
  $03eccc: move.b #$28,30(A6)
  $03ecd2: bra $3f372
L3ecd6:
  $03ecd6: subq.b #1,30(A6)
  $03ecda: bne $3ece8
  $03ecdc: addq.b #2,3(A6)
  $03ece0: clr.b 4(A6)
  $03ece4: bra $3f38a
L3ece8:
  $03ece8: rts
L3ecea:
  $03ecea: move.b 4(A6),D0
  $03ecee: move.w 6(PC,D0.w) == $3ecf6+D0,D1
  $03ecf2: jmp 2(PC,D1.w) == $3ecf6+D1
  ; ---- gap 3ecf6..3ecfa (4 bytes) ----
L3ecfa:
  $03ecfa: jsr $3b3c.w
  $03ecfe: tst.b 41(A6)
  $03ed02: beq $3ed2a
  $03ed04: addq.b #2,4(A6)
  $03ed08: move.b #$1,297(A5)
  $03ed0e: jsr $1b428.l
  $03ed14: jsr $b8a.w
  $03ed18: move.b #$4,D0
  $03ed1c: tst.b 105(A6)
  $03ed20: beq $3ed26
  $03ed22: ori.b #$80,D0
L3ed26:
  $03ed26: jmp $288c.w
L3ed2a:
  $03ed2a: rts
L3ed2c:
  $03ed2c: jmp $3b3c.w
L3ed30:
  $03ed30: move.w #$b30,1078(A5)
  $03ed36: jsr $3946.w
  $03ed3a: beq $3ed4e
  $03ed3c: move.b #$1,0(A4)
  $03ed42: move.b #$1,20(A4)
  $03ed48: move.b #$4,19(A4)
L3ed4e:
  $03ed4e: move.b #$1,297(A5)
  $03ed54: jmp $38f0.w
L3ed58:
  $03ed58: move.w 24(A6),D0
  $03ed5c: bmi $3ed90
  $03ed5e: cmp.w 26(A6),D0
  $03ed62: beq $3edbc
  $03ed64: move.w D0,26(A6)
  $03ed68: move.w 10(A6),D0
  $03ed6c: cmp.w 14(A6),D0
  $03ed70: beq $3ed80
  $03ed72: cmpi.b #$8,63(A6)
  $03ed78: beq $3ed80
  $03ed7a: move.b #$3,63(A6)
L3ed80:
  $03ed80: move.b #$4,3(A6)
  $03ed86: clr.b 4(A6)
  $03ed8a: clr.b 5(A6)
  $03ed8e: rts
L3ed90:
  $03ed90: tst.b 161(A6)
  $03ed94: bne $3edbc
  $03ed96: clr.b 99(A6)
  $03ed9a: cmpi.b #$8,63(A6)
  $03eda0: bne $3eda8
  $03eda2: move.b #$1,99(A6)
L3eda8:
  $03eda8: addq.b #2,2(A6)
  $03edac: clr.b 3(A6)
  $03edb0: clr.b 4(A6)
  $03edb4: clr.b 5(A6)
  $03edb8: jmp $b8a.w
L3edbc:
  $03edbc: rts
L3edbe:
  $03edbe: bsr $40728
  $03edc2: bne $3edcc
  $03edc4: move.b #$1,160(A6)
  $03edca: bra $3edd2
L3edcc:
  $03edcc: bsr $407a2
  $03edd0: bne $3ede8
L3edd2:
  $03edd2: move.l A0,128(A6)
  $03edd6: move.b D3,138(A6)
  $03edda: clr.b 5(A6)
  $03edde: clr.b 4(A6)
  $03ede2: move.b #$2,3(A6)
L3ede8:
  $03ede8: rts
  ; ---- gap 3edea..3f2aa (1216 bytes) ----
L3f2aa:
  $03f2aa: move.l #$404ca,56(A6)
  $03f2b2: rts
  ; ---- gap 3f2b4..3f2bc (8 bytes) ----
L3f2bc:
  $03f2bc: lea 352(PC) == $3f41e,A1
  $03f2c0: jmp $3b1c.w
L3f2c4:
  $03f2c4: lea 3116(PC) == $3fef2,A1
  $03f2c8: jmp $3b1c.w
L3f2cc:
  $03f2cc: lea 3120(PC) == $3fefe,A1
  $03f2d0: jmp $3b1c.w
L3f2d4:
  $03f2d4: lea 3216(PC) == $3ff66,A1
  $03f2d8: jmp $3b1c.w
L3f2dc:
  $03f2dc: lea 3136(PC) == $3ff1e,A1
  $03f2e0: jmp $3b1c.w
L3f2e4:
  $03f2e4: lea 3160(PC) == $3ff3e,A1
  $03f2e8: jmp $3b1c.w
L3f2ec:
  $03f2ec: move.w #$28,D0
  $03f2f0: jsr $9e4.w
  $03f2f4: lea 744(PC) == $3f5de,A1
  $03f2f8: jmp $3b1c.w
L3f2fc:
  $03f2fc: lea 940(PC) == $3f6aa,A1
  $03f300: jmp $3b1c.w
L3f304:
  $03f304: lea 1256(PC) == $3f7ee,A1
  $03f308: jmp $3b1c.w
L3f30c:
  $03f30c: lea 1436(PC) == $3f8aa,A1
  $03f310: jmp $3b1c.w
L3f314:
  $03f314: move.b #$3e,97(A6)
  $03f31a: lea 1566(PC) == $3f93a,A1
  $03f31e: jmp $3b1c.w
L3f322:
  $03f322: lea 2258(PC) == $3fbf6,A1
  $03f326: jmp $3b1c.w
L3f32a:
  $03f32a: lea 2286(PC) == $3fc1a,A1
  $03f32e: jmp $3b1c.w
L3f332:
  $03f332: lea 2314(PC) == $3fc3e,A1
  $03f336: jmp $3b1c.w
L3f33a:
  $03f33a: lea 2334(PC) == $3fc5a,A1
  $03f33e: jmp $3b1c.w
L3f342:
  $03f342: lea 3118(PC) == $3ff72,A1
  $03f346: jmp $3b1c.w
L3f34a:
  $03f34a: lea 3606(PC) == $40162,A1
  $03f34e: jmp $3b1c.w
L3f352:
  $03f352: lea 3614(PC) == $40172,A1
  $03f356: jmp $3b1c.w
L3f35a:
  $03f35a: tst.b 99(A6)
  $03f35e: bne $3f368
  $03f360: lea 3784(PC) == $4022a,A1
  $03f364: jmp $3b1c.w
L3f368:
  $03f368: movea.l #$4018,A1
  $03f36e: jmp $3b1c.w
L3f372:
  $03f372: lea 3774(PC) == $40232,A1
  $03f376: jmp $3b1c.w
L3f37a:
  $03f37a: lea 3930(PC) == $402d6,A1
  $03f37e: jmp $3b1c.w
L3f382:
  $03f382: lea 3914(PC) == $402ce,A1
  $03f386: jmp $3b1c.w
L3f38a:
  $03f38a: lea 1402(PC) == $3f906,A1
  $03f38e: jmp $3b1c.w
  ; ---- gap 3f392..3f39a (8 bytes) ----
L3f39a:
  $03f39a: move.b 67(A6),D0
  $03f39e: lea 6(PC) == $3f3a6,A1
  $03f3a2: jmp $3b10.w
  ; ---- gap 3f3a6..406f2 (4940 bytes) ----
L406f2:
  $0406f2: lea $3edea.l,A0
  $0406f8: cmpi.b #$3,21610(A5)
  $0406fe: bne $40706
  $040700: lea $3eeea.l,A0
L40706:
  $040706: tst.b 148(A6)
  $04070a: beq $40710
  $04070c: lea 128(A0),A0
L40710:
  $040710: moveq #0,D0
  $040712: move.b 96(A6),D0
  $040716: lsl.w #2,D0
  $040718: move.l 0(A0,D0.w),D2
  $04071c: jsr $3c26.w
  $040720: andi.w #$1f,D0
  $040724: btst D0,D2
  $040726: rts
L40728:
  $040728: bsr $4075a
  $04072c: bne $4074e
  $04072e: move.w D1,D2
  $040730: bsr $40760
  $040734: bne $4073a
  $040736: cmp.w D1,D2
  $040738: bcs $40744
L4073a:
  $04073a: lea 1384(A5),A0
  $04073e: moveq #0,D3
  $040740: moveq #0,D0
  $040742: rts
L40744:
  $040744: lea 1576(A5),A0
  $040748: moveq #1,D3
  $04074a: moveq #0,D0
  $04074c: rts
L4074e:
  $04074e: bsr $40760
  $040752: beq $40744
  $040754: move.b #$1,D0
  $040758: rts
L4075a:
  $04075a: lea 1384(A5),A0
  $04075e: bra $40764
L40760:
  $040760: lea 1576(A5),A0
L40764:
  $040764: tst.b 0(A0)
  $040768: beq $4079e
  $04076a: tst.b 137(A0)
  $04076e: bne $4079e
  $040770: move.w 6(A0),D0
  $040774: sub.w 6(A6),D0
  $040778: move.w D0,D1
  $04077a: bpl $4077e
  $04077c: neg.w D1
L4077e:
  $04077e: addi.w #$48,D0
  $040782: cmpi.w #$90,D0
  $040786: bhi $4079e
  $040788: move.w 10(A0),D0
  $04078c: sub.w 10(A6),D0
  $040790: addi.w #$9,D0
  $040794: cmpi.w #$12,D0
  $040798: bhi $4079e
  $04079a: moveq #0,D0
  $04079c: rts
L4079e:
  $04079e: moveq #1,D0
  $0407a0: rts
L407a2:
  $0407a2: bsr $407d0
  $0407a6: bne $407c4
  $0407a8: move.w D1,D2
  $0407aa: bsr $407d8
  $0407ae: bne $407b4
  $0407b0: cmp.w D1,D2
  $0407b2: bcs $407bc
L407b4:
  $0407b4: lea 1384(A5),A0
  $0407b8: moveq #0,D0
  $0407ba: rts
L407bc:
  $0407bc: lea 1576(A5),A0
  $0407c0: moveq #0,D0
  $0407c2: rts
L407c4:
  $0407c4: bsr $407d8
  $0407c8: beq $407bc
  $0407ca: move.b #$1,D0
  $0407ce: rts
L407d0:
  $0407d0: lea 1384(A5),A0
  $0407d4: moveq #0,D3
  $0407d6: bra $407de
L407d8:
  $0407d8: lea 1576(A5),A0
  $0407dc: moveq #1,D3
L407de:
  $0407de: tst.b 0(A0)
  $0407e2: beq $40818
  $0407e4: tst.b 137(A0)
  $0407e8: bne $40818
  $0407ea: move.w 6(A0),D0
  $0407ee: sub.w 6(A6),D0
  $0407f2: move.w D0,D1
  $0407f4: bpl $407f8
  $0407f6: neg.w D1
L407f8:
  $0407f8: addi.w #$58,D0
  $0407fc: cmpi.w #$b0,D0
  $040800: bhi $40818
  $040802: move.w 10(A0),D0
  $040806: sub.w 10(A6),D0
  $04080a: addi.w #$18,D0
  $04080e: cmpi.w #$30,D0
  $040812: bhi $40818
  $040814: moveq #0,D0
  $040816: rts
L40818:
  $040818: moveq #1,D0
  $04081a: rts
L4081c:
  $04081c: move.b 54(A6),D0
  $040820: lsr.b #3,D0
  $040822: bra $4082a
L40824:
  $040824: move.b 54(A6),D0
  $040828: lsr.b #4,D0
L4082a:
  $04082a: move.b 46(A6),D1
  $04082e: eor.b D1,D0
  $040830: bne $40836
  $040832: jmp $3b3c.w
L40836:
  $040836: jmp $3b76.w
L4083a:
  $04083a: bsr $4081c
  $04083c: lea 54(PC) == $40874,A1
  $040840: bra $40848
L40842:
  $040842: bsr $40824
  $040844: lea 58(PC) == $40880,A1
L40848:
  $040848: moveq #0,D2
  $04084a: move.b 41(A6),D2
  $04084e: bmi $4086c
  $040850: movea.l 0(A1,D2.w),A1
  $040854: jsr $3184.w
  $040858: move.l 10(A6),14(A6)
  $04085e: bsr $40af4
  $040862: move.l 10(A6),14(A6)
  $040868: tst.b D6
  $04086a: bne $40870
L4086c:
  $04086c: moveq #0,D0
  $04086e: rts
L40870:
  $040870: moveq #1,D0
  $040872: rts
  ; ---- gap 40874..4088c (24 bytes) ----
L4088c:
  $04088c: moveq #0,D0
  $04088e: move.b 165(A6),D0
  $040892: move.w 6(PC,D0.w) == $4089a+D0,D1
  $040896: jmp 2(PC,D1.w) == $4089a+D1
  ; ---- gap 4089a..408a0 (6 bytes) ----
L408a0:
  $0408a0: move.w #$12c,D1
  $0408a4: cmpi.b #$3,163(A6)
  $0408aa: beq $408b0
  $0408ac: move.w #$c8,D1
L408b0:
  $0408b0: cmp.w 24(A6),D1
  $0408b4: bcs $408c0
  $0408b6: addq.b #2,165(A6)
  $0408ba: move.b #$1,164(A6)
L408c0:
  $0408c0: rts
L408c2:
  $0408c2: move.w #$64,D1
  $0408c6: cmpi.b #$3,163(A6)
  $0408cc: bne $408d2
  $0408ce: move.w #$64,D1
L408d2:
  $0408d2: cmp.w 24(A6),D1
  $0408d6: bcs $408e8
  $0408d8: addq.b #2,165(A6)
  $0408dc: move.b #$1,164(A6)
  $0408e2: move.b #$1,148(A6)
L408e8:
  $0408e8: rts
L408ea:
  $0408ea: rts
L408ec:
  $0408ec: moveq #0,D0
  $0408ee: move.b 169(A6),D0
  $0408f2: move.w 6(PC,D0.w) == $408fa+D0,D1
  $0408f6: jmp 2(PC,D1.w) == $408fa+D1
  ; ---- gap 408fa..408fe (4 bytes) ----
L408fe:
  $0408fe: move.w #$4b,D1
  $040902: cmpi.b #$3,163(A6)
  $040908: beq $4090e
  $04090a: move.w #$70,D1
L4090e:
  $04090e: cmp.w 24(A6),D1
  $040912: bcs $4091e
  $040914: addq.b #2,169(A6)
  $040918: move.b #$1,148(A6)
L4091e:
  $04091e: rts
L40920:
  $040920: rts
L40922:
  $040922: moveq #0,D3
  $040924: lea 1384(A5),A0
  $040928: jsr $3c26.w
  $04092c: andi.w #$f,D0
  $040930: move.w #$aaaa,D1
  $040934: btst D0,D1
  $040936: beq $4093e
  $040938: moveq #1,D3
  $04093a: lea 1576(A5),A0
L4093e:
  $04093e: rts
L40940:
  $040940: bsr $409ac
  $040944: jsr $3c26.w
  $040948: andi.w #$f,D0
  $04094c: move.b 0(A0,D0.w),54(A6)
  $040952: rts
L40954:
  $040954: bsr $409ac
  $040958: moveq #0,D6
L4095a:
  $04095a: jsr $3c26.w
  $04095e: andi.w #$1f,D0
  $040962: move.b 40(PC,D0.w) == $4098c+D0,D0
  $040966: move.b 54(A6),D2
  $04096a: add.b D2,D0
  $04096c: movea.l A0,A1
  $04096e: move.w #$f,D1
L40972:
  $040972: move.b (A1)+,D2
  $040974: cmp.b D2,D0
  $040976: beq $40986
  $040978: dbf D1,#-8 == $40972
  $04097c: addq.b #1,D6
  $04097e: cmpi.b #$5,D6
  $040982: beq $40940
  $040984: bra $4095a
L40986:
  $040986: move.b D2,54(A6)
  $04098a: rts
  ; ---- gap 4098c..409ac (32 bytes) ----
L409ac:
  $0409ac: bsr $40af4
  $0409b0: move.l 10(A6),14(A6)
  $0409b6: move.w 6(A6),D2
  $0409ba: subi.w #$ab4,D2
  $0409be: andi.w #$1c0,D2
  $0409c2: lsr.w #6,D2
  $0409c4: move.w 14(A6),D0
  $0409c8: subi.w #$10,D0
  $0409cc: andi.w #$f0,D0
  $0409d0: move.w D0,D1
  $0409d2: lsr.w #2,D0
  $0409d4: lsr.w #4,D1
  $0409d6: add.w D1,D0
  $0409d8: add.w D0,D2
  $0409da: moveq #0,D0
  $0409dc: move.b 14(PC,D2.w) == $409ec+D2,D0
  $0409e0: lea 26(PC) == $409fc,A0
  $0409e4: lsl.w #4,D0
  $0409e6: lea 0(A0,D0.w),A0
  $0409ea: rts
  ; ---- gap 409ec..40a8c (160 bytes) ----
L40a8c:
  $040a8c: move.l #$40572,92(A6)
  $040a94: cmpi.b #$3,21610(A5)
  $040a9a: bne $40aa4
  $040a9c: move.l #$40632,92(A6)
L40aa4:
  $040aa4: rts
L40aa6:
  $040aa6: moveq #0,D3
  $040aa8: lea 1384(A5),A0
  $040aac: tst.b 0(A0)
  $040ab0: beq $40ab6
  $040ab2: bsr $40ac8
  $040ab4: bne $40ac6
L40ab6:
  $040ab6: moveq #1,D3
  $040ab8: lea 1576(A5),A0
  $040abc: tst.b 0(A0)
  $040ac0: beq $40ac4
  $040ac2: bra $40ac8
L40ac4:
  $040ac4: moveq #0,D0
L40ac6:
  $040ac6: rts
L40ac8:
  $040ac8: move.w 6(A0),D0
  $040acc: sub.w 6(A6),D0
  $040ad0: addi.w #$50,D0
  $040ad4: cmpi.w #$a0,D0
  $040ad8: bhi $40af0
  $040ada: move.w 10(A0),D0
  $040ade: sub.w 10(A6),D0
  $040ae2: addi.w #$20,D0
  $040ae6: cmpi.w #$40,D0
  $040aea: bhi $40af0
  $040aec: moveq #1,D0
  $040aee: rts
L40af0:
  $040af0: moveq #0,D0
  $040af2: rts
L40af4:
  $040af4: moveq #0,D6
  $040af6: bsr $40b02
  $040afa: bsr $40b3a
  $040afe: tst.b D6
  $040b00: rts
L40b02:
  $040b02: move.w 14(A6),D0
  $040b06: cmpi.w #$10,D0
  $040b0a: bcc $40b20
  $040b0c: addq.b #1,D6
  $040b0e: move.l #$100000,14(A6)
  $040b16: move.l #$100000,10(A6)
  $040b1e: rts
L40b20:
  $040b20: cmpi.w #$40,D0
  $040b24: blt $40b38
  $040b26: addq.b #1,D6
  $040b28: move.l #$3f0000,14(A6)
  $040b30: move.l #$3f0000,10(A6)
L40b38:
  $040b38: rts
L40b3a:
  $040b3a: move.w 6(A6),D0
  $040b3e: cmpi.w #$ab4,D0
  $040b42: bcc $40b4e
  $040b44: addq.b #1,D6
  $040b46: move.w #$ab4,6(A6)
  $040b4c: rts
L40b4e:
  $040b4e: cmpi.w #$bf4,D0
  $040b52: bcs $40b5c
  $040b54: addq.b #1,D6
  $040b56: move.w #$bf3,6(A6)
L40b5c:
  $040b5c: rts
L40b5e:
  $040b5e: moveq #0,D6
  $040b60: bsr $40b6a
  $040b64: bsr $40b3a
  $040b66: tst.b D6
  $040b68: rts
L40b6a:
  $040b6a: move.w 14(A6),D0
  $040b6e: cmpi.w #$10,D0
  $040b72: bcc $40b80
  $040b74: addq.b #1,D6
  $040b76: move.l #$100000,14(A6)
  $040b7e: rts
L40b80:
  $040b80: cmpi.w #$40,D0
  $040b84: blt $40b90
  $040b86: addq.b #1,D6
  $040b88: move.l #$3f0000,14(A6)
L40b90:
  $040b90: rts
L40b92:
  $040b92: clr.b 46(A6)
  $040b96: movea.l 128(A6),A1
  $040b9a: move.w 6(A1),D0
  $040b9e: cmp.w 6(A6),D0
  $040ba2: bhi $40baa
  $040ba4: move.b #$1,46(A6)
L40baa:
  $040baa: rts
L40bac:
  $040bac: movea.l 50(A6),A1
  $040bb0: moveq #0,D1
  $040bb2: move.b 54(A6),D1
  $040bb6: add.w D1,D1
  $040bb8: add.w D1,D1
  $040bba: moveq #0,D0
  $040bbc: move.w 0(A1,D1.w),D0
  $040bc0: swap D0
  $040bc2: asr.l #8,D0
  $040bc4: add.l D0,6(A6)
  $040bc8: move.w 2(A1,D1.w),D1
  $040bcc: ext.l D1
  $040bce: lsl.l #8,D1
  $040bd0: add.l D1,14(A6)
  $040bd4: add.l D1,10(A6)
  $040bd8: rts
L40bda:
  $040bda: move.w 132(A6),D0
  $040bde: sub.w 6(A6),D0
  $040be2: addi.w #$9,D0
  $040be6: cmpi.w #$12,D0
  $040bea: bhi $40c02
  $040bec: move.w 134(A6),D0
  $040bf0: sub.w 10(A6),D0
  $040bf4: addi.w #$9,D0
  $040bf8: cmpi.w #$12,D0
  $040bfc: bhi $40c02
  $040bfe: moveq #1,D0
  $040c00: rts
L40c02:
  $040c02: moveq #0,D0
  $040c04: rts
L40c06:
  $040c06: move.b #$1,D0
  $040c0a: and.b 167(A5),D0
  $040c0e: beq $40c4a
  $040c12: move.w 132(A6),D0
  $040c16: move.w 134(A6),D1
  $040c1a: jsr $31f4.w
  $040c1e: addi.b #$4,D6
  $040c22: lsr.b #3,D6
  $040c24: bra $40c28
L40c28:
  $040c28: sub.b 54(A6),D6
  $040c2c: beq $40c4a
  $040c2e: move.b #$1,D2
  $040c32: andi.b #$1f,D6
  $040c36: cmpi.b #$10,D6
  $040c3a: bcs $40c40
  $040c3c: move.b #$ff,D2
L40c40:
  $040c40: add.b D2,54(A6)
  $040c44: andi.b #$1f,54(A6)
L40c4a:
  $040c4a: bra $40842
L40c4e:
  $040c4e: cmpi.w #$bf4,D3
  $040c52: bcc $40c6a
  $040c54: cmpi.w #$ab4,D3
  $040c58: bcs $40c6a
  $040c5a: cmpi.w #$10,D4
  $040c5e: bcs $40c6a
  $040c60: cmpi.w #$40,D4
  $040c64: bge $40c6a
  $040c66: moveq #0,D0
  $040c68: rts
L40c6a:
  $040c6a: moveq #1,D0
  $040c6c: rts

; tables
;  $3d3e2: 0->3d3ea 1->3d570 2->3eb82 3->3ed30
;  $3d3f6: 0->3d3fe 1->3d42a 2->3d4f2 3->3d510
;  $3d530: 0->3d538 1->3d544 2->3d552 3->3d562
;  $3d5b8: 0->3d5d2 1->3db26 2->3dfc4 3->3e4c2 4->3e54e 5->3e5e0 6->3e79e
;  $3d5c6: 0->3d694 1->3d6a0 2->3d732 3->3d74c 4->3d9aa 5->3da9a
;  $3d5fa: 0->3d602 1->3d604 2->3d626 3->3d648
;  $3d758: 0->3d760 1->3d81e 2->3d8f2 3->3d912
;  $3d76c: 0->3d778 1->3d78c 2->3d7aa 3->3d7d2 4->3d954 5->3d994
;  $3d82a: 0->3d838 1->3d84c 2->3d86a 3->3d892 4->3d8de 5->3d954 6->3d994
;  $3d8fe: 0->3d906 1->3d932 2->3d954 3->3d994
;  $3d91e: 0->3d926 1->3d932 2->3d954 3->3d994
;  $3d9b6: 0->3d9ba 1->3d9ee
;  $3dacc: 0->3dad2 1->3dade 2->3db0a
;  $3db1c: 0->3db98 1->3dc40 2->3dd2e 3->3dd56 4->3df4c
;  $3dc58: 0->3dc5c 1->3dcb2
;  $3dd62: 0->3dd6c 1->3dd9e 2->3ddd0 3->3de02 4->3de34
;  $3dd78: 0->3dd80 1->3dd88 2->3ded4 3->3df12
;  $3ddaa: 0->3ddb2 1->3ddba 2->3ded4 3->3df12
;  $3dddc: 0->3dde4 1->3ddec 2->3ded4 3->3df12
;  $3de0e: 0->3de16 1->3de1e 2->3ded4 3->3df12
;  $3de40: 0->3de4a 1->3de7e 2->3de9a 3->3ded4 4->3df12
;  $3df58: 0->3df5c 1->3df92
;  $3dfd0: 0->3dfd6 1->3dffa 2->3e46c
;  $3e008: 0->3e01a 1->3e058 2->3e01a 3->3e0ce 4->3e460 5->3e20e 6->3e324 7->3e0ce 8->3e43a
;  $3e026: 0->3e02e 1->3e036 2->3e046 3->3e074
;  $3e064: 0->3e06c 1->3e036 2->3e046 3->3e074
;  $3e0da: 0->3e0e6 1->3e0ee 2->3e12a 3->3e19a 4->3e1da 5->3e1f8
;  $3e21a: 0->3e222 1->3e260 2->3e2d4 3->3e310
;  $3e330: 0->3e338 1->3e376 2->3e3ea 3->3e426
;  $3e446: 0->3e452 1->3e0ee 2->3e12a 3->3e19a 4->3e1da 5->3e1f8
;  $3e4ce: 0->3e4d2 1->3e522
;  $3e55a: 0->3e562 1->3e57a 2->3e5b4 3->3e5c2
;  $3e5ec: 0->3e5f6 1->3e622 2->3e6de 3->3e71e 4->3e760
;  $3e7aa: 0->3e7b4 1->3e89e 2->3e8ae 3->3e8e2 4->3e942
;  $3e7c0: 0->3e7c6 1->3e800 2->3e824
;  $3e8fe: 0->3e902 1->3e930
;  $3e94e: 0->3e954 1->3e996 2->3e9ba
;  $3ea56: 0->3ea5a 1->3ea66
;  $3eab4: 0->3eac6 1->3eac6 2->3eac6 3->3eace 4->3eaec 5->3eaee 6->3eaee 7->3eb16 8->3eb16
;  $3eb92: 0->3eb98 1->3ecb2 2->3ecea
;  $3eba4: 0->3ebac 1->3ebe2 2->3ec52 3->3ec92
;  $3ecbe: 0->3ecc2 1->3ecd6
;  $3ecf6: 0->3ecfa 1->3ed2c
;  $4089a: 0->408a0 1->408c2 2->408ea
;  $408fa: 0->408fe 1->40920

; external calls (target: callers)
;  $9e4: 3d4a6 3e8be 3e92a 3f2f0
;  $aaa: 3e144 3e166 3e278 3e29c 3e38e 3e3b6 3e650 3e67c 3ebfc 3ec1e
;  $b8a: 3e6d8 3eafa 3eb42 3ed14 3edb8
;  $288c: 3ed26
;  $28b4: 3e6c6
;  $2fa2: 3d452
;  $2fd4: 3d59a
;  $30aa: 3de9a
;  $30d4: 3e13a 3e19a 3e26e 3e384 3e57a 3e63c 3e6de 3ebf2 3ec52
;  $315c: 3e1da 3e2d8 3e3ee 3e722 3ec92
;  $3184: 40854
;  $31f4: 40c1a
;  $32a2: 3d506 3d52c 3eb8e
;  $32aa: 3d5b4 3ea52
;  $32be: 3ea4e
;  $38f0: 3ed54
;  $3946: 3d40e 3ed36
;  $3b10: 3f3a2
;  $3b1c: 3f2c0 3f2c8 3f2d0 3f2d8 3f2e0 3f2e8 3f2f8 3f300 3f308 3f310 3f31e 3f326 3f32e 3f336 3f33e 3f346 3f34e 3f356 3f364 3f36e 3f376 3f37e 3f386 3f38e
;  $3b3c: 3d4f2 3d78c 3d7ce 3d81a 3d84c 3d88e 3d8da 3d8de 3db18 3dd9a 3ddcc 3ddfe 3de30 3de7e 3ded0 3e036 3e074 3e12a 3e1d6 3e20a 3e2d4 3e310 3e3ea 3e426 3e6b8 3e71a 3e71e 3e760 3e820 3e878 3e8ae 3e93e 3e9b6 3ea32 3ebe2 3ec8e 3ecfa 3ed2c 40832
;  $3b76: 40836
;  $3c26: 3d6a4 3d964 3d9be 3da0a 3dae8 3db9c 3dbaa 3dee2 3df60 3e4f2 4071c 40928 40944 4095a
;  $3f7a: 3e6bc
;  $412a: 3d570
;  $4166: 3eb46
;  $41ba: 3ea66
;  $4234: 3ea5e
;  $44d0: 3e190 3e25a 3e2ce 3e370 3e6b4 3ec48
;  $466a: 3d4b6 3d4c6 3d4d6 3d4e6
;  $5f9e: 3e8d2
;  $6c96: 3e646
;  $1b428: 3ed0e
