param(
    [switch]$ProtocolOnly
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
$python = Join-Path $workspace ".tools\originlab-mcp-venv\Scripts\python.exe"
$testScript = Join-Path $PSScriptRoot "test_originlab_mcp.py"
$originExe = "D:\Origin_2025b\Origin64.exe"
$beforeIds = @(Get-Process -Name Origin64 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)

try {
    $arguments = @($testScript, "--workspace", $workspace)
    if ($ProtocolOnly) {
        $arguments += "--protocol-only"
    }
    & $python @arguments
    $testExitCode = $LASTEXITCODE
}
finally {
    if (-not $ProtocolOnly) {
        $newProcesses = @(Get-Process -Name Origin64 -ErrorAction SilentlyContinue | Where-Object {
            if ($beforeIds -contains $_.Id) {
                return $false
            }
            try {
                return (Get-Item -LiteralPath $_.Path).FullName -eq $originExe
            }
            catch {
                return $false
            }
        })
        foreach ($process in $newProcesses) {
            $null = $process.CloseMainWindow()
            if (-not $process.WaitForExit(5000)) {
                Stop-Process -Id $process.Id -Force
            }
        }
    }
}

exit $testExitCode
