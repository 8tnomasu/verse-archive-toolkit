param(
    [ValidateSet("All", "Builder", "Translator")]
    [string]$Target = "All"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "build-windows.ps1"
& $scriptPath -Mode Debug -Target $Target
