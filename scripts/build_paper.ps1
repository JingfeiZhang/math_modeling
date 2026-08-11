[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [string]$ProjectRoot,
    [string]$WorkspaceRoot,
    [string]$OutputPdf,
    [string]$RenderDir,
    [ValidatePattern('^(frontmatter|full|Q[1-9][0-9]*)$')]
    [string]$PreviewCheckpoint
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$hub = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$root = if ($ProjectRoot) { [System.IO.Path]::GetFullPath($ProjectRoot) } else { $hub }
$sharedRoot = if ($WorkspaceRoot) { [System.IO.Path]::GetFullPath($WorkspaceRoot) } else { $hub }
$paperDir = Join-Path $root 'paper'
$outputDir = Join-Path $root 'output'
$temporaryBuildRoot = $null
$buildPaperDir = $paperDir

function Set-PreviewQuestionStructure {
    param(
        [Parameter(Mandatory)][string]$TemporaryPaperDir,
        [Parameter(Mandatory)][string]$Checkpoint
    )
    if ($Checkpoint -eq 'full') { return }
    $generatedDir = Join-Path $TemporaryPaperDir 'generated'
    New-Item -ItemType Directory -Force -Path $generatedDir | Out-Null
    $structurePath = Join-Path $generatedDir 'question_structure.tex'
    $lines = [System.Collections.Generic.List[string]]::new()
    if ($Checkpoint -match '^Q([1-9][0-9]*)$') {
        $questionCount = [int]$Matches[1]
        foreach ($number in 1..$questionCount) {
            $section = Join-Path $TemporaryPaperDir "sections\question_$number.tex"
            if (-not (Test-Path -LiteralPath $section -PathType Leaf)) {
                throw "Preview checkpoint $Checkpoint requires missing section: $section"
            }
            $lines.Add("\input{sections/question_$number.tex}")
        }
    }
    $lines.Add('\end{document}')
    $lines | Set-Content -LiteralPath $structurePath -Encoding UTF8
}

function Remove-TemporaryPreviewRoot {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return }
    $resolvedPath = [System.IO.Path]::GetFullPath($Path)
    $temporaryBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $resolvedPath.StartsWith($temporaryBase, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove preview directory outside the system temporary root: $resolvedPath"
    }
    Remove-Item -LiteralPath $resolvedPath -Recurse -Force
}

if (-not (Test-Path -LiteralPath (Join-Path $paperDir 'main.tex') -PathType Leaf)) {
    throw "Paper entrypoint is missing: $(Join-Path $paperDir 'main.tex')"
}

if ($PreviewCheckpoint) {
    $temporaryBuildRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("mathmodel-paper-preview-" + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporaryBuildRoot | Out-Null
    try {
        Copy-Item -LiteralPath $paperDir -Destination $temporaryBuildRoot -Recurse -Force
        $buildPaperDir = Join-Path $temporaryBuildRoot 'paper'
        if ($PreviewCheckpoint -ne 'full') {
            $temporaryMain = Get-Content -LiteralPath (Join-Path $buildPaperDir 'main.tex') -Raw -Encoding UTF8
            if ($temporaryMain -notmatch 'generated/question_structure\.tex') {
                throw 'Incremental preview requires main.tex to input generated/question_structure.tex.'
            }
        }
        Set-PreviewQuestionStructure -TemporaryPaperDir $buildPaperDir -Checkpoint $PreviewCheckpoint
    } catch {
        Remove-TemporaryPreviewRoot -Path $temporaryBuildRoot
        throw
    }
} else {
    $resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
    $selected = $resolved.Selected
    if ($selected.CoreMissing.Count -gt 0) { throw "Selected environment lacks core packages: $($selected.CoreMissing -join ', ')" }

    $statePath = Join-Path $root 'state\decision_log.json'
    if (Test-Path -LiteralPath $statePath) {
        $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $state.problem) { throw 'decision_log.json does not identify the active problem.' }
        $claimRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
            'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\workflow\render_frozen_claims.py'),
            '--root',$root,'--problem',[string]$state.problem
        )
        if ($claimRun.ExitCode -ne 0) { throw 'Frozen-claim rendering failed; paper build was stopped.' }

        $assetScript = Join-Path $root 'scripts\generate_paper_assets.py'
        if (Test-Path -LiteralPath $assetScript) {
            $assetRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
                'run','--no-capture-output','-p',$selected.Prefix,'python','-s',$assetScript
            )
            if ($assetRun.ExitCode -ne 0) { throw 'Paper metric rendering failed; paper build was stopped.' }
        }
    }

    $prepareRun = Invoke-CondaCommand -Conda $resolved.Conda -Arguments @(
        'run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $sharedRoot 'src\utils\prepare_paper_figures.py'),
        '--root',$root,'--manifest',(Join-Path $root 'paper\figure_contracts.yaml'),
        '--output',(Join-Path $root 'output\figure_collection.json')
    )
    if ($prepareRun.ExitCode -ne 0) { throw 'Figure Contract collection failed; paper build was stopped.' }
}

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
try {
    Push-Location $buildPaperDir
    try {
        & latexmk -xelatex -interaction=nonstopmode -halt-on-error -file-line-error main.tex
        if ($LASTEXITCODE -ne 0) { throw 'XeLaTeX compilation failed.' }
    } finally {
        Pop-Location
    }
    $pdf = Join-Path $buildPaperDir 'main.pdf'
    if (-not (Test-Path -LiteralPath $pdf)) { throw "LaTeX did not create $pdf" }
    $defaultPdf = if ($PreviewCheckpoint) { Join-Path $outputDir "_verification\previews\$PreviewCheckpoint.pdf" } else { Join-Path $outputDir 'submission.pdf' }
    $paperOutput = if ($OutputPdf) { [System.IO.Path]::GetFullPath($OutputPdf) } else { $defaultPdf }
    $paperOutputParent = Split-Path -Parent $paperOutput
    New-Item -ItemType Directory -Force -Path $paperOutputParent | Out-Null
    Copy-Item -LiteralPath $pdf -Destination $paperOutput -Force
    $defaultPages = if ($PreviewCheckpoint) { Join-Path $outputDir "_verification\previews\$PreviewCheckpoint-pages" } else { Join-Path $outputDir '_verification\pdf\rendered-pages' }
    $pageOutput = if ($RenderDir) { [System.IO.Path]::GetFullPath($RenderDir) } else { $defaultPages }
    New-Item -ItemType Directory -Force -Path $pageOutput | Out-Null
    $pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue
    if (-not $pdftoppm) { throw 'pdftoppm is required to render PDF pages.' }
    $pdftoppmExe = $pdftoppm.Source
    if ([System.IO.Path]::GetExtension($pdftoppmExe) -eq '.cmd') {
        $nativeCandidate = Join-Path (Split-Path $pdftoppmExe -Parent) '..\..\native\poppler\Library\bin\pdftoppm.exe'
        if (Test-Path -LiteralPath $nativeCandidate) { $pdftoppmExe = (Resolve-Path -LiteralPath $nativeCandidate).Path }
    }
    Get-ChildItem -LiteralPath $pageOutput -Filter 'page-*.png' -File -ErrorAction SilentlyContinue | Remove-Item -Force
    & $pdftoppmExe -png -r 144 $paperOutput (Join-Path $pageOutput 'page')
    if ($LASTEXITCODE -ne 0) { throw 'PDF page rendering failed.' }
    Write-Host "Paper PDF: $paperOutput"
} finally {
    Remove-TemporaryPreviewRoot -Path $temporaryBuildRoot
}
