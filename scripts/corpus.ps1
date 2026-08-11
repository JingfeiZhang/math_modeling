[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('sync','card','dedupe','scan-matlab','audit-program','report')]
    [string]$Action,
    [string]$Source = 'all',
    [string]$Input,
    [string]$Output,
    [string]$TreeFixture,
    [string]$MatlabRoot,
    [string]$TreeManifest,
    [switch]$DownloadSmall,
    [int]$MaxBlobBytes = 1000000,
    [switch]$RequireDeepRead,
    [string]$EnvironmentName = 'auto'
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$root = Get-ModelingRoot
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$selected = $resolved.Selected
if ($selected.CoreMissing.Count -gt 0) {
    throw "Selected environment lacks core packages: $($selected.CoreMissing -join ', ')"
}

function Invoke-CorpusPython {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $python = @('run','--no-capture-output','-p',$selected.Prefix,'python','-m','src.corpus.miner')
    $run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments ($python + $Arguments)
    if ($run.ExitCode -ne 0) { throw "Corpus action failed: $($Arguments -join ' ')" }
}

function Invoke-WorkspacePython {
    param([Parameter(Mandatory)][string]$Script)
    $run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run','--no-capture-output','-p',$selected.Prefix,'python',$Script
    )
    if ($run.ExitCode -ne 0) { throw "Workspace Python script failed: $Script" }
}

Push-Location $root
try {
    switch ($Action) {
        'sync' {
            $arguments = @('sync','--config','config/corpus_sources.yaml','--source',$Source,'--output',$(if ($Output) { $Output } else { 'corpus/upstream' }),'--max-blob-bytes',[string]$MaxBlobBytes)
            if ($TreeFixture) { $arguments += @('--tree-fixture',(Resolve-Path -LiteralPath $TreeFixture).Path) }
            if ($DownloadSmall) { $arguments += '--download-small' }
            Invoke-CorpusPython $arguments
        }
        'card' {
            if (-not $Input -or -not $Output) { throw 'card requires -Input and -Output.' }
            $arguments = @('card','--input',(Resolve-Path -LiteralPath $Input).Path,'--output',$Output)
            if ($RequireDeepRead) { $arguments += '--require-deep-read' }
            Invoke-CorpusPython $arguments
        }
        'dedupe' {
            if (-not $Input -or -not $Output) { throw 'dedupe requires -Input and -Output.' }
            Invoke-CorpusPython @('dedupe','--input',(Resolve-Path -LiteralPath $Input).Path,'--output',$Output)
        }
        'scan-matlab' {
            if (-not $Output) { throw 'scan-matlab requires -Output.' }
            if ([bool]$MatlabRoot -eq [bool]$TreeManifest) { throw 'scan-matlab requires exactly one of -MatlabRoot or -TreeManifest.' }
            $arguments = @('scan-matlab','--output',$Output)
            if ($MatlabRoot) { $arguments += @('--root',(Resolve-Path -LiteralPath $MatlabRoot).Path) }
            if ($TreeManifest) { $arguments += @('--tree-manifest',(Resolve-Path -LiteralPath $TreeManifest).Path) }
            Invoke-CorpusPython $arguments
        }
        'report' {
            Invoke-WorkspacePython 'scripts/audit_corpus_program.py'
            Invoke-WorkspacePython 'scripts/build_experience_report.py'
            $pandoc = Get-Command pandoc -ErrorAction SilentlyContinue
            if (-not $pandoc) { throw 'pandoc is required to build corpus/experience_report.pdf.' }
            & $pandoc.Source 'corpus/experience_report.md' '--from=gfm' '--pdf-engine=xelatex' `
                '-V' 'CJKmainfont=Microsoft YaHei' '-V' 'geometry:margin=2.5cm' `
                '-V' 'fontsize=11pt' '-o' 'corpus/experience_report.pdf'
            if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath 'corpus/experience_report.pdf')) {
                throw 'Pandoc/XeLaTeX experience report build failed.'
            }
            Write-Output '{"status":"PASS","markdown":"corpus/experience_report.md","pdf":"corpus/experience_report.pdf"}'
        }
        'audit-program' {
            Invoke-WorkspacePython 'scripts/audit_corpus_program.py'
        }
    }
}
finally {
    Pop-Location
}
