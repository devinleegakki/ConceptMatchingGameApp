param(
    [ValidateSet("apk", "aab")]
    [string]$Target = "apk"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot

# Android Gradle rejects non-ASCII Windows paths. Stage the project in an
# ASCII-only directory and copy the final artifact back to the workspace.
if ($projectRoot -match "[^\x00-\x7F]" -and $env:CONCEPT_MATCH_STAGED -ne "1") {
    $stageRoot = "C:\concept_match_build"
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
    New-Item -ItemType Directory -Path $stageRoot | Out-Null
    Get-ChildItem -LiteralPath $projectRoot -Force |
        Where-Object { $_.Name -notin @(".git", "build", "dist", ".flet") } |
        Copy-Item -Destination $stageRoot -Recurse -Force
    $env:CONCEPT_MATCH_STAGED = "1"
    & powershell -ExecutionPolicy Bypass -File (Join-Path $stageRoot "scripts\build_android_release.ps1") -Target $Target
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $builtArtifact = if ($Target -eq "apk") { Get-ChildItem -LiteralPath (Join-Path $stageRoot "build\apk") -File -Filter "*.apk" | Select-Object -First 1 -ExpandProperty FullName } else { Get-ChildItem -LiteralPath (Join-Path $stageRoot "build\aab") -File -Filter "*.aab" | Select-Object -First 1 -ExpandProperty FullName }
    $workspaceOutput = if ($Target -eq "apk") { Join-Path $projectRoot "build\apk" } else { Join-Path $projectRoot "build\aab" }
    New-Item -ItemType Directory -Path $workspaceOutput -Force | Out-Null
    Copy-Item -LiteralPath $builtArtifact -Destination $workspaceOutput -Force
    Write-Host "Copied staged artifact back to $workspaceOutput"
    exit 0
}

Set-Location $projectRoot
$env:PYTHONIOENCODING = "utf-8"
$env:FLET_CLI_LOG_FORMAT = "plain"
$env:FLET_CLI_NO_RICH_OUTPUT = "1"

Write-Host "Cleaning Flet temporary and build directories..."
foreach ($path in @("src\.flet", ".flet", "build", "dist")) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

Write-Host "Building $Target for arm64-v8a..."
$args = @(
    "build", $Target,
    "--arch", "arm64-v8a",
    "--cleanup-app",
    "--cleanup-packages",
    "--exclude", "src/.flet",
    "--exclude", ".flet",
    "--exclude", "tests",
    "--exclude", ".pytest_cache",
    "--exclude", "__pycache__",
    "--yes",
    "--skip-flutter-doctor"
)
& flet @args
if ($LASTEXITCODE -ne 0) { throw "Flet build failed with exit code $LASTEXITCODE" }

$artifact = if ($Target -eq "apk") { Get-ChildItem -LiteralPath (Join-Path $projectRoot "build\apk") -File -Filter "*.apk" | Select-Object -First 1 } else { Get-ChildItem -LiteralPath (Join-Path $projectRoot "build\aab") -File -Filter "*.aab" | Select-Object -First 1 }
if ($null -ne $artifact) {
    $sizeMb = [math]::Round($artifact.Length / 1MB, 1)
    Write-Host "Built artifact: $($artifact.FullName) ($sizeMb MB)"
}
