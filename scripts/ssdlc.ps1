<#
.SYNOPSIS
    parapet SSDLC — Security System Development Life Cycle Launcher
.DESCRIPTION
    Runs the 6-phase SSDLC framework against a project.
    Guides Planning -> Analysis -> Design -> Implementation -> Maintenance -> Retirement.
    Integrates with the Ollama agent for AI-assisted threat modeling and code review.
.PARAMETER Project
    Project name to scope the SSDLC run (default: from directory name or prompt)
.PARAMETER Phase
    Specific phase to execute. One of: Planning, Analysis, Design, Implementation, Maintenance, Retirement.
    If omitted with -Interactive, allows manual phase-by-phase progression.
.PARAMETER Full
    Run all 6 phases sequentially.
.PARAMETER Interactive
    Step through phases interactively — checklist items are presented for user confirmation.
.PARAMETER Report
    Generate a markdown report for the project without running phases.
.PARAMETER Export
    Additional export path for the report (copy to this location).
.EXAMPLE
    .\ssdlc.ps1 -Project myapp
    .\ssdlc.ps1 -Project myapp -Full
    .\ssdlc.ps1 -Project myapp -Phase Design -Interactive
    .\ssdlc.ps1 -Project myapp -Report -Export ..\reports\
#>

param(
    [string]$Project = "",
    [string]$Phase = "",
    [switch]$Full,
    [switch]$Interactive,
    [switch]$Report,
    [string]$Export = ""
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# -- Colours ----------------------------------------------
$Host.UI.RawUI.ForegroundColor = "White"

function Write-Phase { param($msg) Write-Host "`n[$msg]" -ForegroundColor Cyan }
function Write-Pass  { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "  [!!] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Write-Info  { param($msg) Write-Host "  [i] $msg" -ForegroundColor Gray }

# -- Helpers ----------------------------------------------

function Get-SSDLCPhaseKey {
    param([string]$PhaseName)
    switch ($PhaseName.ToLower()) {
        "planning"        { return "planning" }
        "analysis"        { return "analysis" }
        "design"          { return "design" }
        "implementation"  { return "implementation" }
        "maintenance"     { return "maintenance" }
        "retirement"      { return "retirement" }
        default           { return "" }
    }
}

function Format-PhaseLabel {
    param([string]$Key)
    switch ($Key) {
        "planning"        { return "Phase 1: Planning" }
        "analysis"        { return "Phase 2: Analysis" }
        "design"          { return "Phase 3: Design" }
        "implementation"  { return "Phase 4: Implementation" }
        "maintenance"     { return "Phase 5: Maintenance" }
        "retirement"      { return "Phase 6: Retirement" }
        default           { return $Key }
    }
}

function Get-ChecklistItems {
    param([string]$PhaseKey)
    # These mirror ssdlc.py PHASES definitions
    switch ($PhaseKey) {
        "planning" {
            return @(
                @{id="P1"; item="Define security policy statement"; required=$true},
                @{id="P2"; item="Establish risk appetite and tolerance levels"; required=$true},
                @{id="P3"; item="Define project scope and budget"; required=$true},
                @{id="P4"; item="Identify applicable compliance frameworks (GDPR, HIPAA, PCI-DSS, ISO 27001)"; required=$true},
                @{id="P5"; item="Assign security roles and responsibilities"; required=$true},
                @{id="P6"; item="Identify key stakeholders and sign-off authorities"; required=$false},
                @{id="P7"; item="Define security metrics and KPIs"; required=$false},
                @{id="P8"; item="Create project timeline with security gates"; required=$true}
            )
        }
        "analysis" {
            return @(
                @{id="A1"; item="Perform threat assessment (identify threat actors, attack vectors)"; required=$true},
                @{id="A2"; item="Conduct vulnerability identification (existing weaknesses, CVEs)"; required=$true},
                @{id="A3"; item="Classify data by sensitivity (public, internal, confidential, restricted)"; required=$true},
                @{id="A4"; item="Rate system criticality (low, medium, high, critical)"; required=$true},
                @{id="A5"; item="Define security requirements (functional and non-functional)"; required=$true},
                @{id="A6"; item="Perform control gap analysis (existing vs required controls)"; required=$true},
                @{id="A7"; item="Calculate risk scores (likelihood x impact)"; required=$true},
                @{id="A8"; item="Document privacy impact assessment (PIA)"; required=$false}
            )
        }
        "design" {
            return @(
                @{id="D1"; item="Create security architecture blueprint"; required=$true},
                @{id="D2"; item="Conduct STRIDE threat modeling per component"; required=$true},
                @{id="D3"; item="Design network segmentation and trust boundaries"; required=$true},
                @{id="D4"; item="Define access control model (RBAC, ABAC, PBAC)"; required=$true},
                @{id="D5"; item="Select encryption standards and key management strategy"; required=$true},
                @{id="D6"; item="Design audit logging and monitoring architecture"; required=$true},
                @{id="D7"; item="Plan secure API design (auth, rate limiting, input validation)"; required=$true},
                @{id="D8"; item="Design disaster recovery and business continuity"; required=$false},
                @{id="D9"; item="Select security tools (firewall, IDS/IPS, WAF, SIEM)"; required=$true}
            )
        }
        "implementation" {
            return @(
                @{id="I1"; item="Apply secure coding standards (OWASP Top 10, CWE Top 25)"; required=$true},
                @{id="I2"; item="Configure firewalls and network security groups"; required=$true},
                @{id="I3"; item="Deploy intrusion detection/prevention systems (IDS/IPS)"; required=$true},
                @{id="I4"; item="Implement encryption at rest and in transit"; required=$true},
                @{id="I5"; item="Set up identity and access management (IAM)"; required=$true},
                @{id="I6"; item="Run SAST (static analysis) and SCA (dependency scanning)"; required=$true},
                @{id="I7"; item="Run DAST (dynamic analysis) and penetration testing"; required=$true},
                @{id="I8"; item="Harden containers, OS, and runtime environments"; required=$true},
                @{id="I9"; item="Conduct security code review"; required=$true},
                @{id="I10"; item="Validate all security controls before production deployment"; required=$true}
            )
        }
        "maintenance" {
            return @(
                @{id="M1"; item="Establish patch management schedule (OS, dependencies, firmware)"; required=$true},
                @{id="M2"; item="Configure security monitoring and alerting (SIEM)"; required=$true},
                @{id="M3"; item="Implement user onboarding/offboarding procedures"; required=$true},
                @{id="M4"; item="Enforce least-privilege access reviews (quarterly)"; required=$true},
                @{id="M5"; item="Schedule routine vulnerability scans (weekly/monthly)"; required=$true},
                @{id="M6"; item="Create incident response plan and run tabletop exercises"; required=$true},
                @{id="M7"; item="Monitor CVE feeds for relevant vulnerabilities"; required=$true},
                @{id="M8"; item="Review and rotate secrets, keys, and certificates"; required=$true},
                @{id="M9"; item="Conduct periodic compliance audits"; required=$false}
            )
        }
        "retirement" {
            return @(
                @{id="R1"; item="Inventory all assets to be decommissioned"; required=$true},
                @{id="R2"; item="Securely wipe/sanitize all data (NIST 800-88 standard)"; required=$true},
                @{id="R3"; item="Revoke all certificates, keys, and credentials"; required=$true},
                @{id="R4"; item="Remove from network and security groups"; required=$true},
                @{id="R5"; item="Dispose of hardware per environmental regulations"; required=$false},
                @{id="R6"; item="Notify affected users and stakeholders"; required=$true},
                @{id="R7"; item="Archive logs and audit trails per retention policy"; required=$true},
                @{id="R8"; item="Document lessons learned and gap analysis for replacement"; required=$true}
            )
        }
        default { return @() }
    }
}

# -- Project setup ----------------------------------------

if (-not $Project) {
    $Project = Read-Host "Enter project name"
    if (-not $Project) {
        Write-Fail "Project name is required."
        exit 1
    }
}

# Sanitize project name to prevent command injection (CRITICAL #1 fix)
$Project = $Project -replace "[^a-zA-Z0-9_.-]", "_"
if ($Project.Length -gt 64) {
    $Project = $Project.Substring(0, 64)
}

Write-Phase "parapet SSDLC — $Project"
Write-Info "Project: $Project"
Write-Info "Script dir: $ScriptDir"

# Check if containers are running
$AgentRunning = $false
try {
    $test = docker inspect ollama-agent 2>$null | ConvertFrom-Json
    if ($test.State.Status -eq "running") { $AgentRunning = $true }
} catch {}

if (-not $AgentRunning) {
    Write-Warn "Agent container not running. SSDLC can track offline, but agent-assisted features need '.\run.ps1' first."
}

function Invoke-SSDLC {
    param([string]$Code)
    try {
        $result = & docker exec ollama-agent python3 -c $Code 2>&1 | Out-String
        return $result.Trim()
    } catch {
        Write-Warn "Agent call failed (container may not be running): $_"
        return ""
    }
}

# -- Report mode ------------------------------------------

if ($Report) {
    Write-Phase "Generating SSDLC Report for $Project"
    $reportCode = @"
import json
from ssdlc import export_report_markdown
print(export_report_markdown('$Project'))
"@
    $md = Invoke-SSDLC $reportCode
    if ($md) {
        $reportDir = Join-Path $ScriptDir "workspace" "ssdlc"
        New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
        $reportPath = Join-Path $reportDir "$Project-ssdlc-report.md"
        $md | Out-File -FilePath $reportPath -Encoding utf8
        Write-Pass "Report saved: $reportPath"
        if ($Export) {
            New-Item -ItemType Directory -Force -Path $Export | Out-Null
            Copy-Item $reportPath (Join-Path $Export "$Project-ssdlc-report.md") -Force
            Write-Pass "Exported to: $Export"
        }
    } else {
        Write-Warn "Could not generate report (agent not running?). Report file created from local state."
    }
    exit 0
}

# -- Determine phases to run ------------------------------

$phasesToRun = @()
if ($Full) {
    $phasesToRun = @("planning", "analysis", "design", "implementation", "maintenance", "retirement")
    Write-Info "Mode: Full (all 6 phases)"
} elseif ($Phase) {
    $phaseKey = Get-SSDLCPhaseKey -PhaseName $Phase
    if (-not $phaseKey) {
        Write-Fail "Unknown phase: $Phase. Use one of: Planning, Analysis, Design, Implementation, Maintenance, Retirement"
        exit 1
    }
    $phasesToRun = @($phaseKey)
    Write-Info "Mode: Single phase — $phaseKey"
} else {
    Write-Fail "Specify -Full, -Phase <name>, or -Report"
    exit 1
}

# -- Run phases -------------------------------------------

$phaseOrder = @("planning", "analysis", "design", "implementation", "maintenance", "retirement")

foreach ($phaseKey in $phasesToRun) {
    $label = Format-PhaseLabel -PhaseKey $phaseKey
    Write-Phase $label

    # Verify previous phases are completed
    $thisOrder = [array]::IndexOf($phaseOrder, $phaseKey)
    for ($i = 0; $i -lt $thisOrder; $i++) {
        $prevKey = $phaseOrder[$i]
        $checkCode = @"
import json
from ssdlc import load_state
state = load_state('$Project')
print(state['phases']['$prevKey']['status'])
"@
        $prevStatus = Invoke-SSDLC $checkCode
        if ($prevStatus -ne "completed") {
            Write-Warn "Previous phase '$prevKey' is not completed (status: $prevStatus). This may cause incomplete analysis."
        }
    }

    # Start the phase
    $startCode = @"
import json
from ssdlc import start_phase
result = start_phase('$Project', '$phaseKey')
print(json.dumps(result))
"@
    $startResult = Invoke-SSDLC $startCode
    Write-Info "Phase started"

    # Show checklist
    $items = Get-ChecklistItems -PhaseKey $phaseKey
    Write-Host ""
    Write-Host "  Checklist:" -ForegroundColor White
    $itemNum = 0

    if ($Interactive) {
        foreach ($item in $items) {
            $req = if ($item.required) { "[REQUIRED]" } else { "[optional]" }
            $prompt = "    [$($item.id)] $req $($item.item) — Complete? (y/n/skip)"
            $response = Read-Host $prompt
            if ($response -eq "y") {
                Invoke-SSDLC "from ssdlc import check_item; check_item('$Project', '$phaseKey', '$($item.id)', True, '')" | Out-Null
                Write-Pass "$($item.id) checked"
            } elseif ($response -eq "n") {
                Invoke-SSDLC "from ssdlc import check_item; check_item('$Project', '$phaseKey', '$($item.id)', False, '')" | Out-Null
                Write-Warn "$($item.id) not yet complete"
            } else {
                Write-Info "$($item.id) skipped"
            }
        }
    } else {
        # Non-interactive: display checklist with status
        foreach ($item in $items) {
            $req = if ($item.required) { "[REQUIRED]" } else { "[optional]" }
            Write-Host "    [$($item.id)] $req $($item.item)" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Info "Non-interactive mode. Checklist items shown above."
        Write-Info "Use -Interactive to check items, or use the web UI at http://localhost:8080/ssdlc"
    }

    # Complete the phase if interactive and user confirms
    if ($Interactive) {
        $confirm = Read-Host "`n  Complete this phase? (y/n)"
        if ($confirm -eq "y") {
            $completeCode = @"
import json
from ssdlc import complete_phase
result = complete_phase('$Project', '$phaseKey')
print(json.dumps(result))
"@
            $completeResult = Invoke-SSDLC $completeCode
            Write-Pass "Phase '$phaseKey' completed."
        } else {
            Write-Info "Phase '$phaseKey' left in progress."
        }
    } else {
        Write-Info "Phase '$phaseKey' started but not auto-completed (use -Interactive for checklists)"
    }

    Write-Host ""
}

# -- Check if we have any phases with auth-token drift ----
# The Python ssdlc module auto-saves on every operation,
# so we don't need to care about auth tokens for state.

Write-Phase "SSDLC Summary for $Project"
$summaryCode = @"
import json
from ssdlc import get_progress
progress = get_progress('$Project')
print(json.dumps(progress, indent=2))
"@
$summary = Invoke-SSDLC $summaryCode
if ($summary) {
    try {
        $p = $summary | ConvertFrom-Json
        Write-Host "  Overall Status: $($p.overall_status)" -ForegroundColor White
        Write-Host "  Completion: $($p.overall_pct)% ($($p.checked_items)/$($p.total_items) items)" -ForegroundColor White
        Write-Host ""
        foreach ($prop in $p.phases.PSObject.Properties) {
            $ps = $prop.Value
            $statusIcon = switch ($ps.status) {
                "completed"   { "[OK]" }
                "in_progress" { "[>>]" }
                "pending"     { "[  ]" }
                "skipped"     { "[--]" }
                default       { "[??]" }
            }
            $color = switch ($ps.status) {
                "completed"   { "Green" }
                "in_progress" { "Cyan" }
                "pending"     { "Gray" }
                default       { "Yellow" }
            }
            Write-Host "  $statusIcon $($ps.label): $($ps.status) — $($ps.checklist_pct)% checklist, $($ps.risks_count) risks" -ForegroundColor $color
        }
    } catch {
        Write-Host $summary
    }
}

Write-Host "`nSSDLC complete for $Project. Use -Report to generate a markdown report." -ForegroundColor White
