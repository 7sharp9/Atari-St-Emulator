// fsi_drive.fsx: drive the F# core from F# Interactive (typed, no rebuild). Run from M68000/ (the ROM path is cwd-relative):
//   sh tools/fsi_prep.sh                      # once per build: copies bin/ to scratchpad/fsi/dll
//   DOTNET_gcServer=0 dotnet fsi tools/fsi_drive.fsx --snap <snap> --steps <N> [--disk <.st>] [--out <snap>] [--rom <img>]
//                                          [--watch <lo>[-<hi>]] [--poke <addr>=<byte>]...        (addresses are hex)
// --watch prints the REPL's WATCH lines (the core's own MMU.SetWatch; odd addresses miss word writes, watch the even byte below).
// --poke writes a byte before the run. Copy this file and edit the loop for anything the flags do not cover: `st.Step()`, `st.Cpu.PC`,
// `st.Cpu.MMU.ReadByte/ReadWord/ReadLong/WriteByte/WriteWord/WriteLong` are all typed. See DEVELOPING.md "F# Interactive".
#r "../scratchpad/fsi/dll/M68000.dll"
open System
open System.Diagnostics
open Atari

let args = fsi.CommandLineArgs |> Array.skip 1
let opt (k: string) = args |> Array.tryFindIndex ((=) k) |> Option.map (fun i -> args.[i + 1])
let opts (k: string) = [ for i in 0 .. args.Length - 2 do if args.[i] = k then yield args.[i + 1] ]
let hex (s: string) = Convert.ToUInt32(s.Replace("$", "").Replace("0x", ""), 16)
let say (s: string) = Console.Error.WriteLine s

let snap = match opt "--snap" with Some s -> s | None -> failwith "--snap <snapshot> required"
let steps = match opt "--steps" with Some s -> int s | None -> failwith "--steps <N> required"

Trace.enabled <- false      // the core prints a line per instruction otherwise (the switch ATARI_NOTRACE flips)
Console.SetOut(IO.TextWriter.Null)

let st = AtartSt(defaultArg (opt "--rom") "TOS100UK.IMG", ?diskAPath = opt "--disk")
st.LoadState snap
let mmu = st.Cpu.MMU
for p in opts "--poke" do
    let a, v = match p.Split('=') with [| a; v |] -> hex a, byte (hex v) | _ -> failwith "--poke <addr>=<byte>"
    mmu.WriteByte a v

let origErr = Console.Error
let cap = new IO.StringWriter()
match opt "--watch" with
| Some w ->
    let lo, hi = match w.Split('-') with [| a |] -> hex a, hex a | [| a; b |] -> hex a, hex b | _ -> failwith "--watch <lo>[-<hi>]"
    Console.SetError cap
    mmu.SetWatch lo hi
| None -> ()

let sw = Stopwatch.StartNew()
for _ in 1 .. steps do st.Step()
mmu.ClearWatch()
Console.SetError origErr
for l in cap.ToString().Split('\n') do if l.StartsWith "WATCH:" then Console.Error.WriteLine l
say (sprintf "%d steps in %d ms (%.0f ms/M), PC=$%06x" steps sw.ElapsedMilliseconds (float sw.ElapsedMilliseconds * 1e6 / float steps) st.Cpu.PC)
match opt "--out" with Some o -> st.SaveState o | None -> ()
