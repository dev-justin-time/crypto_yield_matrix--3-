<#
.SYNOPSIS
    Restarts the Blocks provider runtimes and the Node gateway managed by this
    repository.

.DESCRIPTION
    The default action stops runtimes previously started by this script and
    starts the selected provider projects again, plus the all-agent Node
    gateway (crypto_yield_matrix_node_gateway). It never stops arbitrary
    processes named blocks or node; only PIDs recorded in
    .blocks-agent-state.json are eligible for termination.

    The first run starts the selected processes and records their PIDs. Later
    runs can safely restart those same processes. Logs are written under
    blocks-agent-logs/ and credentials remain in each project's ignored .env.

    Use -AgentName gateway to manage only the Node gateway, -SkipGateway to
    manage only the provider runtimes, and -AgentName <name> to manage a
    single provider.

.PARAMETER AgentName
    Agent directory name, wildcard pattern, or the special value 'gateway'.
    Defaults to all deployment projects plus the gateway, for example:
    -AgentName crypto_risk_analyst

.PARAMETER StopOnly
    Stop managed runtimes without starting them again.

.PARAMETER StartOnly
    Start selected runtimes without stopping existing managed runtimes.

.PARAMETER SkipGateway
    Do not manage the Node gateway process.

.EXAMPLE
    .\Restart-BlocksAgents.ps1

.EXAMPLE
    .\Restart-BlocksAgents.ps1 -AgentName crypto_risk_analyst

.EXAMPLE
    .\Restart-BlocksAgents.ps1 -AgentName gateway

.EXAMPLE
    .\Restart-BlocksAgents.ps1 -SkipGateway

.EXAMPLE
    .\Restart-BlocksAgents.ps1 -StopOnly

.EXAMPLE
    .\Restart-BlocksAgents.ps1 -WhatIf
#>

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Position = 0)]
    [string]$AgentName = '*',

    [switch]$StopOnly,

    [switch]$StartOnly,

    [switch]$SkipGateway
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($StopOnly -and $StartOnly) {
    throw 'Use only one of -StopOnly or -StartOnly.'
}
if ($AgentName -eq 'gateway' -and $SkipGateway) {
    throw 'Use only one of -AgentName gateway or -SkipGateway.'
}

$repoRoot = $PSScriptRoot
$deployRoot = Join-Path $repoRoot 'blocks_deploy'
$gatewayDir = Join-Path $repoRoot 'crypto_yield_matrix_node_gateway'
$gatewayName = 'gateway'
$statePath = Join-Path $repoRoot '.blocks-agent-state.json'
$logRoot = Join-Path $repoRoot 'blocks-agent-logs'

if (-not (Test-Path -LiteralPath $deployRoot -PathType Container)) {
    throw "Deployment directory not found: $deployRoot"
}

function Resolve-BlocksCommand {
    $installedPath = Join-Path $env:USERPROFILE '.blocks\bin\blocks.exe'
    if (Test-Path -LiteralPath $installedPath -PathType Leaf) {
        return $installedPath
    }

    $command = Get-Command blocks.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command blocks -ErrorAction SilentlyContinue
    }
    if ($command) {
        return $command.Source
    }

    throw "Blocks CLI not found. Install it or add %USERPROFILE%\.blocks\bin to PATH."
}

function Resolve-NodeCommand {
    $command = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $command) {
        $command = Get-Command node -ErrorAction SilentlyContinue
    }
    if ($command) {
        return $command.Source
    }

    throw 'Node.js not found on PATH. Install Node.js 18+ (or 22+, see setup.md) to manage the gateway.'
}

function Read-State {
    $result = @{}
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        return $result
    }

    try {
        $parsed = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    }
    catch {
        throw "Unable to read state file '$statePath'. Repair or remove it before restarting agents. $($_.Exception.Message)"
    }

    if ($null -ne $parsed) {
        foreach ($property in $parsed.PSObject.Properties) {
            $result[$property.Name] = $property.Value
        }
    }
    return $result
}

function Save-State([hashtable]$state) {
    if ($state.Count -eq 0) {
        if (Test-Path -LiteralPath $statePath -PathType Leaf) {
            Remove-Item -LiteralPath $statePath -Force
        }
        return
    }
    $temporaryPath = "$statePath.$PID.tmp"
    $state | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $temporaryPath -Encoding UTF8
    Move-Item -LiteralPath $temporaryPath -Destination $statePath -Force
}

function Get-ProcessStartStamp([System.Diagnostics.Process]$process) {
    try {
        return $process.StartTime.ToUniversalTime().ToString('o')
    }
    catch {
        return $null
    }
}

function Get-ProcessCommandLine([int]$processId) {
    try {
        $cimProcess = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $processId" -ErrorAction Stop
        return $cimProcess.CommandLine
    }
    catch {
        return $null
    }
}

function Test-ManagedProcess([System.Diagnostics.Process]$process, $record) {
    $expectedExecutable = [string]$record.ExecutablePath
    if (-not [string]::IsNullOrWhiteSpace($expectedExecutable)) {
        try {
            $actualExecutable = $process.MainModule.FileName
            if (-not [string]::Equals($actualExecutable, $expectedExecutable, [StringComparison]::OrdinalIgnoreCase)) {
                return $false
            }
        }
        catch {
            return $false
        }
    }

    $commandLine = Get-ProcessCommandLine $process.Id
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    if ([string]$record.Kind -eq 'gateway') {
        # The Node gateway is started as: node --import tsx index.ts
        return ($commandLine -match '(?i)index\.ts')
    }

    return ($commandLine -match '(?i)(^|[\s"''])run($|[\s])')
}

function Stop-ManagedAgent {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [string]$name,
        [hashtable]$state
    )

    if (-not $state.ContainsKey($name)) {
        Write-Host "[$name] no managed PID recorded; nothing to stop."
        return $true
    }

    $record = $state[$name]
    $pidValue = 0
    try { $pidValue = [int]$record.Pid } catch { $pidValue = 0 }
    if ($pidValue -le 0) {
        Write-Warning "[$name] invalid PID in state; removing stale state without stopping a process."
        $state.Remove($name)
        return $true
    }

    $process = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
    if (-not $process) {
        Write-Host "[$name] PID $pidValue is not running; removing stale state."
        $state.Remove($name)
        return $true
    }

    $actualStart = Get-ProcessStartStamp $process
    $expectedStart = [string]$record.StartTimeUtc
    if ([string]::IsNullOrWhiteSpace($actualStart) -or $actualStart -ne $expectedStart -or -not (Test-ManagedProcess $process $record)) {
        Write-Warning "[$name] PID $pidValue does not match the recorded process identity; refusing to stop or replace it. Resolve the stale state in '$statePath'."
        return $false
    }

    if ($PSCmdlet.ShouldProcess("$name (PID $pidValue)", 'stop the managed process tree')) {
        & taskkill.exe /PID $pidValue /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "[$name] taskkill failed for PID $pidValue (exit code $LASTEXITCODE)."
        }
        $state.Remove($name)
        Write-Host "[$name] stopped PID $pidValue and its child processes."
    }
    return $true
}

function Start-ManagedRuntime {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
    param(
        [string]$name,
        [string]$workingDirectory,
        [string]$command,
        [string[]]$argumentList,
        [string]$kind,
        [hashtable]$state
    )

    if ($state.ContainsKey($name)) {
        $record = $state[$name]
        $existingPid = 0
        try { $existingPid = [int]$record.Pid } catch { $existingPid = 0 }
        $existingProcess = if ($existingPid -gt 0) { Get-Process -Id $existingPid -ErrorAction SilentlyContinue } else { $null }
        $existingStart = if ($existingProcess) { Get-ProcessStartStamp $existingProcess } else { $null }
        if ($existingProcess -and $existingStart -eq [string]$record.StartTimeUtc -and (Test-ManagedProcess $existingProcess $record)) {
            Write-Host "[$name] managed process PID $existingPid is already running; not starting a duplicate."
            return
        }
        if ($existingProcess) {
            throw "[$name] recorded PID $existingPid is running but does not match its recorded start time; refusing to start a duplicate. Resolve the stale state in '$statePath'."
        }
        $state.Remove($name)
    }
    $runtimeLogRoot = Join-Path $logRoot $name
    $stdoutLog = Join-Path $runtimeLogRoot 'stdout.log'
    $stderrLog = Join-Path $runtimeLogRoot 'stderr.log'
    $description = "$name in $workingDirectory"

    if (-not $PSCmdlet.ShouldProcess($description, 'start the managed runtime')) {
        return
    }

    if (-not (Test-Path -LiteralPath $runtimeLogRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $runtimeLogRoot -Force | Out-Null
    }

    $process = Start-Process `
        -FilePath $command `
        -ArgumentList $argumentList `
        -WorkingDirectory $workingDirectory `
        -RedirectStandardOutput $stdoutLog `
        -RedirectStandardError $stderrLog `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Milliseconds 500
    $process.Refresh()
    if ($process.HasExited) {
        throw "[$name] runtime exited immediately with code $($process.ExitCode). See $stderrLog."
    }

    $startStamp = Get-ProcessStartStamp $process
    if ([string]::IsNullOrWhiteSpace($startStamp)) {
        & taskkill.exe /PID $process.Id /T /F | Out-Null
        throw "[$name] could not read the new process start time; stopped PID $($process.Id) instead of recording unsafe state."
    }

    $state[$name] = [ordered]@{
        Kind           = $kind
        Pid            = $process.Id
        StartTimeUtc   = $startStamp
        ExecutablePath = $command
        Project        = $workingDirectory
        StartedUtc     = [DateTime]::UtcNow.ToString('o')
    }
    Write-Host "[$name] started ($kind, PID $($process.Id))."
}

function Start-Agent {
    param(
        [System.IO.DirectoryInfo]$project,
        [hashtable]$state,
        [string]$blocksCommand
    )
    Start-ManagedRuntime `
        -Name $project.Name `
        -WorkingDirectory $project.FullName `
        -Command $blocksCommand `
        -ArgumentList @('run') `
        -Kind 'agent' `
        -State $state
}

function Start-Gateway {
    param(
        [hashtable]$state,
        [string]$nodeCommand
    )
    Start-ManagedRuntime `
        -Name $gatewayName `
        -WorkingDirectory $gatewayDir `
        -Command $nodeCommand `
        -ArgumentList @('--import', 'tsx', 'index.ts') `
        -Kind 'gateway' `
        -State $state
}

if ($AgentName -eq 'gateway') {
    $projects = @()
}
else {
    $projects = @(
        Get-ChildItem -LiteralPath $deployRoot -Directory |
            Where-Object {
                $_.Name -like $AgentName -and
                (Test-Path -LiteralPath (Join-Path $_.FullName 'agent-card.json') -PathType Leaf)
            } |
            Sort-Object Name
    )
    if ($projects.Count -eq 0) {
        throw "No deployment project matched AgentName '$AgentName'."
    }
}

$manageGateway = (-not $SkipGateway) -and ($AgentName -eq '*' -or $AgentName -eq 'gateway')
if ($projects.Count -eq 0 -and -not $manageGateway) {
    throw 'Nothing selected: use -AgentName to pick a provider or run with the default fleet and gateway.'
}

$state = Read-State
$blocksCommand = $null
$nodeCommand = $null
if (-not $StopOnly -and -not $WhatIfPreference) {
    if ($projects.Count -gt 0) {
        $blocksCommand = Resolve-BlocksCommand
    }
    if ($manageGateway) {
        $nodeCommand = Resolve-NodeCommand
    }
}

$stopFailures = @()
$startFailures = @()
if (-not $StartOnly) {
    foreach ($project in $projects) {
        try {
            if (-not (Stop-ManagedAgent $project.Name $state)) {
                $stopFailures += $project.Name
            }
        }
        catch {
            $stopFailures += $project.Name
            Write-Error $_
        }
    }
    if ($manageGateway) {
        try {
            if (-not (Stop-ManagedAgent $gatewayName $state)) {
                $stopFailures += $gatewayName
            }
        }
        catch {
            $stopFailures += $gatewayName
            Write-Error $_
        }
    }
}

if ($stopFailures.Count -gt 0 -and -not $StartOnly) {
    Write-Warning ("Refusing to start runtimes whose managed process could not be safely stopped: " + ($stopFailures -join ', '))
}

if (-not $StopOnly) {
    foreach ($project in $projects) {
        if ($stopFailures -contains $project.Name) {
            continue
        }
        try {
            Start-Agent $project $state $blocksCommand
        }
        catch {
            $startFailures += $project.Name
            Write-Error $_
        }
    }
    if ($manageGateway -and $stopFailures -notcontains $gatewayName) {
        try {
            Start-Gateway $state $nodeCommand
        }
        catch {
            $startFailures += $gatewayName
            Write-Error $_
        }
    }
}

if (-not $WhatIfPreference) {
    Save-State $state
}

if ($stopFailures.Count -gt 0 -or $startFailures.Count -gt 0) {
    if ($stopFailures.Count -gt 0) {
        Write-Error ("Stop failures: " + ($stopFailures -join ', '))
    }
    if ($startFailures.Count -gt 0) {
        Write-Error ("Start failures: " + ($startFailures -join ', '))
    }
    exit 1
}

Write-Host "Managed process state: $statePath"
Write-Host "Process logs: $logRoot"
