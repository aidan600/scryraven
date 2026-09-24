param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$RunDirectory
)

$ErrorActionPreference = 'Stop'
$forensicRoot = [System.IO.Path]::GetFullPath('C:\tmp\scryraven-forensic').TrimEnd('\')
$requested = $RunDirectory
$resolved = '(unresolved)'
$validation = 'REJECTED'
$deleted = 'NO'
$capturedErrors = New-Object 'System.Collections.Generic.List[string]'

try {
    if ($requested -match '[*?\[\]]') {
        throw 'Wildcard or glob characters are not allowed.'
    }
    if ($requested -notmatch '^[A-Za-z]:[\\/]') {
        throw 'The run directory must be an absolute drive path.'
    }
    if (@($requested -split '[\\/]' | Where-Object { $_ -eq '.' -or $_ -eq '..' }).Count -gt 0) {
        throw 'Dot path segments are not allowed.'
    }

    $resolved = [System.IO.Path]::GetFullPath($requested).TrimEnd('\')
    $parent = [System.IO.Path]::GetDirectoryName($resolved)
    if (-not [System.StringComparer]::OrdinalIgnoreCase.Equals($parent, $forensicRoot)) {
        throw 'The run directory must be one direct child of the forensic root.'
    }
    if (-not (Test-Path -LiteralPath $resolved -PathType Container)) {
        throw 'The selected run directory does not exist.'
    }

    # Canonical lexical paths are safe only when no component redirects the
    # filesystem walk. Refuse reparse points at and below the selected child.
    foreach ($path in @('C:\tmp', $forensicRoot, $resolved)) {
        $item = Get-Item -LiteralPath $path -Force
        if (-not $item.PSIsContainer -or
            ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            throw "Unsafe redirected path component: $path"
        }
    }
    $pending = New-Object 'System.Collections.Generic.Stack[string]'
    $pending.Push($resolved)
    while ($pending.Count -gt 0) {
        $directory = $pending.Pop()
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Run contains a symbolic link or junction: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                $pending.Push($item.FullName)
            }
        }
    }

    $validation = 'APPROVED'
    $operationOutput = @(& { Remove-Item -LiteralPath $resolved -Recurse -Force -ErrorAction Stop } 2>&1)
    foreach ($line in $operationOutput) {
        if ($line -is [System.Management.Automation.ErrorRecord]) {
            $capturedErrors.Add([string]$line)
        }
    }
    if (Test-Path -LiteralPath $resolved) {
        throw 'The selected run directory still exists after removal.'
    }
    $deleted = 'YES'
}
catch {
    $capturedErrors.Add([string]$_)
}

function Format-CleanupSummary {
    $errorText = if ($capturedErrors.Count -eq 0) {
        'none'
    }
    else {
        $capturedErrors -join ' | '
    }
    @(
        "Requested run directory: $requested"
        "Resolved run directory: $resolved"
        "Forensic root: $forensicRoot"
        "Validation: $validation"
        "Deleted: $deleted"
        "Errors (2>&1): $errorText"
    ) -join [Environment]::NewLine
}

$summary = Format-CleanupSummary
try {
    Set-Clipboard -Value $summary -ErrorAction Stop
}
catch {
    $capturedErrors.Add("Clipboard: $([string]$_)")
    $summary = Format-CleanupSummary
}
Write-Output $summary
if ($deleted -ne 'YES') {
    exit 1
}
