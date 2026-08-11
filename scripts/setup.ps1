[CmdletBinding()]
param(
    [string]$EnvironmentName = 'auto',
    [ValidateSet('core','extended')][string]$Tier = 'core',
    [switch]$RetryClone
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
$root = Get-ModelingRoot
$conda = Get-CondaExecutable
$output = Join-Path $root 'output'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$setupReport = Join-Path $output "setup-$Tier.json"
$priorSetupReport = $null
if (Test-Path -LiteralPath $setupReport) {
    try { $priorSetupReport = Get-Content -LiteralPath $setupReport -Raw -Encoding UTF8 | ConvertFrom-Json }
    catch { $priorSetupReport = $null }
}
$attempts = [System.Collections.Generic.List[object]]::new()
$cleanupEvents = [System.Collections.Generic.List[object]]::new()
$transactionLock = $null
$basePrefix = [System.IO.Path]::GetFullPath((Split-Path (Split-Path $conda -Parent) -Parent)).TrimEnd('\')
$baseFingerprintBefore = $null
$baseFingerprintAfter = $null
$promotionCompleted = $false

function Get-TextSha256 {
    param([Parameter(Mandatory)][string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-CondaPrefixFingerprint {
    param([Parameter(Mandatory)][string]$Prefix)
    $result = Invoke-CondaCommand -Conda $conda -Arguments @('list', '-p', $Prefix, '--json') -CaptureOutput -TimeoutSeconds 600
    if ($result.ExitCode -ne 0) {
        throw "Could not fingerprint Conda prefix ${Prefix}: $(Format-CondaFailure -Result $result)"
    }
    return Get-TextSha256 -Text (($result.Output -join "`n").Trim())
}

function Format-CondaFailure {
    param([Parameter(Mandatory)]$Result)
    $errors = @($Result.ErrorOutput | Where-Object { $_ })
    $output = @($Result.Output | Where-Object { $_ })
    $diagnostic = @($errors + @($output | Where-Object { $_ -match '(?i)error|exception|failed|not found|clobber|verification' }))
    $lines = if ($diagnostic.Count -gt 0) { $diagnostic } else { $output }
    $tail = @($lines | Select-Object -Last 30 | ForEach-Object {
        ([string]$_ -replace '[\x00-\x08\x0B\x0C\x0E-\x1F]', '').Trim()
    } | Where-Object { $_ })
    $detail = if ($tail.Count -gt 0) { $tail -join ' | ' } else { 'no diagnostic output' }
    return "exit=$($Result.ExitCode); $detail"
}

function Update-BaseFingerprint {
    try { $script:baseFingerprintAfter = Get-CondaPrefixFingerprint -Prefix $basePrefix }
    catch { $cleanupEvents.Add([ordered]@{ action = 'fingerprint-base'; status = 'WARNING'; message = $_.Exception.Message }) }
}

function Assert-BaseUnmodified {
    if (-not $baseFingerprintBefore -or -not $baseFingerprintAfter) {
        throw 'Base integrity could not be verified before and after the setup transaction.'
    }
    if ($baseFingerprintBefore -ne $baseFingerprintAfter) {
        throw 'The base Conda package fingerprint changed during setup.'
    }
}

function Write-BaseEnvironmentAudit {
    $auditPath = Join-Path $output 'environment-base.json'
    $previousName = $env:MATHMODEL_SELECTED_ENV
    $previousPrefix = $env:MATHMODEL_SELECTED_PREFIX
    try {
        $env:MATHMODEL_SELECTED_ENV = 'base'
        $env:MATHMODEL_SELECTED_PREFIX = $basePrefix
        $audit = Invoke-CondaCommand -Conda $conda -Arguments @(
            'run', '--no-capture-output', '-p', $basePrefix, 'python', '-s',
            (Join-Path $root 'src\utils\verify_env.py'), '--tier', 'core',
            '--requirements', (Join-Path $root 'config\environment_requirements.json'),
            '--allow-missing', '--json', $auditPath
        ) -CaptureOutput -TimeoutSeconds 1200
        if ($audit.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $auditPath)) {
            throw "Base audit failed: $(Format-CondaFailure -Result $audit)"
        }
    } finally {
        $env:MATHMODEL_SELECTED_ENV = $previousName
        $env:MATHMODEL_SELECTED_PREFIX = $previousPrefix
    }
}

function Write-SetupReport {
    param([string]$Status, [string]$Stage, [string]$Message, [string]$Environment = '')
    $baseModified = $null
    if ($baseFingerprintBefore -and $baseFingerprintAfter) {
        $baseModified = $baseFingerprintBefore -ne $baseFingerprintAfter
        if ($baseModified -and $Status -eq 'PASS') {
            $Status = 'FAIL'
            $Stage = 'base-integrity'
            $Message = 'The base Conda package fingerprint changed during setup; the transaction is not accepted.'
        }
    }
    $pythonVersion = ''
    if ($Environment) {
        try {
            $environmentPrefix = $Environment
            if ($Environment -notmatch '^[A-Za-z]:[\\/]') {
                $environmentPrefix = Get-DefaultEnvironmentPrefix -Name $Environment
            }
            $versionProbe = Invoke-CondaCommand -Conda $conda -Arguments @('run', '--no-capture-output', '-p', $environmentPrefix, 'python', '-E', '-s', '-c', 'import sys; print(sys.version.split()[0])') -CaptureOutput -TimeoutSeconds 120
            if ($versionProbe.ExitCode -eq 0) { $pythonVersion = (@($versionProbe.Output | Where-Object { $_ }) | Select-Object -Last 1).Trim() }
        } catch {
            $cleanupEvents.Add([ordered]@{ action = 'report-python-version'; status = 'WARNING'; message = $_.Exception.Message })
        }
    }
    $pythonPolicy = if ($Tier -eq 'extended' -and $Stage -eq 'reuse-existing') { 'existing-verified-prefix' } elseif ($Tier -eq 'extended') { 'clean-local-python-3.13' } else { 'compatible-core' }
    $payload = [ordered]@{
        schema_version = 3
        tier = $Tier
        status = $Status
        stage = $Stage
        message = $Message
        environment = $Environment
        promotion_completed = $promotionCompleted
        python_policy = $pythonPolicy
        python_version = $pythonVersion
        user_site_policy = if ($Tier -eq 'extended') { 'target-prefix-only; user-site disabled' } else { 'external-local allowed with provenance warning' }
        conda_serialization = [ordered]@{
            mutex = Get-CondaMutexName -Conda $conda
            transaction_scope = $true
            per_process_temp = $true
        }
        base = [ordered]@{
            prefix = $basePrefix
            fingerprint_before = $baseFingerprintBefore
            fingerprint_after = $baseFingerprintAfter
            modified = $baseModified
        }
        attempts = @($attempts)
        cleanup = @($cleanupEvents)
    }
    [System.IO.File]::WriteAllText($setupReport, ($payload | ConvertTo-Json -Depth 10), [System.Text.UTF8Encoding]::new($false))
}

function Add-Attempt {
    param(
        [string]$Python,
        [string]$Strategy,
        [string]$Status,
        [string]$Message,
        [string[]]$Packages = @()
    )
    $attempts.Add([ordered]@{
        python = $Python
        strategy = $Strategy
        status = $Status
        message = $Message
        packages = @($Packages)
    })
}

function Get-DefaultEnvironmentPrefix {
    param([Parameter(Mandatory)][string]$Name)
    if ($Name -notmatch '^math-modeling(?:-build-\d+|-backup-\d{8}-\d{6})?$') {
        throw "Refusing to resolve an unmanaged environment name: $Name"
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Join-Path $basePrefix 'envs') $Name))
}

function Remove-BuildEnvironment {
    param([Parameter(Mandatory)][string]$Name)
    $registered = @(Get-CondaEnvironments -Conda $conda | Where-Object { $_.Name -eq $Name })
    if ($registered.Count -gt 1) {
        $event = [ordered]@{ action = 'remove-environment'; environment = $Name; status = 'FAIL'; message = 'Environment name is ambiguous.' }
        $cleanupEvents.Add($event)
        return $event
    }
    if ($registered.Count -eq 1) {
        $remove = Invoke-CondaCommand -Conda $conda -Arguments @('env', 'remove', '-p', $registered[0].Prefix, '--yes') -CaptureOutput -TimeoutSeconds 3600
        $status = if ($remove.ExitCode -eq 0) { 'PASS' } else { 'FAIL' }
        $message = if ($remove.ExitCode -eq 0) { 'Registered environment removed by Conda.' } else { Format-CondaFailure -Result $remove }
        $event = [ordered]@{ action = 'remove-environment'; environment = $Name; prefix = $registered[0].Prefix; status = $status; message = $message }
        $cleanupEvents.Add($event)
        return $event
    }

    $candidate = Get-DefaultEnvironmentPrefix -Name $Name
    $envRoot = [System.IO.Path]::GetFullPath((Join-Path $basePrefix 'envs')).TrimEnd('\')
    if ((Split-Path -Parent $candidate).TrimEnd('\') -ne $envRoot -or (Split-Path -Leaf $candidate) -ne $Name) {
        throw "Refusing unsafe orphan cleanup target: $candidate"
    }
    if (Test-Path -LiteralPath $candidate) {
        Remove-Item -LiteralPath $candidate -Recurse -Force
        $event = [ordered]@{ action = 'remove-orphan'; environment = $Name; prefix = $candidate; status = 'PASS'; message = 'Unregistered partial environment directory removed.' }
    } else {
        $event = [ordered]@{ action = 'remove-environment'; environment = $Name; prefix = $candidate; status = 'NOT_FOUND'; message = 'No registered environment or partial directory remained.' }
    }
    $cleanupEvents.Add($event)
    return $event
}

function Invoke-PrefixPythonCommand {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string[]]$Arguments,
        [int]$TimeoutSeconds = 1800
    )
    $match = @(Get-CondaEnvironments -Conda $conda | Where-Object { $_.Name -eq $Name })
    if ($match.Count -ne 1) { throw "Cannot resolve one Conda prefix for Python command: $Name" }
    $python = Join-Path $match[0].Prefix 'python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw "Python executable is missing from $($match[0].Prefix)." }
    $temporaryDirectory = New-CondaTemporaryDirectory
    $process = $null
    $previous = @{}
    $restored = $false
    try {
        $quote = {
            param([string]$Value)
            if ($Value -notmatch '[\s"]') { return $Value }
            return '"' + ([regex]::Replace($Value, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
        }
        foreach ($entry in ([ordered]@{
            PYTHONNOUSERSITE = '1'; TEMP = $temporaryDirectory.Path; TMP = $temporaryDirectory.Path
        }).GetEnumerator()) {
            $previous[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, 'Process')
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
        }
        $start = [System.Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $python
        $start.Arguments = (@(@('-E') + @($Arguments) | ForEach-Object { & $quote ([string]$_) }) -join ' ')
        $start.WorkingDirectory = $root
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $start.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $start.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        $process = [System.Diagnostics.Process]::new()
        $process.StartInfo = $start
        if (-not $process.Start()) { throw "Unable to start prefix Python: $python" }
        foreach ($entry in $previous.GetEnumerator()) { [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process') }
        $restored = $true
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            try { Stop-ExactProcessTree -Process $process } catch { try { $process.Kill() } catch { } }
            throw "Prefix Python command timed out after $TimeoutSeconds seconds: $($Arguments -join ' ')"
        }
        return [pscustomobject]@{
            Output = @($stdoutTask.Result -split '\r?\n' | Where-Object { $_ })
            ErrorOutput = @($stderrTask.Result -split '\r?\n' | Where-Object { $_ })
            ExitCode = $process.ExitCode
        }
    } finally {
        if (-not $restored) {
            foreach ($entry in $previous.GetEnumerator()) { [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process') }
        }
        if ($process) { $process.Dispose() }
        [void](Remove-CondaTemporaryDirectory -TemporaryDirectory $temporaryDirectory)
    }
}

function Install-ExtendedPipPackages {
    param([string]$Name, [object[]]$Items)
    $packages = @($Items | Where-Object { $_.installer -eq 'pip' } | ForEach-Object { [string]$_.pip })
    if ($packages.Count -eq 0) { return }
    $result = Invoke-PrefixPythonCommand -Name $Name -Arguments (@('-s', '-m', 'pip', 'install', '--disable-pip-version-check') + $packages) -TimeoutSeconds 600
    if ($result.ExitCode -ne 0) { throw "Pip extension installation failed: $(Format-CondaFailure -Result $result)" }
}

function Install-PipPackages {
    param(
        [string]$Name,
        [string[]]$Packages,
        [string]$IndexUrl = 'https://pypi.tuna.tsinghua.edu.cn/simple'
    )
    if ($Packages.Count -eq 0) { return }
    $batchSize = 3
    for ($offset = 0; $offset -lt $Packages.Count; $offset += $batchSize) {
        $last = [Math]::Min($offset + $batchSize - 1, $Packages.Count - 1)
        $batch = @($Packages[$offset..$last])
        $result = Invoke-PrefixPythonCommand -Name $Name -Arguments (@(
            '-s', '-m', 'pip', 'install', '--disable-pip-version-check',
            '--index-url', $IndexUrl, '--only-binary', ':all:',
            '--timeout', '60', '--retries', '3', '--progress-bar', 'off'
        ) + $batch) -TimeoutSeconds 2400
        if ($result.ExitCode -ne 0) {
            throw "Pip package batch failed [$($batch -join ', ')]: $(Format-CondaFailure -Result $result)"
        }
    }
}

function Test-ExtendedCandidate {
    param([string]$Name, [ValidateSet('3.13')][string]$ExpectedPython)
    $smokePath = Join-Path $output "extended-smoke-$Name.json"
    $smoke = Invoke-PrefixPythonCommand -Name $Name -Arguments @(
        '-s',
        (Join-Path $root 'src\utils\smoke_extended.py'),
        '--output', $smokePath,
        '--expected-python', $ExpectedPython
    ) -TimeoutSeconds 600
    if ($smoke.ExitCode -ne 0) { throw "Extended smoke test failed: $(Format-CondaFailure -Result $smoke)" }
    if (-not (Test-Path -LiteralPath $smokePath)) { throw "Extended smoke test did not write its report: $smokePath" }
    $smokeReport = Get-Content -LiteralPath $smokePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($smokeReport.status -ne 'PASS') {
        $failed = @($smokeReport.checks | Where-Object { -not $_.passed } | ForEach-Object { "$($_.name): $($_.error)" })
        throw "Extended smoke test reported FAIL: $($failed -join ' | ')"
    }
}

function Build-ClonedCandidate {
    param([Parameter(Mandatory)]$Source, [Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)]$Requirements)
    $clone = Invoke-CondaCommand -Conda $conda -Arguments @('create', '-n', $Name, '--clone', $Source.Prefix, '--yes') -CaptureOutput -TimeoutSeconds 7200
    if ($clone.ExitCode -ne 0) { throw "Environment clone failed: $(Format-CondaFailure -Result $clone)" }

    $coreMissing = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $sourceCoreMissing = if ($Source.PSObject.Properties.Name -contains 'CorePrefixMissing') { $Source.CorePrefixMissing } else { $Source.CoreMissing }
    foreach ($item in @($sourceCoreMissing)) { [void]$coreMissing.Add([string]$item) }
    $extendedMissing = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($item in @($Source.ExtendedMissing)) { [void]$extendedMissing.Add([string]$item) }
    $neededCore = @($Requirements.core.python | Where-Object { $coreMissing.Contains([string]$_.import) })
    $neededExtended = @($Requirements.extended.python | Where-Object { $extendedMissing.Contains([string]$_.import) })
    $needed = @($neededCore) + @($neededExtended)
    $condaPackages = @($needed | Where-Object { -not $_.installer -or $_.installer -eq 'conda' } | ForEach-Object { [string]$_.conda })
    if ($condaPackages.Count -gt 0) {
        $install = Invoke-CondaCommand -Conda $conda -Arguments (@('install', '-n', $Name, '--yes', '--override-channels', '-c', 'conda-forge', 'python=3.13.*') + $condaPackages) -CaptureOutput -TimeoutSeconds 10800
        if ($install.ExitCode -ne 0) { throw "Conda Python 3.13 extension installation failed: $(Format-CondaFailure -Result $install)" }
    }
    Install-ExtendedPipPackages -Name $Name -Items $neededExtended
    Test-ExtendedCandidate -Name $Name -ExpectedPython '3.13'
    return @($needed | ForEach-Object { [string]$_.import })
}

function Build-CleanPython313Candidate {
    param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)]$Requirements)
    $create = $null
    try {
        $create = Invoke-CondaCommand -Conda $conda -Arguments @('create', '-n', $Name, '--yes', 'python=3.13.*', 'pip') -CaptureOutput -TimeoutSeconds 1200
    } catch {
        $candidatePrefix = Get-DefaultEnvironmentPrefix -Name $Name
        $pythonReady = Test-Path -LiteralPath (Join-Path $candidatePrefix 'python.exe')
        $historyReady = Test-Path -LiteralPath (Join-Path $candidatePrefix 'conda-meta\history')
        if ($_.Exception.Message -match 'timed out' -and $pythonReady -and $historyReady) {
            $cleanupEvents.Add([ordered]@{
                action = 'recover-conda-create-timeout'; environment = $Name; prefix = $candidatePrefix
                status = 'WARNING'; message = 'Conda stopped returning after writing a complete minimal prefix; the exact process tree was terminated and the prefix will be validated before promotion.'
            })
        } else {
            throw
        }
    }
    if ($create -and $create.ExitCode -ne 0) { throw "Clean local Python 3.13 environment creation failed: $(Format-CondaFailure -Result $create)" }
    $pipNames = [ordered]@{
        numpy = 'numpy'; scipy = 'scipy'; pandas = 'pandas'; sympy = 'sympy'
        statsmodels = 'statsmodels'; sklearn = 'scikit-learn'; matplotlib = 'matplotlib'
        seaborn = 'seaborn'; plotly = 'plotly'; networkx = 'networkx'; openpyxl = 'openpyxl'
        yaml = 'PyYAML'; PIL = 'Pillow'; pypdf = 'pypdf'; pytest = 'pytest'
        ortools = 'ortools'; pulp = 'PuLP'; cvxpy = 'cvxpy'; pyomo = 'pyomo'
        highspy = 'highspy'; cv2 = 'opencv-python-headless'; fitz = 'PyMuPDF'
        pdfplumber = 'pdfplumber'; SALib = 'SALib'; deap = 'deap'; simpy = 'simpy'
        rapidocr_onnxruntime = 'rapidocr-onnxruntime'; schemdraw = 'schemdraw'; pyswarms = 'pyswarms'
    }
    $imports = @($Requirements.core.python.import) + @($Requirements.extended.python.import)
    $packages = @($imports | ForEach-Object {
        if (-not $pipNames.Contains([string]$_)) { throw "No pip fallback mapping exists for import: $_" }
        [string]$pipNames[[string]$_]
    })
    # Install NumPy first so compiled dependants resolve against a verified wheel.
    Install-PipPackages -Name $Name -Packages @('numpy')
    $numpyProbe = Invoke-PrefixPythonCommand -Name $Name -Arguments @('-s', '-c', 'import numpy; print(numpy.__version__); print(numpy.__file__)') -TimeoutSeconds 300
    if ($numpyProbe.ExitCode -ne 0) { throw "NumPy foundation import failed: $(Format-CondaFailure -Result $numpyProbe)" }
    $remaining = @($packages | Where-Object { $_ -ne 'numpy' })
    Install-PipPackages -Name $Name -Packages $remaining
    # Verify the PDF dependency explicitly; it must live in the target prefix.
    Install-PipPackages -Name $Name -Packages @('pypdf')
    $pdfProbe = Invoke-PrefixPythonCommand -Name $Name -Arguments @('-s', '-c', 'import pypdf; print(pypdf.__file__)') -TimeoutSeconds 300
    if ($pdfProbe.ExitCode -ne 0) { throw "PyPDF foundation import failed: $(Format-CondaFailure -Result $pdfProbe)" }
    Test-ExtendedCandidate -Name $Name -ExpectedPython '3.13'
    return $imports
}

$baseFingerprintBefore = Get-CondaPrefixFingerprint -Prefix $basePrefix
Write-BaseEnvironmentAudit

if ($Tier -eq 'core') {
    $resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
    if ($resolved.Selected.CoreMissing.Count -eq 0) {
        & (Join-Path $PSScriptRoot 'verify_env.ps1') -EnvironmentName $resolved.Selected.Prefix -Tier core -NoAggregateReport
        $reuseExit = $LASTEXITCODE
        if ($reuseExit -eq 0) {
            Update-BaseFingerprint
            Assert-BaseUnmodified
            $promotionCompleted = $true
            Write-SetupReport -Status 'PASS' -Stage 'reuse-existing' -Message 'Existing core environment passed verification; no environment was modified.' -Environment $resolved.Selected.Prefix
            exit 0
        }
        Add-Attempt -Python $resolved.Selected.Python -Strategy "reuse:$($resolved.Selected.Prefix)" -Status 'FAIL' -Message "Existing environment failed core verification with exit code $reuseExit; creating an independent fallback."
    }
    $targetName = 'math-modeling'
    try {
        $transactionLock = Enter-CondaLock -Conda $conda -TimeoutSeconds 10800
        $existing = @(Get-CondaEnvironments -Conda $conda | Where-Object { $_.Name -eq $targetName })
        if ($existing.Count -eq 0) {
            $result = Invoke-CondaCommand -Conda $conda -Arguments @('env', 'create', '-n', $targetName, '-f', (Join-Path $root 'environment.yml'), '--yes') -CaptureOutput -TimeoutSeconds 10800
        } else {
            $result = Invoke-CondaCommand -Conda $conda -Arguments @('env', 'update', '-p', $existing[0].Prefix, '-f', (Join-Path $root 'environment.yml')) -CaptureOutput -TimeoutSeconds 10800
        }
        if ($result.ExitCode -ne 0) { throw "Core fallback creation failed: $(Format-CondaFailure -Result $result)" }
        & (Join-Path $PSScriptRoot 'verify_env.ps1') -EnvironmentName $targetName -Tier core -NoAggregateReport
        $verifyExit = $LASTEXITCODE
        if ($verifyExit -ne 0) { throw "Core fallback verification exited with $verifyExit." }
        Update-BaseFingerprint
        Assert-BaseUnmodified
        Write-SetupReport -Status 'PASS' -Stage 'core-verify' -Message 'Independent core fallback passed verification.' -Environment $targetName
        exit 0
    } catch {
        Update-BaseFingerprint
        Write-SetupReport -Status 'FAIL' -Stage 'core-fallback' -Message $_.Exception.Message -Environment $targetName
        throw
    } finally {
        if ($transactionLock) { Exit-CondaLock -Lock $transactionLock }
    }
}

$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier full
if ($resolved.Selected.Python -match '^3\.13\.' -and $resolved.Selected.ExtendedMissing.Count -eq 0 -and $resolved.Selected.CoreMissing.Count -eq 0) {
    & (Join-Path $PSScriptRoot 'verify_env.ps1') -EnvironmentName $resolved.Selected.Prefix -Tier full -NoAggregateReport
    $reuseExit = $LASTEXITCODE
    if ($reuseExit -eq 0) {
        Update-BaseFingerprint
        Assert-BaseUnmodified
        $promotionCompleted = $true
        Write-SetupReport -Status 'PASS' -Stage 'reuse-existing' -Message 'An existing full environment passed verification; no environment was modified.' -Environment $resolved.Selected.Prefix
        exit 0
    }
    Add-Attempt -Python $resolved.Selected.Python -Strategy "reuse:$($resolved.Selected.Prefix)" -Status 'FAIL' -Message "Existing environment failed full verification with exit code $reuseExit; rebuilding transactionally."
}

$sourceResolution = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$source = $sourceResolution.Selected
$requirements = $sourceResolution.Requirements
$targetName = 'math-modeling'
$tempName = "math-modeling-build-$PID"
$backupName = "math-modeling-backup-$(Get-Date -Format yyyyMMdd-HHmmss)"
$promoted = $false
$backupCreated = $false
$success = $false
$directTargetBuild = $false
try {
    $transactionLock = Enter-CondaLock -Conda $conda -TimeoutSeconds 10800
    $existingTarget = @(Get-CondaEnvironments -Conda $conda | Where-Object { $_.Name -eq $targetName })
    $directTargetBuild = $existingTarget.Count -eq 0
    $buildName = if ($directTargetBuild) { $targetName } else { $tempName }
    $preclean = Remove-BuildEnvironment -Name $buildName
    if ($preclean.status -eq 'FAIL') { throw 'Could not establish a clean build environment prefix.' }
    $cloneFailure = $null
    if (-not $RetryClone) {
        $cloneFailure = 'The full Anaconda clone is skipped by default because local Qt/PySide packages have conflicting shared paths; building a clean environment with the installed Python 3.13 instead.'
        Add-Attempt -Python '3.13' -Strategy "clone:$($source.Prefix)" -Status 'SKIPPED' -Message $cloneFailure
    } else {
        try {
            $installed = Build-ClonedCandidate -Source $source -Name $buildName -Requirements $requirements
            Add-Attempt -Python '3.13' -Strategy "clone:$($source.Prefix)" -Status 'PASS' -Message 'Clone, missing-package install, and smoke tests passed.' -Packages $installed
        } catch {
            $cloneFailure = $_.Exception.Message
            Add-Attempt -Python '3.13' -Strategy "clone:$($source.Prefix)" -Status 'FAIL' -Message $cloneFailure
        }
    }
    if ($cloneFailure) {
        Write-Warning "Full Python 3.13 clone is unavailable; building a clean environment with the installed Python 3.13: $cloneFailure"
        $removed = Remove-BuildEnvironment -Name $buildName
        if ($removed.status -eq 'FAIL') { throw 'Python 3.13 clone cleanup failed; refusing an unclean Python 3.13 build.' }
        try {
            $installed = Build-CleanPython313Candidate -Name $buildName -Requirements $requirements
            Add-Attempt -Python '3.13' -Strategy 'clean-local-python' -Status 'PASS' -Message 'Independent local Python 3.13 environment and smoke tests passed.' -Packages $installed
        } catch {
            Add-Attempt -Python '3.13' -Strategy 'clean-local-python' -Status 'FAIL' -Message $_.Exception.Message
            throw
        }
    }

    if ($directTargetBuild) {
        $promoted = $true
    } elseif ($existingTarget.Count -gt 0) {
        $backup = Invoke-CondaCommand -Conda $conda -Arguments @('rename', '-p', $existingTarget[0].Prefix, $backupName, '--yes') -CaptureOutput -TimeoutSeconds 3600
        if ($backup.ExitCode -ne 0) { throw "Could not preserve the existing math-modeling environment: $(Format-CondaFailure -Result $backup)" }
        $backupCreated = $true
    }
    if (-not $directTargetBuild) {
        $promote = Invoke-CondaCommand -Conda $conda -Arguments @('rename', '-n', $tempName, $targetName, '--yes') -CaptureOutput -TimeoutSeconds 3600
        if ($promote.ExitCode -ne 0) { throw "Could not promote the verified extended environment: $(Format-CondaFailure -Result $promote)" }
        $promoted = $true
    }

    & (Join-Path $PSScriptRoot 'verify_env.ps1') -EnvironmentName $targetName -Tier full -NoAggregateReport
    $verifyExit = $LASTEXITCODE
    if ($verifyExit -ne 0) { throw 'Promoted environment failed full prefix-only verification.' }
    $success = $true
    $promotionCompleted = $true
    if ($backupCreated) {
        $oldCleanup = Remove-BuildEnvironment -Name $backupName
        if ($oldCleanup.status -eq 'FAIL') {
            $cleanupEvents.Add([ordered]@{ action = 'backup-retained'; environment = $backupName; status = 'WARNING'; message = 'Verified target is active, but the old backup could not be removed.' })
        } else {
            $backupCreated = $false
        }
    }
    Update-BaseFingerprint
    Assert-BaseUnmodified
    $chosenPython = @($attempts | Where-Object { $_.status -eq 'PASS' } | Select-Object -Last 1).python
    Write-SetupReport -Status 'PASS' -Stage 'promoted' -Message "Extended environment passed smoke and full verification with Python $chosenPython." -Environment $targetName
} catch {
    $failure = $_.Exception.Message
    if (($promoted -or $directTargetBuild) -and -not $success) {
        $targetCleanup = Remove-BuildEnvironment -Name $targetName
        if ($targetCleanup.status -ne 'FAIL') { $promoted = $false }
    }
    if ($backupCreated) {
        $restore = Invoke-CondaCommand -Conda $conda -Arguments @('rename', '-n', $backupName, $targetName, '--yes') -CaptureOutput -TimeoutSeconds 3600
        if ($restore.ExitCode -eq 0) {
            $cleanupEvents.Add([ordered]@{ action = 'restore-backup'; environment = $targetName; status = 'PASS'; message = 'Previous math-modeling environment restored.' })
            $backupCreated = $false
        } else {
            $cleanupEvents.Add([ordered]@{ action = 'restore-backup'; environment = $targetName; status = 'FAIL'; message = Format-CondaFailure -Result $restore })
        }
    }
    $tempCleanup = Remove-BuildEnvironment -Name $tempName
    Update-BaseFingerprint
    Write-SetupReport -Status 'FAIL' -Stage 'extended-build' -Message $failure -Environment $tempName
    throw
} finally {
    if ($transactionLock) { Exit-CondaLock -Lock $transactionLock }
}
Write-Host "Extended environment ready: $targetName"
