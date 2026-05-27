param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

Write-Host "Running lint checks..."
python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "Running tests..."
python -m pytest @Args
