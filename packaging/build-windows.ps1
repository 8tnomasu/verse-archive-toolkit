param(
    [ValidateSet("Debug", "Release")]
    [string]$Mode = "Debug",

    [ValidateSet("All", "Builder", "Translator")]
    [string]$Target = "All"
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = (Resolve-Path (Join-Path $scriptDir "..")).Path
$srcDir = Join-Path $root "src"
$modeName = $Mode.ToLowerInvariant()
$distRoot = Join-Path $root "dist\windows\$modeName"
$workRoot = Join-Path $root "build\pyinstaller\$modeName"
$specRoot = Join-Path $root "build\pyinstaller\spec"

Set-Location $root

function Invoke-GuiBuild {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$EntryScript
    )

    $resolvedEntry = (Resolve-Path $EntryScript).Path
    $workPath = Join-Path $workRoot $Name
    New-Item -ItemType Directory -Force -Path $distRoot, $workPath, $specRoot | Out-Null

    $arguments = @(
        "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--paths", $srcDir,
        "--collect-all", "PySide6",
        "--collect-submodules", "shiboken6",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        "--distpath", $distRoot,
        "--workpath", $workPath,
        "--specpath", $specRoot,
        "--name", $Name
    )

    if ($Mode -eq "Debug") {
        $arguments += @("--console", "--debug=all")
    }
    else {
        $arguments += @("--windowed")
    }

    $arguments += $resolvedEntry

    Write-Host "開始打包 $Name（模式：$Mode）..." -ForegroundColor Cyan
    & python @arguments
}

if ($Target -in @("All", "Builder")) {
    $builderName = if ($Mode -eq "Debug") { "VerseArchiveToolkitDebug" } else { "VerseArchiveToolkit" }
    Invoke-GuiBuild -Name $builderName -EntryScript (Join-Path $srcDir "verse_archive_toolkit\builder_gui_entry.py")
}

if ($Target -in @("All", "Translator")) {
    $translatorName = if ($Mode -eq "Debug") { "VerseArchiveTranslatorDebug" } else { "VerseArchiveTranslator" }
    Invoke-GuiBuild -Name $translatorName -EntryScript (Join-Path $srcDir "verse_archive_toolkit\translator_gui_entry.py")
}

Write-Host "打包完成，輸出目錄：$distRoot" -ForegroundColor Green
