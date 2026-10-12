// F# half of the synthetic blit cross-check: Sprites.blitEntity on 13 synthetic
// records over one fixed cell, covered pixels per case in $XCHECK_OUT/blit_fs.txt.
// byte6 4 records take their jitter from the address (Sprites.propJitter), as in
// the game. The melee case (b31 $32) is expected to differ: the port draws it
// ($11c8a), pm_render_ref skips it.
#r "../../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open PmLogic
let outDir = match System.Environment.GetEnvironmentVariable "XCHECK_OUT" with null | "" -> "." | d -> d
open System.Text

let lcg (seed:int) (n:int) =
    let a = Array.zeroCreate<byte> n
    let mutable x = uint32 seed
    for i in 0 .. n-1 do
        x <- x * 1103515245u + 12345u
        a.[i] <- byte ((x >>> 16) &&& 0xffu)
    a
let sheet33 = lcg 1 (0x160 * 55)
let sheetProp = lcg 2 (28 * 480)

let c00 = (120,80)
let c10 = (150,78)
let c01 = (122,111)
let c11 = (151,109)

let ctx : Sprites.EntityCtx =
    { Yaw = 0xf0; Anim = false; SelGroup = 1; TileOff = 6; RotPhase = 2
      Sheet33 = sheet33; SheetProp = sheetProp; Ram = [||]; Zoom = 4; SheetProp32 = [||]; SheetProp16 = [||] }

let cases =
    [ // b6, b5, b7, b14, b17, b31, fx, fy, fx4, fy4, group
      (0, 1, 0x10, 0, 0x20, 0, 128, 100, 0,0, 0)
      (0, 2, 0x00, 0, 0x77, 0, 40, 200, 0,0, 0)
      (0, 3, 0x90, 0, 0x05, 0, 200,30, 0,0, 60)   // bit7 set, ram empty -> no +0x40
      (0, 4, 0x00, 0, 0xf0, 0x32, 10,10, 0,0, 0)  // melee -> None
      (4, 0, 0x11, 0, 0, 0, 0,0, 88, 120, 0)
      (4, 0, 0x0e, 0, 0, 0, 0,0, 12, 200, 0)
      (4, 0, 0x0d, 0, 0, 0, 0,0, 250, 5, 0)
      (8, 0, 0, 0x33, 0, 0, 150, 150, 0,0, 0)
      (8, 0, 0, 0x08, 0, 0, 22, 240, 0,0, 0)
      (14, 1, 0, 0, 0, 0, 90, 90, 0,0, 0)
      (14, 3, 0, 0, 0, 0, 5, 250, 0,0, 0)
      (24, 0, 0x10, 0, 0, 0, 0,0, 0,0, 0)
      (24, 0, 0x12, 0, 0, 0, 0,0, 0,0, 0) ]

let sb = StringBuilder()
for k, (b6,b5,b7,b14,b17,b31,fx,fy,_,_,grp) in List.indexed cases do
    let addr = 0x50000 + 0x2a * k   // byte6 4: the jitter comes from the address (propJitter)
    let fx4, fy4 = Sprites.propJitter 0x47970 addr 0x3F364
    let buf = Fill.Buffer.Create()
    let r : Sprites.EntityRec =
        { Addr=addr; B6=b6; B5=b5; B7=b7; B14=b14; B17=b17; B31=b31
          Fx=fx; Fy=fy; Group=grp; Wcx=0; Wcy=0
          B15=0; B32=0; W18=0; Icons=0; B33=0; B44=0; B16=0; W12=0 }
    Sprites.blitEntity buf ctx c00 c10 c01 c11 0 0 r
    let px =
        [ for y in 0 .. Fill.ScreenHeight-1 do
            for x in 0 .. Fill.ScreenWidth-1 do
              let i = y*Fill.ScreenWidth+x
              if buf.Covered.[i] then yield sprintf "%d,%d,%d" x y (int buf.Index.[i]) ]
    sb.AppendLine(sprintf "CASE b6=%d b5=%d b7=%d b14=%d b17=%d b31=%d fx=%d fy=%d fx4=%d fy4=%d grp=%d | %s"
                    b6 b5 b7 b14 b17 b31 fx fy fx4 fy4 grp (String.concat " " px)) |> ignore
System.IO.File.WriteAllText(System.IO.Path.Combine(outDir, "blit_fs.txt"), sb.ToString())
printfn "wrote fs output, %d cases" cases.Length
