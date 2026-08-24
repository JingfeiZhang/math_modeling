[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('preflight','initialize','run','validate','freeze','prepare-sprint','check-sprint','merge-sprint','quickcheck','checkpoint','promote','paper-evidence','refresh-quality-contracts','literature-plan','literature-search','literature-register','literature-read','literature-synthesize','literature-audit','figure-data','figure-intent','figure-brief','figure-render','figure-qa','figure-promote','prompt','layout-check','archive-work','preview','build','audit','package','seal','verify-release','status')]
    [string]$Action,
    [string]$Problem,
    [string]$ProblemFile,
    [string]$Question,
    [ValidateSet('default','q1-solve','q1-compose')]
    [string]$SprintProfile = 'default',
    [string]$InputSprintId,
    [string]$Config,
    [string]$RunId,
    [string]$Intent,
    [string]$Brief,
    [string]$Outputs,
    [string]$Qa,
    [string]$FigureId,
    [ValidateSet('G0','G1','G2','G3','G4','G5','G6')]
    [string]$Gate,
    [string]$DecisionId,
    [switch]$StrictManifest,
    [ValidateSet('off','parallel')]
    [string]$AgentMode = 'off',
    [ValidateRange(1,2147483647)]
    [int]$MaxAgents = 3,
    [string]$SprintId,
    [string]$PreviewCheckpoint = 'full',
    [string]$EnvironmentName = 'auto',
    [string]$Project,
    [ValidateSet('P0','P1','P2','P3a','P3b','P4','P5','P6')]
    [string]$Stage,
    [ValidateSet('orchestrator','solver','literature','visualization','paper','studio_release','reviewer')]
    [string]$Role
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_environment.ps1')
. (Join-Path $PSScriptRoot '_project.ps1')
$projectContext = Resolve-ModelingProject -Project $Project
Assert-ProjectRoot -ProjectContext $projectContext
$root = $projectContext.Root
$hub = $projectContext.HubRoot
$projectExplicitActions = @(
    'literature-plan','literature-search','literature-register','literature-read','literature-synthesize','literature-audit',
    'figure-data','figure-intent','figure-brief','figure-render','figure-qa','figure-promote','prompt','refresh-quality-contracts'
)
if ($Action -in $projectExplicitActions -and [string]::IsNullOrWhiteSpace($Project)) {
    throw "$Action requires an explicit -Project selection."
}
$resolved = Resolve-ModelingEnvironment -RequestedName $EnvironmentName -Tier core
$selected = $resolved.Selected
if ($selected.CoreMissing.Count -gt 0) { throw "Selected environment lacks core packages: $($selected.CoreMissing -join ', ')" }
$python = @('run','--no-capture-output','-p',$selected.Prefix,'python','-s',(Join-Path $hub 'src\workflow\competition_workflow.py'),'--root',$root,'--workspace-root',$hub)

function Invoke-WorkflowPython {
    param([Parameter(Mandatory)][string[]]$Arguments)
    $run = Invoke-CondaCommand -Conda $resolved.Conda -Arguments ($python + $Arguments)
    if ($run.ExitCode -ne 0) { throw "Workflow action failed: $($Arguments -join ' ')" }
}

function Get-ConfiguredProblem {
    if ($Problem) { return $Problem }
    $line = Get-Content -LiteralPath (Join-Path $root 'contest.yaml') -Encoding UTF8 | Where-Object { $_ -match '^problem:\s*(.+?)\s*$' } | Select-Object -First 1
    if (-not $line) { throw 'contest.yaml does not define problem.' }
    return ($line -replace '^problem:\s*','').Trim('"').Trim("'")
}

function New-ValidationArguments {
    param(
        [Parameter(Mandatory)][string]$GateName,
        [string]$QuestionName
    )
    $validationArguments = @('validate','--problem',(Get-ConfiguredProblem),'--gate',$GateName)
    if ($QuestionName) { $validationArguments += @('--question',$QuestionName) }
    if ($StrictManifest) { $validationArguments += '--strict' }
    return $validationArguments
}

function New-V4QuestionArguments {
    param([Parameter(Mandatory)][string]$CommandName)
    $arguments = @($CommandName,'--problem',(Get-ConfiguredProblem))
    if ($Question) { $arguments += @('--question',$Question) }
    if ($StrictManifest) { $arguments += '--strict' }
    return $arguments
}

function Invoke-LayoutPreview {
    if ($PreviewCheckpoint -notmatch '^(frontmatter|full|Q[1-9][0-9]*)$') {
        throw 'layout preview requires -PreviewCheckpoint frontmatter, full, or Q<number>.'
    }
    $previewRoot = Join-Path $root 'output\_verification\previews'
    $previewPdf = Join-Path $previewRoot "$PreviewCheckpoint.pdf"
    $previewPages = Join-Path $previewRoot "$PreviewCheckpoint-pages"
    & (Join-Path $PSScriptRoot 'build_paper.ps1') -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub -OutputPdf $previewPdf -RenderDir $previewPages -PreviewCheckpoint $PreviewCheckpoint
    if ($LASTEXITCODE -ne 0) { throw 'Paper layout preview failed.' }
}

function Resolve-ProjectLocalPath {
    param(
        [Parameter(Mandatory)][string]$Value,
        [Parameter(Mandatory)][string]$Label,
        [switch]$AllowDirectory
    )
    $resolvedValue = (Resolve-Path -LiteralPath $Value).Path
    $projectPrefix = [System.IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    if (-not $resolvedValue.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must remain inside the selected project root: $resolvedValue"
    }
    if (-not $AllowDirectory -and -not (Test-Path -LiteralPath $resolvedValue -PathType Leaf)) {
        throw "$Label must be a file: $resolvedValue"
    }
    return $resolvedValue
}

switch ($Action) {
    'preflight' {
        & (Join-Path $PSScriptRoot 'verify_env.ps1') -EnvironmentName $EnvironmentName -Tier core
        if ($LASTEXITCODE -ne 0) { throw 'Core environment preflight failed.' }
        Invoke-WorkflowPython @('preflight')
    }
    'initialize' {
        if (-not $Problem -or -not $ProblemFile) { throw 'initialize requires -Problem and -ProblemFile.' }
        Invoke-WorkflowPython @('initialize','--problem',$Problem,'--problem-file',(Resolve-Path -LiteralPath $ProblemFile).Path)
    }
    'run' {
        if (-not $Question -or -not $Config) { throw 'run requires -Question and -Config.' }
        & (Join-Path $PSScriptRoot 'run_experiment.ps1') -Config $Config -Question $Question -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Experiment run failed.' }
    }
    'validate' {
        if (-not $Gate) { throw 'validate requires -Gate.' }
        Invoke-WorkflowPython (New-ValidationArguments -GateName $Gate -QuestionName $Question)
    }
    'freeze' {
        if (-not $Question -or -not $DecisionId) { throw 'freeze requires -Question and -DecisionId.' }
        Invoke-WorkflowPython @('freeze','--problem',(Get-ConfiguredProblem),'--question',$Question,'--decision-id',$DecisionId)
    }
    'prepare-sprint' {
        if ($AgentMode -ne 'parallel') { throw 'prepare-sprint requires explicit -AgentMode parallel opt-in.' }
        $arguments = @('prepare-sprint','--agent-mode',$AgentMode,'--max-agents',[string]$MaxAgents)
        if ($Problem) { $arguments += @('--problem',$Problem) }
        if ($Question) { $arguments += @('--question',$Question) }
        if ($SprintProfile -ne 'default') { $arguments += @('--sprint-profile',$SprintProfile) }
        if ($InputSprintId) { $arguments += @('--input-sprint-id',$InputSprintId) }
        Invoke-WorkflowPython $arguments
    }
    'check-sprint' {
        if (-not $SprintId) { throw 'check-sprint requires -SprintId.' }
        Invoke-WorkflowPython @('check-sprint','--sprint-id',$SprintId)
    }
    'merge-sprint' {
        if (-not $SprintId) { throw 'merge-sprint requires -SprintId.' }
        Invoke-WorkflowPython @('merge-sprint','--sprint-id',$SprintId)
    }
    'quickcheck' {
        Invoke-WorkflowPython (New-V4QuestionArguments -CommandName 'quickcheck')
    }
    'checkpoint' {
        Invoke-WorkflowPython (New-V4QuestionArguments -CommandName 'checkpoint')
    }
    'promote' {
        if (-not $Question -or -not $RunId) { throw 'promote requires -Question and -RunId.' }
        Invoke-WorkflowPython @('promote','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId)
    }
    'paper-evidence' {
        if (-not $Question -or -not $Config) { throw 'paper-evidence requires -Question and -Config.' }
        $resolvedConfig = (Resolve-Path -LiteralPath $Config).Path
        $projectPrefix = [System.IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
        if (-not $resolvedConfig.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "paper-evidence config must remain inside the selected project root: $resolvedConfig"
        }
        & (Join-Path $PSScriptRoot 'run_experiment.ps1') -Config $resolvedConfig -Question $Question -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Paper-evidence experiment run failed.' }
        $arguments = @('paper-evidence','--problem',(Get-ConfiguredProblem),'--question',$Question,'--config',$resolvedConfig)
        if ($StrictManifest) { $arguments += '--strict' }
        Invoke-WorkflowPython $arguments
    }
    'refresh-quality-contracts' {
        $arguments = @('refresh-quality-contracts','--problem',(Get-ConfiguredProblem))
        if ($Question) { $arguments += @('--question',$Question) }
        Invoke-WorkflowPython $arguments
    }
    'literature-plan' {
        if (-not $Question) { throw 'literature-plan requires -Question.' }
        $arguments = @('literature-plan','--problem',(Get-ConfiguredProblem),'--question',$Question)
        if ($Config) {
            $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'literature-plan config'
            $arguments += @('--config',$resolvedConfig)
        }
        Invoke-WorkflowPython $arguments
    }
    'literature-search' {
        if (-not $Question -or -not $Config) { throw 'literature-search requires -Question and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'literature-search config'
        Invoke-WorkflowPython @('literature-search','--problem',(Get-ConfiguredProblem),'--question',$Question,'--config',$resolvedConfig)
    }
    'literature-register' {
        if (-not $Question -or -not $Config) { throw 'literature-register requires -Question and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'literature-register config'
        Invoke-WorkflowPython @('literature-register','--problem',(Get-ConfiguredProblem),'--question',$Question,'--config',$resolvedConfig)
    }
    'literature-read' {
        if (-not $Question -or -not $Config) { throw 'literature-read requires -Question and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'literature-read config'
        Invoke-WorkflowPython @('literature-read','--problem',(Get-ConfiguredProblem),'--question',$Question,'--config',$resolvedConfig)
    }
    'literature-synthesize' {
        if (-not $Question -or -not $Config) { throw 'literature-synthesize requires -Question and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'literature-synthesize config'
        Invoke-WorkflowPython @('literature-synthesize','--problem',(Get-ConfiguredProblem),'--question',$Question,'--config',$resolvedConfig)
    }
    'literature-audit' {
        $arguments = @('literature-audit','--problem',(Get-ConfiguredProblem))
        if ($Question) { $arguments += @('--question',$Question) }
        if ($StrictManifest) { $arguments += '--strict' }
        Invoke-WorkflowPython $arguments
    }
    'figure-data' {
        if (-not $Question -or -not $RunId -or -not $Config) { throw 'figure-data requires -Question, -RunId, and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'figure-data config'
        Invoke-WorkflowPython @('figure-data','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId,'--config',$resolvedConfig)
    }
    'figure-intent' {
        if (-not $Question -or -not $RunId -or -not $Config) { throw 'figure-intent requires -Question, -RunId, and -Config.' }
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'figure-intent config'
        Invoke-WorkflowPython @('figure-intent','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId,'--config',$resolvedConfig)
    }
    'figure-brief' {
        if (-not $Question -or -not $RunId -or -not $Intent -or -not $Config) { throw 'figure-brief requires -Question, -RunId, -Intent, and -Config.' }
        $resolvedIntent = Resolve-ProjectLocalPath -Value $Intent -Label 'visual intent'
        $resolvedConfig = Resolve-ProjectLocalPath -Value $Config -Label 'figure-brief config'
        Invoke-WorkflowPython @('figure-brief','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId,'--intent',$resolvedIntent,'--config',$resolvedConfig)
    }
    'figure-render' {
        if (-not $Question -or -not $RunId -or -not $Brief) { throw 'figure-render requires -Question, -RunId, and -Brief.' }
        $resolvedBrief = Resolve-ProjectLocalPath -Value $Brief -Label 'figure brief'
        Invoke-WorkflowPython @('figure-render','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId,'--brief',$resolvedBrief)
    }
    'figure-qa' {
        if (-not $Question -or -not $RunId -or -not $Brief -or -not $Outputs) { throw 'figure-qa requires -Question, -RunId, -Brief, and -Outputs.' }
        $resolvedBrief = Resolve-ProjectLocalPath -Value $Brief -Label 'figure brief'
        $resolvedOutputs = Resolve-ProjectLocalPath -Value $Outputs -Label 'figure outputs' -AllowDirectory
        Invoke-WorkflowPython @('figure-qa','--problem',(Get-ConfiguredProblem),'--question',$Question,'--run-id',$RunId,'--brief',$resolvedBrief,'--outputs',$resolvedOutputs)
    }
    'figure-promote' {
        if (-not $Question -or -not $FigureId -or -not $Brief -or -not $Qa) { throw 'figure-promote requires -Question, -FigureId, -Brief, and -Qa.' }
        $resolvedBrief = Resolve-ProjectLocalPath -Value $Brief -Label 'figure brief'
        $resolvedQa = Resolve-ProjectLocalPath -Value $Qa -Label 'figure QA'
        Invoke-WorkflowPython @('figure-promote','--problem',(Get-ConfiguredProblem),'--question',$Question,'--figure-id',$FigureId,'--brief',$resolvedBrief,'--qa',$resolvedQa,'--root-authorized')
    }
    'prompt' {
        if (-not $Project -or -not $Stage -or -not $Role) { throw 'prompt requires -Project, -Stage, and -Role.' }
        if ($Stage -notin @('P0','P1') -and -not $Question) { throw 'prompt requires -Question for stages P2-P6.' }
        $arguments = @('prompt','--project-id',$Project,'--stage',$Stage,'--role',$Role)
        if ($Question) { $arguments += @('--question',$Question) }
        Invoke-WorkflowPython $arguments
    }
    'layout-check' {
        Invoke-LayoutPreview
    }
    'archive-work' {
        $arguments = @('archive-work','--problem',(Get-ConfiguredProblem))
        if ($Question) { $arguments += @('--question',$Question) }
        Invoke-WorkflowPython $arguments
    }
    'preview' {
        Invoke-LayoutPreview
    }
    'build' {
        & (Join-Path $PSScriptRoot 'build_paper.ps1') -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Paper build failed.' }
    }
    'audit' {
        Invoke-WorkflowPython (New-ValidationArguments -GateName 'G5')
        & (Join-Path $PSScriptRoot 'audit_submission.ps1') -EnvironmentName $EnvironmentName -Strict -SkipPackage -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Pre-package submission audit failed.' }
    }
    'package' {
        Invoke-WorkflowPython (New-ValidationArguments -GateName 'G5')
        foreach ($name in @('paper_audit.json','figure_audit.json','pdf_visual_audit.json')) {
            if (-not (Test-Path -LiteralPath (Join-Path $root "output\$name"))) { throw "Run -Action audit before packaging; missing output/$name" }
        }
        & (Join-Path $PSScriptRoot 'package_submission.ps1') -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Submission packaging failed.' }
        Invoke-WorkflowPython (New-ValidationArguments -GateName 'G6')
    }
    'seal' {
        Invoke-WorkflowPython (New-ValidationArguments -GateName 'G6')
        & (Join-Path $PSScriptRoot 'release_submission.ps1') -Action seal -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Submission release sealing failed.' }
    }
    'verify-release' {
        & (Join-Path $PSScriptRoot 'release_submission.ps1') -Action verify -EnvironmentName $EnvironmentName -ProjectRoot $root -WorkspaceRoot $hub
        if ($LASTEXITCODE -ne 0) { throw 'Sealed submission verification failed.' }
    }
    'status' { Invoke-WorkflowPython @('status') }
}
