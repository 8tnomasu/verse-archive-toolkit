param(
    [ValidateSet("All", "Builder", "Translator")]
    [string]$Target = "All"
)

$ErrorActionPreference = "Stop"
$utf8 = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = $utf8
try {
    [Console]::InputEncoding = $utf8
    [Console]::OutputEncoding = $utf8
}
catch {
}
try {
    chcp 65001 > $null
}
catch {
}

$scriptPath = Join-Path $PSScriptRoot "build-windows.ps1"
& $scriptPath -Mode Release -Target $Target
