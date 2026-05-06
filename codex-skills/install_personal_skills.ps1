param(
    [string]$CodexSkillsPath = "$env:USERPROFILE\.codex\skills"
)

$ErrorActionPreference = "Stop"

$sourceRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$skillNames = @("handoff", "catchup", "clean")

New-Item -ItemType Directory -Force -Path $CodexSkillsPath | Out-Null

foreach ($skillName in $skillNames) {
    $source = Join-Path $sourceRoot $skillName
    $target = Join-Path $CodexSkillsPath $skillName

    if (-not (Test-Path -LiteralPath $source)) {
        throw "Missing skill source: $source"
    }

    if (Test-Path -LiteralPath $target) {
        Remove-Item -LiteralPath $target -Recurse -Force
    }

    Copy-Item -LiteralPath $source -Destination $target -Recurse
    Write-Host "Installed $skillName -> $target"
}

Write-Host "Done. Restart Codex if the new skills do not appear immediately."
