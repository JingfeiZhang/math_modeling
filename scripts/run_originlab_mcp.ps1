param(
    [switch]$AttachExisting,
    [switch]$EnableAdvanced
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$python = Join-Path $workspace ".tools\originlab-mcp-venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "OriginLab MCP runtime not found: $python"
}

$env:PYTHONNOUSERSITE = "1"
$env:ORIGINLAB_MCP_ATTACH_EXISTING = if ($AttachExisting) { "1" } else { "0" }
$env:ORIGINLAB_MCP_ENABLE_ADVANCED = if ($EnableAdvanced) { "1" } else { "0" }

& $python -m originlab_mcp.server
exit $LASTEXITCODE
