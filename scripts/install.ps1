param([string]$Python = 'python', [Parameter(ValueFromRemainingArguments=$true)][string[]]$Options)
$ErrorActionPreference = 'Stop'
& $Python (Join-Path $PSScriptRoot 'install.py') @Options
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; existing rules and credentials were not replaced.' }
