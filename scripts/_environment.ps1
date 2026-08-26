Set-StrictMode -Version Latest

function Get-ModelingRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

function Get-RequirementManifest {
    $path = Join-Path (Get-ModelingRoot) 'config\environment_requirements.json'
    if (-not (Test-Path -LiteralPath $path)) { throw "Environment requirement manifest is missing: $path" }
    return Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Get-CondaExecutable {
    $command = Get-Command conda -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in @('D:\anaconda3\Scripts\conda.exe', 'D:\miniforge3\Scripts\conda.exe')) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw 'Conda was not found. Install or expose Conda before running this command.'
}

function Get-CondaMutexName {
    param([Parameter(Mandatory)][string]$Conda)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(([System.IO.Path]::GetFullPath($Conda)).ToLowerInvariant())
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $hash = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').Substring(0, 16) }
    finally { $sha.Dispose() }
    return "Local\MathModelingConda_$hash"
}

function Enter-CondaLock {
    param(
        [Parameter(Mandatory)][string]$Conda,
        [int]$TimeoutSeconds = 900,
        [switch]$Quiet
    )
    $name = Get-CondaMutexName -Conda $Conda
    $mutex = [System.Threading.Mutex]::new($false, $name)
    $started = [DateTimeOffset]::UtcNow
    try {
        try { $acquired = $mutex.WaitOne([TimeSpan]::FromSeconds($TimeoutSeconds)) }
        catch [System.Threading.AbandonedMutexException] {
            $acquired = $true
            Write-Warning "Recovered abandoned Conda lock: $name"
        }
        if (-not $acquired) {
            $mutex.Dispose()
            throw "Timed out after $TimeoutSeconds seconds waiting for Conda lock: $name"
        }
        $waited = [Math]::Round(([DateTimeOffset]::UtcNow - $started).TotalSeconds, 3)
        if ($waited -ge 0.5 -and -not $Quiet) { Write-Host "Conda lock acquired after ${waited}s: $name" }
        return [pscustomobject]@{ Mutex = $mutex; Name = $name; WaitSeconds = $waited; Released = $false }
    } catch {
        if ($mutex) { $mutex.Dispose() }
        throw
    }
}

function Exit-CondaLock {
    param([Parameter(Mandatory)]$Lock)
    if (-not $Lock.Released) {
        $Lock.Mutex.ReleaseMutex()
        $Lock.Mutex.Dispose()
        $Lock.Released = $true
    }
}

function New-CondaTemporaryDirectory {
    $tempRoot = Join-Path (Get-ModelingRoot) 'output\.conda-tmp'
    New-Item -ItemType Directory -Force -Path $tempRoot | Out-Null
    do {
        $leaf = "call-$PID-$([Guid]::NewGuid().ToString('N'))"
        $path = Join-Path $tempRoot $leaf
    } while (Test-Path -LiteralPath $path)
    New-Item -ItemType Directory -Path $path | Out-Null
    return [pscustomobject]@{
        Root = [System.IO.Path]::GetFullPath($tempRoot).TrimEnd('\')
        Path = [System.IO.Path]::GetFullPath($path).TrimEnd('\')
        Leaf = $leaf
    }
}

function Remove-CondaTemporaryDirectory {
    param([Parameter(Mandatory)]$TemporaryDirectory)
    $path = [System.IO.Path]::GetFullPath([string]$TemporaryDirectory.Path).TrimEnd('\')
    $root = [System.IO.Path]::GetFullPath([string]$TemporaryDirectory.Root).TrimEnd('\')
    if ((Split-Path -Parent $path).TrimEnd('\') -ne $root -or
        (Split-Path -Leaf $path) -notmatch '^call-\d+-[0-9a-f]{32}$') {
        throw "Refusing unsafe Conda TEMP cleanup target: $path"
    }
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
    return -not (Test-Path -LiteralPath $path)
}

function Stop-ExactProcessTree {
    param([Parameter(Mandatory)][System.Diagnostics.Process]$Process)
    if ($Process.HasExited) { return }
    $taskkill = Join-Path $env:SystemRoot 'System32\taskkill.exe'
    $stop = [System.Diagnostics.ProcessStartInfo]::new()
    $stop.FileName = $taskkill
    $stop.Arguments = "/PID $($Process.Id) /T /F"
    $stop.UseShellExecute = $false
    $stop.CreateNoWindow = $true
    $killer = [System.Diagnostics.Process]::Start($stop)
    try { [void]$killer.WaitForExit(30000) } finally { $killer.Dispose() }
    if (-not $Process.HasExited) { $Process.Kill() }
}

function Invoke-CondaCommand {
    param(
        [Parameter(Mandatory)][string]$Conda,
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$CaptureOutput,
        [switch]$DisableUserSite,
        [int]$TimeoutSeconds = 900
    )
    $lock = Enter-CondaLock -Conda $Conda -TimeoutSeconds $TimeoutSeconds -Quiet:$CaptureOutput
    $temporaryDirectory = $null
    $process = $null
    $commandResult = $null
    $tempCleaned = $false
    $tempCleanupError = $null
    $processEnvironment = @{}
    $processEnvironmentRestored = $false
    $commandFailure = $null
    try {
        $temporaryDirectory = New-CondaTemporaryDirectory
        $quote = {
            param([string]$Value)
            if ($Value -notmatch '[\s"]') { return $Value }
            return '"' + ([regex]::Replace($Value, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
        }
        $start = [System.Diagnostics.ProcessStartInfo]::new()
        $start.FileName = $Conda
        $start.Arguments = (@($Arguments | ForEach-Object { & $quote ([string]$_) }) -join ' ')
        $start.WorkingDirectory = Get-ModelingRoot
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $start.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        $start.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        # Windows PowerShell on this host does not expose a writable
        # ProcessStartInfo.EnvironmentVariables dictionary. Change the parent
        # process only for Process.Start; the child receives an isolated copy.
        $childEnvironment = [ordered]@{ TEMP = $temporaryDirectory.Path; TMP = $temporaryDirectory.Path }
        if ($DisableUserSite) { $childEnvironment['PYTHONNOUSERSITE'] = '1' }
        foreach ($entry in $childEnvironment.GetEnumerator()) {
            $processEnvironment[$entry.Key] = [Environment]::GetEnvironmentVariable($entry.Key, 'Process')
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
        }
        $process = [System.Diagnostics.Process]::new()
        $process.StartInfo = $start
        if (-not $process.Start()) { throw "Unable to start Conda: $Conda" }
        foreach ($entry in $processEnvironment.GetEnumerator()) {
            [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
        }
        $processEnvironmentRestored = $true
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutSeconds * 1000)) {
            try { Stop-ExactProcessTree -Process $process } catch { try { $process.Kill() } catch { } }
            throw "Conda command timed out after $TimeoutSeconds seconds: $($Arguments -join ' ')"
        }
        $stdout = $stdoutTask.Result
        $stderr = $stderrTask.Result
        $code = $process.ExitCode
        $outputLines = @($stdout -split '\r?\n' | Where-Object { $_ -ne '' })
        $errorLines = @($stderr -split '\r?\n' | Where-Object { $_ -ne '' })
        if (-not $CaptureOutput) {
            $outputLines | ForEach-Object { Write-Host $_ }
            $errorLines | ForEach-Object { Write-Host $_ }
        }
        $commandResult = [pscustomobject]@{
            Output = $outputLines
            ErrorOutput = $errorLines
            ExitCode = $code
            LockWaitSeconds = $lock.WaitSeconds
            UserSiteDisabled = [bool]$DisableUserSite
            TemporaryDirectory = $temporaryDirectory.Path
        }
    } catch {
        $commandFailure = $_
    } finally {
        if (-not $processEnvironmentRestored) {
            foreach ($entry in $processEnvironment.GetEnumerator()) {
                [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, 'Process')
            }
        }
        if ($process) { $process.Dispose() }
        if ($temporaryDirectory) {
            try { $tempCleaned = Remove-CondaTemporaryDirectory -TemporaryDirectory $temporaryDirectory }
            catch { $tempCleanupError = $_.Exception.Message }
        }
        Exit-CondaLock -Lock $lock
    }
    if ($commandFailure) { throw $commandFailure }
    $commandResult | Add-Member -NotePropertyName TemporaryDirectoryCleaned -NotePropertyValue $tempCleaned -Force
    $commandResult | Add-Member -NotePropertyName TemporaryDirectoryCleanupError -NotePropertyValue $tempCleanupError -Force
    return $commandResult
}

function Get-CondaEnvironments {
    param([Parameter(Mandatory)][string]$Conda)
    $result = Invoke-CondaCommand -Conda $Conda -Arguments @('env', 'list', '--json') -CaptureOutput
    if ($result.ExitCode -ne 0) { throw "Unable to enumerate Conda environments: $($result.Output -join [Environment]::NewLine)" }
    $payload = ($result.Output -join '') | ConvertFrom-Json
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $rows = [System.Collections.Generic.List[object]]::new()
    foreach ($rawPrefix in @($payload.envs)) {
        $prefix = [System.IO.Path]::GetFullPath([string]$rawPrefix).TrimEnd('\')
        if (-not $seen.Add($prefix)) { continue }
        $detailProperty = $payload.envs_details.PSObject.Properties | Where-Object { $_.Name -eq [string]$rawPrefix } | Select-Object -First 1
        $detail = if ($detailProperty) { $detailProperty.Value } else { $null }
        $isBase = [bool]($detail -and $detail.base)
        $name = if ($detail -and [string]$detail.name) { [string]$detail.name } elseif ($isBase) { 'base' } else { Split-Path -Leaf $prefix }
        if (-not $name) { $name = if ($isBase) { 'base' } else { Split-Path -Leaf $prefix } }
        $rows.Add([pscustomobject]@{ Name = $name; Prefix = $prefix; IsBase = $isBase })
    }
    return @($rows)
}

function Get-CondaEnvironmentNames {
    param([Parameter(Mandatory)][string]$Conda)
    return @(Get-CondaEnvironments -Conda $Conda | ForEach-Object { $_.Name })
}

function Get-EnvironmentCoverage {
    param(
        [Parameter(Mandatory)][string]$Conda,
        [Parameter(Mandatory)][string]$Prefix,
        [Parameter(Mandatory)]$Requirements
    )
    $imports = @($Requirements.core.python | ForEach-Object { $_.import }) + @($Requirements.extended.python | ForEach-Object { $_.import })
    $joined = $imports -join ' '
    $probe = "import importlib.util as u,importlib.machinery as m,site,sys; names='$joined'.split(); usp=site.getusersitepackages(); print('python='+sys.version.split()[0]+'|'+ '|'.join(n+'='+('yes' if u.find_spec(n) else 'no')+','+('yes' if m.PathFinder.find_spec(n,[usp]) else 'no') for n in names))"
    $result = Invoke-CondaCommand -Conda $Conda -Arguments @('run', '--no-capture-output', '-p', $Prefix, 'python', '-s', '-c', $probe) -CaptureOutput -DisableUserSite
    $available = @{}
    $externalLocal = @{}
    $pythonVersion = $null
    if ($result.ExitCode -eq 0) {
        $raw = ($result.Output -join '').Trim()
        foreach ($item in $raw.Split('|')) {
            if ($item -match '^python=(.+)$') { $pythonVersion = $Matches[1] }
            elseif ($item -match '^([^=]+)=(yes|no),(yes|no)$') {
                $available[$Matches[1]] = ($Matches[2] -eq 'yes')
                $externalLocal[$Matches[1]] = ($Matches[3] -eq 'yes')
            }
        }
    }
    return [pscustomobject]@{ Available = $available; ExternalLocal = $externalLocal; Python = $pythonVersion; ProbeExitCode = $result.ExitCode }
}

function Resolve-ModelingEnvironment {
    param(
        [string]$RequestedName = 'auto',
        [ValidateSet('core','full')][string]$Tier = 'core'
    )
    $conda = Get-CondaExecutable
    $requirements = Get-RequirementManifest
    $environments = @(Get-CondaEnvironments -Conda $conda)
    if ($RequestedName -ne 'auto') {
        $matches = @($environments | Where-Object { $_.Name -eq $RequestedName -or $_.Prefix -eq $RequestedName })
        if ($matches.Count -eq 0) { throw "Requested Conda environment does not exist: $RequestedName" }
        if ($matches.Count -gt 1) {
            $rootPrefix = [System.IO.Path]::GetFullPath((Split-Path (Split-Path $conda -Parent) -Parent)).TrimEnd('\')
            $rootMatch = @($matches | Where-Object { $_.Prefix -eq $rootPrefix })
            if ($RequestedName -eq 'base' -and $rootMatch.Count -eq 1) { $matches = $rootMatch }
            else { throw "Conda environment name is ambiguous; use a prefix: $RequestedName -> $($matches.Prefix -join ', ')" }
        }
        $candidates = $matches
    } else {
        $candidates = $environments
    }
    $coreNames = @($requirements.core.python | ForEach-Object { [string]$_.import })
    $extendedNames = @($requirements.extended.python | ForEach-Object { [string]$_.import })
    $rootPrefix = [System.IO.Path]::GetFullPath((Split-Path (Split-Path $conda -Parent) -Parent)).TrimEnd('\')
    $rows = foreach ($environment in $candidates) {
        $probe = Get-EnvironmentCoverage -Conda $conda -Prefix $environment.Prefix -Requirements $requirements
        $corePrefixMissing = @($coreNames | Where-Object { -not $probe.Available[$_] })
        $coreExternalLocal = @($corePrefixMissing | Where-Object { $probe.ExternalLocal[$_] })
        if ($environment.Prefix -eq $rootPrefix) {
            $coreMissing = @($corePrefixMissing | Where-Object { $_ -notin $coreExternalLocal })
        } else {
            $coreMissing = @($corePrefixMissing)
        }
        $extendedMissing = @($extendedNames | Where-Object { -not $probe.Available[$_] })
        $corePreference = if ($environment.Prefix -eq $rootPrefix) { 30 } elseif ($environment.Name -eq 'math-modeling') { 10 } else { 20 }
        $fullPreference = if ($environment.Name -eq 'math-modeling') { 30 } elseif ($environment.Prefix -eq $rootPrefix) { 20 } else { 10 }
        [pscustomobject]@{
            Name = $environment.Name
            Prefix = $environment.Prefix
            IsBase = $environment.IsBase
            Python = $probe.Python
            ProbeExitCode = $probe.ProbeExitCode
            CoreScore = $coreNames.Count - $coreMissing.Count
            FullScore = $coreNames.Count + $extendedNames.Count - $corePrefixMissing.Count - $extendedMissing.Count
            CoreMissing = $coreMissing
            CorePrefixMissing = $corePrefixMissing
            CoreExternalLocal = $coreExternalLocal
            ExtendedMissing = $extendedMissing
            Coverage = $probe.Available
            CorePreference = $corePreference
            FullPreference = $fullPreference
        }
    }
    if (-not $rows) { throw 'No usable Conda environments were found.' }
    $selected = if ($RequestedName -ne 'auto') {
        @($rows)[0]
    } elseif ($Tier -eq 'full') {
        $rows | Sort-Object @{Expression='FullScore';Descending=$true}, @{Expression='CoreScore';Descending=$true}, @{Expression='FullPreference';Descending=$true}, Name | Select-Object -First 1
    } else {
        $rows | Sort-Object @{Expression='CoreScore';Descending=$true}, @{Expression='CorePreference';Descending=$true}, @{Expression='FullScore';Descending=$true}, Name | Select-Object -First 1
    }
    return [pscustomobject]@{ Conda = $conda; Selected = $selected; Candidates = @($rows); Requirements = $requirements }
}
