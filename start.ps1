$ErrorActionPreference = 'Stop'
$toolDirectory = $PSScriptRoot
$settingsPath = Join-Path $toolDirectory 'settings.local.json'
if (-not (Test-Path -LiteralPath $settingsPath)) {
    Write-Host 'Please copy examples/settings.example.json to settings.local.json and configure Python, Blender, the PDX exporter, and CK3.'
    Read-Host 'Press Enter to close'
    exit 1
}
$toolSettings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
$env:PYTHONUTF8 = '1'
& $toolSettings.python -X utf8 (Join-Path $toolDirectory 'bridge_cli.py') serve
