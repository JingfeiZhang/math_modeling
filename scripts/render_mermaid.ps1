[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$InputFile,

    [Parameter(Mandatory = $true)]
    [string]$OutputFile
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$mmdc = Join-Path $projectRoot 'tools\cli\mermaid\node_modules\@mermaid-js\mermaid-cli\src\cli.js'
$puppeteerConfig = Join-Path $projectRoot 'tools\cli\mermaid\puppeteer.edge.json'

if (-not (Test-Path -LiteralPath $mmdc)) {
    throw "Mermaid CLI is not installed: $mmdc"
}
if (-not (Test-Path -LiteralPath $puppeteerConfig)) {
    throw "Puppeteer configuration is missing: $puppeteerConfig"
}
$resolvedInput = (Resolve-Path -LiteralPath $InputFile).Path
$resolvedOutput = if ([System.IO.Path]::IsPathRooted($OutputFile)) {
    [System.IO.Path]::GetFullPath($OutputFile)
} else {
    [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputFile))
}
$outputDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

& node $mmdc -p $puppeteerConfig -i $resolvedInput -o $resolvedOutput
if ($LASTEXITCODE -ne 0) {
    throw "Mermaid CLI failed with exit code $LASTEXITCODE."
}
Write-Host "Mermaid figure written to $resolvedOutput"
