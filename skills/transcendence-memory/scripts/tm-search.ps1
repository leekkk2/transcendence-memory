param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$globalFlags = @(); $rest = @()
foreach ($item in $CliArgs) { if ($item -eq '--json') { $globalFlags += $item } else { $rest += $item } }
& (Join-Path $PSScriptRoot 'tm.ps1') @globalFlags @rest
exit $LASTEXITCODE
