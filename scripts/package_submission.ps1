[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [string]$ProjectRoot,
    [string]$WorkspaceRoot
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')

function Resolve-WinRarExecutable {
    $command = Get-Command 'WinRAR.exe' -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $candidates = @()
    $programFiles = [Environment]::GetEnvironmentVariable('ProgramFiles')
    $programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
    if ($programFiles) { $candidates += (Join-Path $programFiles 'WinRAR\WinRAR.exe') }
    if ($programFilesX86) { $candidates += (Join-Path $programFilesX86 'WinRAR\WinRAR.exe') }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'Supporting archive policy requires WinRAR, but WinRAR.exe was not found in PATH or the standard Program Files locations.'
}

$hub = Get-ModelingRoot
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier full
$selected = $resolved.Selected
if ($selected.CorePrefixMissing.Count -gt 0 -or -not $selected.Coverage['pypdf']) {
    throw "Submission packaging requires an independent prefix with pypdf; missing: $($selected.CorePrefixMissing -join ', ')"
}
$winRar = Resolve-WinRarExecutable

# Rebuild concise AI disclosure from the latest internal log immediately before
# staging so the support archive cannot contain a stale details PDF.
& (Join-Path $PSScriptRoot 'prepare_ai_disclosure.ps1') -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $sharedRoot

$output = Join-Path $root 'output'
$releaseManifest = Join-Path $output 'release\release_manifest.json'
if (Test-Path -LiteralPath $releaseManifest) {
    throw 'A sealed release already exists. Verify or archive it before rebuilding the package.'
}

# The formal package is sourced from one explicit tree. Its contents become
# the archive root so the support ZIP stays concise; paper/code_manifest.yaml
# maps project paths to archive members through support_path.
$submissionSource = Join-Path $root 'src\submission'
if (-not (Test-Path -LiteralPath $submissionSource -PathType Container)) {
    throw "Submission package source is missing: $submissionSource. Create the curated src/submission tree before packaging; no legacy fallback is enabled."
}
$reparse = @(Get-ChildItem -LiteralPath $submissionSource -Recurse -Force | Where-Object {
    ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
})
if ($reparse.Count -gt 0) {
    throw "Submission package source contains reparse points: $($reparse.FullName -join ', ')"
}

$zip = Join-Path $output 'supporting.zip'
$stage = Join-Path $output '.support-staging'
$stageAudit = Join-Path $output 'package_audit_staging.json'
$packageAudit = Join-Path $output 'package_audit.json'
if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
try {
    # The archive is assembled from an explicit allow-list. In particular,
    # generated MATLAB MAT/report files and Python bytecode never enter it.
    $entries = @()
    foreach ($name in @('README.md','requirements.txt','run.py')) {
        $entries += @{ source = Join-Path $submissionSource $name; destination = $name }
    }
    $entries += @(Get-ChildItem -LiteralPath (Join-Path $submissionSource 'code') -Recurse -File |
        Where-Object { $_.FullName -notmatch '[\\/]__pycache__[\\/]' -and $_.Extension -in @('.py','.m') } |
        ForEach-Object {
            $relative = $_.FullName.Substring((Join-Path $submissionSource 'code').Length).TrimStart('\').Replace('\','/')
            @{ source = $_.FullName; destination = ('code/' + $relative) }
        })
    $entries += @(Get-ChildItem -LiteralPath (Join-Path $submissionSource 'matlab') -Recurse -File |
        Where-Object { $_.FullName -notmatch '[\\/](derived|reports|__pycache__)[\\/]' -and $_.Extension -eq '.m' } |
        ForEach-Object {
            $relative = $_.FullName.Substring((Join-Path $submissionSource 'matlab').Length).TrimStart('\').Replace('\','/')
            @{ source = $_.FullName; destination = ('code/matlab/' + $relative) }
        })
    foreach ($folder in @('input','results','manifest')) {
        $folderPath = Join-Path $submissionSource $folder
        if (Test-Path -LiteralPath $folderPath) {
            $entries += @(Get-ChildItem -LiteralPath $folderPath -Recurse -File |
                Where-Object { $_.FullName -notmatch '[\\/](__pycache__|derived|reports)[\\/]' } |
                ForEach-Object {
                    $relative = $_.FullName.Substring($submissionSource.Length).TrimStart('\').Replace('\','/')
                    @{ source = $_.FullName; destination = $relative }
                })
        }
    }
    foreach ($entry in $entries) {
        if (-not (Test-Path -LiteralPath $entry.source -PathType Leaf)) {
            throw "Submission package source file is missing: $($entry.source)"
        }
        $relative = [string]$entry.destination
        $parts = $relative.Split('/')
        if ($parts | Where-Object { $_ -eq '..' -or $_ -eq '.' -or $_.StartsWith('.') }) {
            throw "Submission package destination contains a hidden or traversal path: $relative"
        }
        $destination = Join-Path $stage ($relative.Replace('/', '\'))
        $destinationParent = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationParent | Out-Null
        Copy-Item -LiteralPath $entry.source -Destination $destination -Force
    }

    $embeddedManifest = Join-Path $stage 'manifest\package_manifest.sha256'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $embeddedManifest) | Out-Null
    $embeddedLines = Get-ChildItem -LiteralPath $stage -Recurse -File |
        Where-Object { $_.FullName -ne $embeddedManifest } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($stage.Length).TrimStart('\').Replace('\','/')
            "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $relative"
        }
    $embeddedLines | Set-Content -LiteralPath $embeddedManifest -Encoding ASCII

    $stagingRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\utils\audit_package.py'),
        '--source',$stage,'--output',$stageAudit,'--strict'
    ) -CaptureOutput -DisableUserSite
    if ($stagingRun.ExitCode -ne 0) { throw 'Supporting staging failed deep anonymity/package audit.' }

    $manifestPath = Join-Path $output 'supporting_manifest.sha256'
    $manifestLines = Get-ChildItem -LiteralPath $stage -Recurse -File | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($stage.Length).TrimStart('\').Replace('\','/')
        "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $relative"
    }
    $manifestLines | Set-Content -LiteralPath $manifestPath -Encoding ASCII
    if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }

    # CUMCM 2026 requires the support archive to be created with WinRAR.
    # Run WinRAR from inside the staging directory so the archive root contains
    # only the curated allow-list members rather than the staging folder itself.
    Push-Location $stage
    try {
        & $winRar 'a' '-afzip' '-ep1' '-m5' '-r' '-y' $zip '*' | Out-Null
        $winRarExitCode = $LASTEXITCODE
        if ($winRarExitCode -ne 0) {
            throw "WinRAR failed to create supporting.zip (exit code $winRarExitCode)."
        }
    } finally {
        Pop-Location
    }
    if (-not (Test-Path -LiteralPath $zip -PathType Leaf)) {
        throw 'WinRAR completed without producing supporting.zip.'
    }
} finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}

$archiveRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
    'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\utils\audit_package.py'),
    '--source',$zip,'--output',$packageAudit,'--strict'
) -CaptureOutput -DisableUserSite
if ($archiveRun.ExitCode -ne 0) { throw 'Supporting archive failed deep anonymity/package audit.' }

$overallManifest = Join-Path $output 'manifest.sha256'
$overallMd5Manifest = Join-Path $output 'manifest.md5'
$hashLines = foreach ($path in @((Join-Path $output 'submission.pdf'), $zip)) {
    if (Test-Path -LiteralPath $path) {
        "$((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant())  $([System.IO.Path]::GetFileName($path))"
    }
}
$hashLines | Set-Content -LiteralPath $overallManifest -Encoding ASCII
$md5Lines = foreach ($path in @((Join-Path $output 'submission.pdf'), $zip)) {
    if (Test-Path -LiteralPath $path) {
        "$((Get-FileHash -LiteralPath $path -Algorithm MD5).Hash.ToLowerInvariant())  $([System.IO.Path]::GetFileName($path))"
    }
}
$md5Lines | Set-Content -LiteralPath $overallMd5Manifest -Encoding ASCII

& (Join-Path $PSScriptRoot 'audit_submission.ps1') -EnvironmentName $selected.Prefix -Strict -ProjectRoot $root -WorkspaceRoot $sharedRoot
if ($LASTEXITCODE -ne 0) { throw 'Submission audit failed; package is not ready.' }
$zipBytes = (Get-Item -LiteralPath $zip).Length
Write-Host "Supporting archive: $zip ($zipBytes bytes; compressor=WinRAR)"
