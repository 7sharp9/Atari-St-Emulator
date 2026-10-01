// Gate for port/godot/logic/Equipment.fs (138th pass).
//
//   cd M68000 && python3 reversing/powermonger/py/export_equip_corpus.py
//   dotnet build -c Debug reversing/powermonger/port/godot/logic/PmLogic.fsproj
//   dotnet fsi reversing/powermonger/py/equip_check.fsx [corpus.json]
//
// 1. Original mode against the REAL 68000: every case of the corpus (the 201 states of py/gate_equip.py, whose expected bytes
//    are the callcap deltas, plus the native e1/e2 exchanges) must leave the compared ranges byte-identical and return the
//    same D0.w/D1.w ($16892: D0 = 1 when it sent the man, else 0).
// 2. Corrected mode has no oracle (the original never ran it); it is checked by two properties on the same entry states:
//    for a lord < 8 it equals Original byte for byte, and for every lord only that lord's own goods change, with
//    sum(goods[0..7]) + [byte 44 <> 0] + [byte 33 <> 0] conserved (an item handed back is never lost or sent elsewhere).
#r "../port/godot/logic/bin/Debug/net8.0/PmLogic.dll"
open System
open System.IO
open System.Text.Json
open PmLogic

let path =
    match fsi.CommandLineArgs |> Array.tryItem 1 with
    | Some p -> p
    | None -> Path.Combine(__SOURCE_DIRECTORY__, "../../../scratchpad/pm138/equip_corpus.json")
let doc = JsonDocument.Parse(File.ReadAllText path).RootElement
let lo, dest = doc.GetProperty("lo").GetInt32(), doc.GetProperty("dest").GetInt32()
let hexBytes (s: string) = Convert.FromHexString s

type Case =
    { Name: string; Kind: string; Lords: byte[]; Man: byte[]; XLords: byte[]; XMan: byte[]
      Cmp: (int * int) list; D0: int option; D1: int option; D2: int option }

let optInt (e: JsonElement) (k: string) =
    match e.TryGetProperty k with
    | true, v when v.ValueKind = JsonValueKind.Number -> Some(v.GetInt32())
    | _ -> None

let cases =
    [ for c in doc.GetProperty("cases").EnumerateArray() ->
        { Name = c.GetProperty("name").GetString(); Kind = c.GetProperty("kind").GetString()
          Lords = hexBytes (c.GetProperty("lords").GetString()); Man = hexBytes (c.GetProperty("man").GetString())
          XLords = hexBytes (c.GetProperty("xlords").GetString()); XMan = hexBytes (c.GetProperty("xman").GetString())
          Cmp = [ for r in c.GetProperty("cmp").EnumerateArray() -> r.[0].GetInt32(), r.[1].GetInt32() ]
          D0 = optInt c "d0"; D1 = optInt c "d1"; D2 = optInt c "d2" } ]

let image (c: Case) =
    let ram = Array.zeroCreate<byte> 0x100000
    Array.blit c.Lords 0 ram lo c.Lords.Length
    Array.blit c.Man 0 ram dest c.Man.Length
    ram

let expected (c: Case) =
    let ram = image c
    Array.blit c.XLords 0 ram lo c.XLords.Length
    Array.blit c.XMan 0 ram dest c.XMan.Length
    ram

/// Run the routine the case names; returns (D0.w, D1.w option).
let run mode (c: Case) (ram: byte[]) =
    match c.Kind with
    | "tail" -> let struct (a, b) = Equipment.tail mode ram dest in a, Some b
    | "arriveFight" -> let struct (a, b) = Equipment.arriveFight mode ram dest in a, Some b
    | "arriveGoods" -> let struct (a, b) = Equipment.arriveGoods mode (fun _ _ -> ()) ram dest in a, Some b
    | "goods" -> (if Equipment.goodsRegroup ram dest c.D2.Value then 1 else 0), None
    | k -> failwithf "unknown kind %s" k

// ---- 1. Original vs the real 68000
let mutable bad = 0
let perKind = Collections.Generic.Dictionary<string, int * int>()
for c in cases do
    let ram = image c
    let want = expected c
    let d0, d1 = run Equipment.Original c ram
    let bytesOk = c.Cmp |> List.forall (fun (a, b) -> Array.sub ram a (b - a) = Array.sub want a (b - a))
    let regsOk = (c.D0.IsNone || c.D0 = Some d0) && (c.D1.IsNone || d1 = c.D1)
    let ok, n = match perKind.TryGetValue c.Kind with | true, v -> v | _ -> (0, 0)
    perKind.[c.Kind] <- ((if bytesOk && regsOk then ok + 1 else ok), n + 1)
    if not (bytesOk && regsOk) then
        bad <- bad + 1
        printfn "MISMATCH %s: bytes %b regs %b (D0 %d, real %A)" c.Name bytesOk regsOk d0 c.D0
let total = cases |> List.sumBy (fun c -> c.Cmp |> List.sumBy (fun (a, b) -> b - a))
printfn "Original vs real 68000: %d/%d cases identical (%d bytes compared)" (cases.Length - bad) cases.Length total
for kv in perKind do printfn "  %-12s %d/%d" kv.Key (fst kv.Value) (snd kv.Value)

// ---- 2. Corrected: properties
let w16 (ram: byte[]) a = (int ram.[a] <<< 8) ||| int ram.[a + 1]
let mutable propBad, lordLt8, lordLt8Same, conserved, ge8Conserved, origLeaks, nTail = 0, 0, 0, 0, 0, 0, 0
for c in cases |> List.filter (fun c -> c.Kind <> "goods") do
    nTail <- nTail + 1
    let entry = image c
    let lordOff = w16 entry (Equipment.Settlements + int (int16 (w16 entry (dest + 34))) + 14)
    let g = Equipment.Leaders + lordOff + 24
    let held (r: byte[]) = (if r.[dest + 44] <> 0uy then 1 else 0) + (if r.[dest + 33] <> 0uy then 1 else 0)
    let goods (r: byte[]) = seq { for k in 0 .. 7 -> int r.[g + k] } |> Seq.sum
    let a = image c
    run Equipment.Original c a |> ignore
    let b = image c
    run Equipment.Corrected c b |> ignore
    // only the own lord's goods may differ from the entry state
    let others = Seq.forall (fun i -> i >= g && i < g + 8 || b.[i] = entry.[i]) (seq { lo .. lo + c.Lords.Length - 1 })
    let cons (r: byte[]) = goods r + held r = goods entry + held entry
    if not others || not (cons b) then propBad <- propBad + 1; printfn "PROPERTY %s: others %b conserved %b" c.Name others (cons b)
    if lordOff / 32 < 8 then
        lordLt8 <- lordLt8 + 1
        if a = b then lordLt8Same <- lordLt8Same + 1
    elif not (cons a) || a <> b then origLeaks <- origLeaks + 1
printfn "Corrected: %d of %d non-goods cases keep every byte outside the own lord's goods and conserve goods+held (%d bad)" (nTail - propBad) nTail propBad
printfn "Corrected == Original for lord < 8: %d/%d; lord >= 8 cases where Original differs from Corrected: %d" lordLt8Same lordLt8 origLeaks
if bad = 0 && propBad = 0 && lordLt8Same = lordLt8 then printfn "GATE PASS" else printfn "GATE FAIL"; exit 1
