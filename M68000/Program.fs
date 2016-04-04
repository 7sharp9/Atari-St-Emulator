namespace Atari        
open System
open Bits
open Instructions

[<StructuredFormatDisplay("{Debug}")>]
type AtartSt(romPath) =
    let rom = IO.File.ReadAllBytes(romPath)
    let mmu = MMU(rom, [||])
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

module Main =
    let main args = 
        let st = AtartSt("/Users/dave/Desktop/100uk.img")
        st.Reset()
        for _ in 1..100 do
            st.Step()
    
