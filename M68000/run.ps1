#!/usr/bin/env pwsh
#
# Build-once / exec-many wrapper for the Atari ST emulator. See DEVELOPING.md.
#
# Why this exists: a live `window` instance locks M68000.exe, and `dotnet run`
# rebuilds every invocation, so every session ends up hand-typing
# `dotnet build` then `dotnet exec bin/Debug/net8.0/M68000.dll ...`. This does
# the build once (skippable) and always `exec`s the DLL, from the M68000/
# directory so TOS100UK.IMG / checkpoint.txt resolve.
#
# Usage:
#   ./run.ps1 <subcommand> [args]        build (unless -NoBuild), then run
#   ./run.ps1 -NoBuild <subcommand> ...  skip the build
#   ./run.ps1 -Trace <subcommand> ...    keep the per-instruction trace (default: ATARI_NOTRACE=1)
#
# Subcommands (thin aliases over Program.fs's argv modes):
#   boot   <N>                 run N steps from cold boot (trace ON by default here)
#   trace  <N>                 alias for `boot`, trace explicitly ON
#   snap   <N> <path>          run N steps, save a snapshot
#   resume <path> [N]          load snapshot, run N more steps      (N default 20000000)
#   repl   [N]                 cold boot + N steps, then REPL       (N default 20000)
#   rrepl  <path>              load snapshot, then REPL
#   window [path]              live SDL2 window (optionally from a snapshot)
#   verify <N>                 run N steps, diff against checkpoint.txt
#   check  <N>                 run N steps, (re)write checkpoint.txt
#   teartest <snap> <frames>   headless cursor-path frame dump
#   selftest <dir> [substr]    680x0 ProcessorTests vectors vs Cpu.Step
#   dll                        print the DLL path and exit
#
param(
    [switch] $NoBuild,
    [switch] $Trace,
    [string] $Command
)

# Leftover positional args land in $args (plain script, no CmdletBinding - so piped
# stdin passes straight through to `dotnet exec` for the REPL).
$Rest = $args
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dll = Join-Path $here 'bin/Debug/net8.0/M68000.dll'

if (-not $Command) {
    Get-Content $PSCommandPath | Select-Object -First 40 | ForEach-Object { $_ -replace '^# ?', '' }
    exit 1
}

if (-not $NoBuild -and $Command -ne 'dll') {
    dotnet build -c Debug "$here/M68000.fsproj" | Out-Host
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# Trace defaults: ON for boot/trace (you run those to read the trace), OFF elsewhere.
$traceByDefault = $Command -in @('boot', 'trace')
if ($Trace -or $traceByDefault) { Remove-Item Env:ATARI_NOTRACE -ErrorAction SilentlyContinue }
else { $env:ATARI_NOTRACE = '1' }

$argv =
    switch ($Command) {
        'boot'     { @($Rest[0]) }
        'trace'    { @($Rest[0]) }
        'snap'     { @($Rest[0], 'snapshot', $Rest[1]) }
        'resume'   { @(($Rest[1] ?? '20000000'), 'resume', $Rest[0]) }
        'repl'     { if ($Rest[0]) { @($Rest[0], 'repl') } else { @() } }  # no N -> default 20000 steps + REPL
        'rrepl'    { @('resume', $Rest[0], 'repl') }
        'window'   { if ($Rest[0]) { @('window', 'resume', $Rest[0]) } else { @('window') } }
        'verify'   { @($Rest[0], 'verify') }
        'check'    { @($Rest[0], 'checkpoint') }
        'teartest' { @('teartest', $Rest[0], $Rest[1]) }
        'selftest' { @('selftest') + ($Rest | Where-Object { $_ }) }
        'dll'      { Write-Output $dll; exit 0 }
        default    { Write-Error "unknown subcommand '$Command' (run ./run.ps1 with no args for help)"; exit 2 }
    }

Push-Location $here
try {
    if ($MyInvocation.ExpectingInput) { $input | dotnet exec $dll @argv }
    else { dotnet exec $dll @argv }
}
finally { Pop-Location }
exit $LASTEXITCODE
