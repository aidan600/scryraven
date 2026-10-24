param(
    [Parameter(Mandatory = $true)]
    [string]$RunDirectory
)

$ErrorActionPreference = 'Stop'
$run = (Resolve-Path -LiteralPath $RunDirectory).ProviderPath
$manifest = Get-Content -LiteralPath (Join-Path $run 'manifest.json') -Raw | ConvertFrom-Json
if (-not $manifest.server_pid) { throw 'No server PID is recorded for this run.' }
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $($manifest.server_pid)"
if (-not $process) {
    Write-Output 'This forensic server is already stopped.'
    return
}
# Refuse PID reuse or any unrelated process. The exact run path and entrypoint
# must both occur in the recorded process command line before it is stopped.
$quotedRunArgument = '"--run-directory" "{0}"' -f $run
$plainRunArgument = '--run-directory {0}' -f $run
if (-not $process.CommandLine -or
    -not $process.CommandLine.Contains('scripts.forensic_reading_room') -or
    -not ($process.CommandLine.EndsWith($quotedRunArgument) -or
          $process.CommandLine.EndsWith($plainRunArgument) -or
          $process.CommandLine.EndsWith(('--run-directory "{0}"' -f $run)))) {
    throw 'The recorded PID does not identify this forensic run; nothing was stopped.'
}
Stop-Process -Id ([int]$manifest.server_pid) -ErrorAction Stop
Write-Output "Stopped forensic server PID $($manifest.server_pid) for $run"
