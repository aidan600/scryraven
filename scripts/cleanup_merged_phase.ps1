#Requires -Version 5.1
<#
.SYNOPSIS
  Thin Windows operator wrapper for repository-owned merged-phase cleanup.

.DESCRIPTION
  Accepts operator parameters, invokes scripts/cleanup_merged_phase.py, prints the
  captured summary, best-effort copies it to the clipboard, and preserves the
  Python process exit code. This wrapper does not implement Git cleanup logic.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ReviewedHead,

    [Parameter(Mandatory = $true)]
    [string]$PhaseBranch,

    [Parameter(Mandatory = $true)]
    [string]$PhaseRoot,

    [Parameter(Mandatory = $false)]
    [string]$Repo = "",

    [Parameter(Mandatory = $false)]
    [string]$Remote = "origin",

    [Parameter(Mandatory = $false)]
    [string]$MainBranch = "main",

    [Parameter(Mandatory = $false)]
    [string]$PhaseParent = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrWhiteSpace($Repo)) {
    $Repo = Split-Path -Parent $ScriptDir
}

$PyEngine = Join-Path $ScriptDir "cleanup_merged_phase.py"
if (-not (Test-Path -LiteralPath $PyEngine)) {
    Write-Host "cleanup engine not found: $PyEngine"
    exit 1
}

$PyArgs = @(
    $PyEngine,
    "--reviewed-head", $ReviewedHead,
    "--phase-branch", $PhaseBranch,
    "--phase-root", $PhaseRoot,
    "--repo", $Repo,
    "--remote", $Remote,
    "--main-branch", $MainBranch
)
if (-not [string]::IsNullOrWhiteSpace($PhaseParent)) {
    $PyArgs += @("--phase-parent", $PhaseParent)
}

# Safe native-command capture: array first, then join. Never (.Trim()) on a bare native call.
$Lines = @(& py @PyArgs 2>&1)
$Exit = $LASTEXITCODE
if ($null -eq $Exit) {
    $Exit = 1
}

$Text = ($Lines | ForEach-Object { "$_" }) -join "`n"
$Text = $Text.Trim()

if (-not [string]::IsNullOrWhiteSpace($Text)) {
    Write-Host $Text
} else {
    Write-Host "cleanup produced no output"
}

$ClipboardStatus = "unavailable"
try {
    Set-Clipboard -Value $Text
    $ClipboardStatus = "copied"
} catch {
    $ClipboardStatus = "unavailable"
}
Write-Host "Clipboard: $ClipboardStatus"

exit $Exit
