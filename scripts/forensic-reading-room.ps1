param(
    [ValidateRange(1, 65535)]
    [int]$Port = 7332,

    # Offline launcher verification only; do not start the Reading Room.
    [switch]$PrepareOnly,

    [ValidateRange(60, 604800)]
    [int]$TimeoutSeconds = 86400
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

# Read effective local role settings. Importing ModelConfig makes no provider call
# and avoids duplicating model policy in this development launcher.
$profileCode = 'import json; from dataclasses import asdict; from scryraven.model import ModelConfig; print(json.dumps(asdict(ModelConfig())))'
Push-Location $repository
try {
    $profileJson = [string](& $pythonExecutable -c $profileCode)
    if ($LASTEXITCODE -ne 0) {
        throw 'Could not read the effective model profile.'
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
    inference_backend = 'chatgpt_plan'
    plan_account = 'personal'
    api_inference_fallback = $false
    acquisition_configuration = $null
    launch_status = 'prepared'
    server_pid = $null
    safe_error_code = $null
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText(
    $manifestPath,
    ($manifest | ConvertTo-Json -Depth 3),
    $utf8NoBom
)

$credentialFile = 'C:\Users\aidan\AppData\Local\ScryRaven\credentials.env'
$brokerStdout = Join-Path $runDirectory 'broker.stdout.txt'
$brokerStderr = Join-Path $runDirectory 'broker.stderr.txt'
$brokerStatus = Join-Path $runDirectory 'broker.status.json'
$brokerArgs = @(
    (Join-Path $repository 'scripts\run_brokered_command_once.py'),
    '--repo-root', $repository,
    '--env-file', $credentialFile,
    '--stdout', $brokerStdout,
    '--stderr', $brokerStderr,
    '--status', $brokerStatus,
    '--timeout-seconds', [string]$TimeoutSeconds,
    '--target-current-python', '--',
    '-m', 'scripts.forensic_reading_room', '--run-directory', $runDirectory
)

Write-Output 'FORENSIC DOGFOOD MODE'
Write-Output 'Source text and diagnostic observer events are being saved locally.'
Write-Output "Requested Reading Room URL: http://127.0.0.1:$Port"
Write-Output "Run directory: $runDirectory"
Write-Output "Sessions DB: $sessionDatabase"
Write-Output "Body-free dogfood log: $dogfoodLog"
Write-Output "Forensic observer log: $forensicLog"
Write-Output "Manifest: $manifestPath"
Write-Output 'Inference backend: chatgpt_plan'
Write-Output 'Account label: personal'
Write-Output 'API inference fallback: disabled'
Write-Output ('Effective Research/Answer profile: {0}' -f ($modelProfile | ConvertTo-Json -Compress -Depth 3))
Write-Output ('Command: powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}" -Port {1} 2>&1' -f
    (Join-Path $repository 'scripts\forensic-reading-room.ps1'), $Port)

if ($PrepareOnly) {
    Write-Output 'Prepared only; Reading Room was not started.'
    return
}

# Start only the existing doorman. The public launcher never opens the private
# credential file; the child publishes fixed diagnostics and boolean readiness.
$quotedBrokerArgs = @($brokerArgs | ForEach-Object { '"{0}"' -f $_ })
$brokerProcess = Start-Process -FilePath $pythonExecutable -ArgumentList $quotedBrokerArgs `
    -WorkingDirectory $repository -WindowStyle Hidden -PassThru
$deadline = (Get-Date).AddSeconds(30)
$ready = $false
while ((Get-Date) -lt $deadline) {
    $brokerProcess.Refresh()
    $childManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ($childManifest.launch_status -eq 'ready') {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$Port/" -TimeoutSec 2
            $ready = $response.StatusCode -eq 200
        }
        catch { $ready = $false }
        if ($ready) { break }
    }
    if ($brokerProcess.HasExited -or $childManifest.launch_status -eq 'failed') { break }
    Start-Sleep -Milliseconds 100
}
if (-not $ready) {
    if (-not $brokerProcess.HasExited) {
        # This exact process tree was created above for this run. Do not leave
        # a delayed or failed startup alive after reporting launch failure.
        $termination = @(& taskkill.exe /PID $brokerProcess.Id /T /F 2>&1)
        $brokerProcess.WaitForExit(5000) | Out-Null
    }
    Write-Output "Reading Room not ready. Safe launch status: $($childManifest.launch_status)"
    Write-Output "Safe child error: $($childManifest.safe_error_code)"
    Write-Output "Sanitized broker status: $brokerStatus"
    Write-Output "Sanitized broker stdout/stderr: $brokerStdout ; $brokerStderr"
    if (Test-Path -LiteralPath $brokerStatus -PathType Leaf) {
        Write-Output (Get-Content -LiteralPath $brokerStatus -Raw)
    }
    exit 1
}
Write-Output "Reading Room ready: http://127.0.0.1:$Port"
Write-Output ('Acquisition configuration: {0}' -f ($childManifest.acquisition_configuration | ConvertTo-Json -Compress))
Write-Output ('Verified Research/Answer profile: {0}' -f ($childManifest.model_profile | ConvertTo-Json -Compress -Depth 3))
Write-Output "Server PID: $($childManifest.server_pid)"
Write-Output 'Plan account access and inference are deferred until the first user question.'
Write-Output ('Stop only this run: powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{0}" -RunDirectory "{1}" 2>&1' -f
    (Join-Path $repository 'scripts\stop-forensic-reading-room.ps1'), $runDirectory)
$brokerProcess.WaitForExit()
if ($brokerProcess.ExitCode -ne 0) {
    Write-Output "Broker exited with code $($brokerProcess.ExitCode). See $brokerStatus"
    exit $brokerProcess.ExitCode
}
