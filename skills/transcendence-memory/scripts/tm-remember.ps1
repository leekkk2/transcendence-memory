param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$globalFlags = @(); $rest = @()
foreach ($item in $CliArgs) { if ($item -eq '--json') { $globalFlags += $item } elseif ($item -eq '--no-embed') { $rest += '--no-auto-embed' } else { $rest += $item } }
& (Join-Path $PSScriptRoot 'tm.ps1') @globalFlags remember @rest
exit $LASTEXITCODE
