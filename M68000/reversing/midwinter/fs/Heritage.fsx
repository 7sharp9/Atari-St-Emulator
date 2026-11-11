/// Where the terrain came from: Midwinter's memory, read the way the 68000 laid it out.
/// A cell is one big-endian longword, (height.w, seed.w); a grid is rows of cells with no padding.
/// The island is file 37.2, a 50 x 50 grid the game loads at $4a104 (terrain.md section 1).
module Heritage

open System
open System.IO

/// The RAM image of an emulator snapshot (tools/gfxview.py load_ram has the same layout).
let loadRam (path: string) : byte[] =
    let d = File.ReadAllBytes path
    if d.[0..3] <> "A68S"B then failwithf "%s: not a snapshot" path
    let regCount = if d.[4] >= 5uy then 19 else 18
    let off = 5 + regCount * 4 + 2
    let len = BitConverter.ToInt32(d, off)
    d.[off + 4 .. off + 3 + len]

let word (ram: byte[]) (a: int) = (int ram.[a] <<< 8) ||| int ram.[a + 1]

/// A signed 68000 word.
let sword (ram: byte[]) (a: int) = int (int16 (word ram a))

let long (ram: byte[]) (a: int) = (word ram a <<< 16) ||| word ram (a + 2)

module Addr =
    let file372 = 0x4a104          // the 50 x 50 island
    let grid = 0x404c4             // the 100 x 100 working grid around the player
    let target = 0x19cd4           // ($19cd4, $19cd6): where the player is, in finest cells
    let origin = 0x19cda           // ($19cda, $19cdc): the working grid's top-left after $19962
    let camCell = 0x12c80          // longword: the grid cell the 3D view starts from
    let camHeight = 0x1721c        // the camera's height, in the grid's height units
