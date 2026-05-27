param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

python -m ruff check . @Args
