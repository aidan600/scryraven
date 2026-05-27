param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

python -m pytest @Args
