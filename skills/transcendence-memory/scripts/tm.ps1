param([Parameter(ValueFromRemainingArguments=$true)][string[]]$CliArgs)
$ErrorActionPreference = 'Stop'
$manifest = Join-Path $env:USERPROFILE '.transcendence-memory/install.json'
$python = $env:TM_PYTHON
if (-not $python -and (Test-Path $manifest)) { $python = (Get-Content -Raw $manifest | ConvertFrom-Json).python_executable }
if (-not $python) { $python = 'python' }
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
if (-not $CliArgs) { $CliArgs = @('--help') }
if ($CliArgs -contains '--token-stdin') { $input | & $python -X utf8 -m tm_cli.main @CliArgs; exit $LASTEXITCODE }
if ($CliArgs -contains '--manual') { & $python -X utf8 -m tm_cli.main @CliArgs; exit $LASTEXITCODE }
$envelope = ConvertTo-Json -InputObject @($CliArgs) -Compress
$encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($envelope))
('TM_ARGS_V1:' + $encoded) | & $python -X utf8 (Join-Path $PSScriptRoot 'tm-entry.py')
exit $LASTEXITCODE
