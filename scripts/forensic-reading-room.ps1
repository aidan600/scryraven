param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7332,

    # Offline launcher verification only; do not start the Reading Room.
    [switch]$PrepareOnly
)

$ErrorActionPreference = 'Stop'
$repository = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).ProviderPath
$venvPython = Join-Path $repository '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
    $pythonExecutable = $venvPython
}
else {
    $pythonExecutable = (Get-Command python -ErrorAction Stop).Source
}
$forensicRoot = [System.IO.Path]::GetFullPath('C:\tmp\scryraven-forensic').TrimEnd('\')

# Refuse redirected roots so this development launcher cannot write into a
# repository or another location through a junction or symbolic link.
foreach ($parent in @('C:\tmp', $forensicRoot)) {
    if (Test-Path -LiteralPath $parent) {
        $item = Get-Item -LiteralPath $parent -Force
        if (-not $item.PSIsContainer -or
            ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Unsafe forensic root component: $parent"
        }
    }
}

if (-not (Test-Path -LiteralPath $forensicRoot)) {
    New-Item -ItemType Directory -Path $forensicRoot -ErrorAction Stop | Out-Null
}

$gitSha = [string](& git -C $repository rev-parse HEAD 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "Could not read repository revision: $gitSha"
}
$gitBranch = [string](& git -C $repository branch --show-current 2>&1)
if ($LASTEXITCODE -ne 0) {
    throw "Could not read repository branch: $gitBranch"
}
if ([string]::IsNullOrWhiteSpace($gitBranch)) {
    $gitBranch = '(detached HEAD)'
}

# Read only built-in role defaults. Importing ModelConfig makes no provider call
# and avoids duplicating model policy in this development launcher.
$profileCode = 'import json; from dataclasses import asdict; from scryraven.model import ModelConfig; print(json.dumps(asdict(ModelConfig())))'
Push-Location $repository
try {
    $profileJson = [string](& $pythonExecutable -c $profileCode)
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not read the built-in model profile.'
    }
}
finally {
    Pop-Location
}
$modelProfile = $profileJson | ConvertFrom-Json

# A timestamp makes runs recognizable; the GUID keeps same-second launches
# distinct. Never reuse an existing run directory.
do {
    $runName = '{0}-{1}' -f (Get-Date -Format 'yyyyMMdd-HHmmss'),
        ([guid]::NewGuid().ToString('N').Substring(0, 12))
    $runDirectory = Join-Path $forensicRoot $runName
} while (Test-Path -LiteralPath $runDirectory)
New-Item -ItemType Directory -Path $runDirectory -ErrorAction Stop | Out-Null

$sessionDatabase = Join-Path $runDirectory 'sessions.sqlite3'
$dogfoodLog = Join-Path $runDirectory 'turns.jsonl'
$forensicLog = Join-Path $runDirectory 'observer.jsonl'
$manifestPath = Join-Path $runDirectory 'manifest.json'
$manifest = [ordered]@{
    forensic_mode = $true
    repository_path = $repository
    git_sha = $gitSha.Trim()
    git_branch = $gitBranch.Trim()
    run_directory = $runDirectory
    session_database_path = $sessionDatabase
    dogfood_log_path = $dogfoodLog
    forensic_observer_log_path = $forensicLog
    port = $Port
    launch_timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
    model_profile = $modelProfile
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $manifestPath,
    ($manifest | ConvertTo-Json -Depth 3),
    $utf8NoBom
)

$readingRoomArgs = @(
    '-m', 'scryraven.reading_room',
    '--database', $sessionDatabase,
    '--dogfood-log', $dogfoodLog,
    '--forensic-log', $forensicLog,
    '--port', [string]$Port
)

Write-Output 'FORENSIC DOGFOOD MODE'
Write-Output 'Source text and diagnostic observer events are being saved locally.'
Write-Output "Reading Room URL: http://127.0.0.1:$Port"
Write-Output "Run directory: $runDirectory"
Write-Output "Sessions DB: $sessionDatabase"
Write-Output "Body-free dogfood log: $dogfoodLog"
Write-Output "Forensic observer log: $forensicLog"
Write-Output "Manifest: $manifestPath"
Write-Output ('Command: & "{0}" -m scryraven.reading_room --database "{1}" --dogfood-log "{2}" --forensic-log "{3}" --port {4}' -f
    $pythonExecutable, $sessionDatabase, $dogfoodLog, $forensicLog, $Port)

if ($PrepareOnly) {
    Write-Output 'Prepared only; Reading Room was not started.'
    return
}

Push-Location $repository
try {
    & $pythonExecutable @readingRoomArgs
    $readingRoomExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
if ($readingRoomExitCode -ne 0) {
    exit $readingRoomExitCode
}
