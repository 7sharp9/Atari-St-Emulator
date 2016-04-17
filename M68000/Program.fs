#if INTERACTIVE
#load "Extensions.fs"
#load "MMU.fs"
#load "Instructions.fs"
#load "68k.fs"
open Atari
#else
namespace Atari
#endif

open System
open Bits
open Instructions

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath) =
    let rom = IO.File.ReadAllBytes(romPath)
    let ram = Array.create (1024 * 1024) 0uy
    let mmu = MMU(rom, ram)
    let mutable cpu = Cpu.Create(mmu)
    
    member x.Reset() = cpu <- cpu.Reset()
    member x.Rom = rom
    
    member x.Step() =
        cpu <- cpu.Step()
        printfn "%A" x
    
    member x.Debug =
       sprintf """
-------------
CPU Registers
%A
-------------""" cpu

#if INTERACTIVE 
let st = AtartSt("/Users/dave/Desktop/100uk.img")
st.Reset()
for _ in 1..100 do
    st.Step()
#else
module Main =
    [<EntryPoint>]
    let main arg=
        let st = AtartSt("/Users/dave/Desktop/100uk.img")
        st.Reset()
        for _ in 1..100 do
            st.Step()
        0
            
#endif
()
