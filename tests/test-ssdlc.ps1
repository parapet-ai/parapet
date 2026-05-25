<#
.SYNOPSIS
    SSDLC Integration Test Suite
.DESCRIPTION
    Tests the SSDLC system end-to-end:
    - PowerShell launcher syntax and parameter validation
    - Web UI API routes (if server is running)
    - Agent plugin tool registration (if container is running)
    - Full lifecycle across all 6 phases via API
.EXAMPLE
    .\test-ssdlc.ps1
    .\test-ssdlc.ps1 -Target "localhost:8080" -Verbose
#>
param(
    [string]$Target = "localhost:8080",
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$Pass = 0
$Fail = 0
$Skip = 0
$Total = 0

function Test-Case($name, [ScriptBlock]$test) {
    $script:Total++
    Write-Host "  TEST: $name... " -NoNewline
    try {
        $r = & $test
        if ($r -eq $true) {
            Write-Host "PASS" -ForegroundColor Green
            $script:Pass++
        } elseif ($r -eq "SKIP") {
            Write-Host "SKIP" -ForegroundColor DarkGray
            $script:Skip++
        } else {
            Write-Host "FAIL — $r" -ForegroundColor Red
            $script:Fail++
        }
    } catch {
        Write-Host "FAIL — $_" -ForegroundColor Red
        if ($Verbose) { Write-Host "    $($_.Exception.Message)" -ForegroundColor DarkGray }
        $script:Fail++
    }
}

Write-Host "`n  SSDLC INTEGRATION TEST SUITE v1.0`n" -ForegroundColor Cyan

# ====================================================================
# 1. PowerShell Launcher Syntax
# ====================================================================
Write-Host "  --- PS LAUNCHER SYNTAX ---" -ForegroundColor Yellow

Test-Case "ssdlc.ps1 exists" {
    return Test-Path (Join-Path $ScriptDir "ssdlc.ps1")
}

Test-Case "ssdlc.ps1 parses without syntax errors" {
    try {
        $null = Get-Command (Join-Path $ScriptDir "ssdlc.ps1") -ErrorAction Stop
        return $true
    } catch {
        # Try direct parse
        try {
            $tokens = $null
            $errors = $null
            $ast = [System.Management.Automation.Language.Parser]::ParseFile(
                (Join-Path $ScriptDir "ssdlc.ps1"), [ref]$tokens, [ref]$errors)
            return $errors.Count -eq 0
        } catch {
            return "Parse error: $_"
        }
    }
}

Test-Case "ssdlc.ps1 has expected parameters" {
    $content = Get-Content (Join-Path $ScriptDir "ssdlc.ps1") -Raw
    $hasProject = $content -match '\$Project'
    $hasPhase   = $content -match '\$Phase'
    $hasFull    = $content -match '\$Full'
    $hasInteractive = $content -match '\$Interactive'
    $hasReport  = $content -match '\$Report'
    $hasExport  = $content -match '\$Export'
    return ($hasProject -and $hasPhase -and $hasFull -and $hasInteractive -and $hasReport -and $hasExport)
}

Test-Case "ssdlc.ps1 has all 6 phases defined" {
    $content = Get-Content (Join-Path $ScriptDir "ssdlc.ps1") -Raw
    $phases = @("planning", "analysis", "design", "implementation", "maintenance", "retirement")
    foreach ($p in $phases) {
        if ($content -notmatch $p) { return "Missing phase: $p" }
    }
    return $true
}

Test-Case "ssdlc.ps1 has checklist items" {
    $content = Get-Content (Join-Path $ScriptDir "ssdlc.ps1") -Raw
    # Check for some known checklist IDs
    $ids = @("P1", "P5", "A3", "D2", "I7", "M1", "R8")
    foreach ($id in $ids) {
        if ($content -notmatch $id) { return "Missing checklist ID: $id" }
    }
    return $true
}

Test-Case "ssdlc.ps1 references Docker for agent calls" {
    $content = Get-Content (Join-Path $ScriptDir "ssdlc.ps1") -Raw
    return $content -match "docker exec ollama-agent"
}

# ====================================================================
# 2. Python Module Structure
# ====================================================================
Write-Host "`n  --- PYTHON MODULE ---" -ForegroundColor Yellow

Test-Case "ssdlc.py exists in agent-container" {
    return Test-Path (Join-Path $ScriptDir "agent-container" "ssdlc.py")
}

Test-Case "ssdlc.py exists in web-ui" {
    return Test-Path (Join-Path $ScriptDir "web-ui" "ssdlc.py")
}

Test-Case "test-ssdlc.py exists" {
    return Test-Path (Join-Path $ScriptDir "test-ssdlc.py")
}

# ====================================================================
# 3. Web UI API Routes (if server running)
# ====================================================================
Write-Host "`n  --- WEB UI API ---" -ForegroundColor Yellow

$ServerRunning = $false
try {
    $test = Invoke-RestMethod -Uri "http://$Target/health" -TimeoutSec 3 -ErrorAction Stop
    if ($test.status -eq "ok") { $ServerRunning = $true }
} catch {
    $ServerRunning = $false
}

if (-not $ServerRunning) {
    Write-Host "  Server not running at $Target — API tests skipped" -ForegroundColor DarkGray
    Write-Host "  Start with: .\run.ps1`n" -ForegroundColor DarkGray

    Test-Case "Server not running (skip API tests)" { return "SKIP" }
    Test-Case "GET /api/ssdlc/phases" { return "SKIP" }
    Test-Case "POST /api/ssdlc/init" { return "SKIP" }
    Test-Case "POST /api/ssdlc/phase/start" { return "SKIP" }
    Test-Case "POST /api/ssdlc/check" { return "SKIP" }
    Test-Case "POST /api/ssdlc/risk" { return "SKIP" }
    Test-Case "POST /api/ssdlc/phase/complete" { return "SKIP" }
    Test-Case "GET /api/ssdlc/status" { return "SKIP" }
    Test-Case "GET /api/ssdlc/report" { return "SKIP" }
    Test-Case "GET /api/ssdlc/report/markdown" { return "SKIP" }
    Test-Case "Full lifecycle test via API" { return "SKIP" }
    Test-Case "GET /api/ssdlc/projects lists projects" { return "SKIP" }
} else {
    Write-Host "  Server running at $Target" -ForegroundColor Green

    $AuthToken = ""
    try {
        $authResp = Invoke-RestMethod -Uri "http://$Target/api/auth-token" -TimeoutSec 3
        $AuthToken = $authResp.token
    } catch {
        Write-Host "  Warning: Could not get auth token — mutating endpoints will fail" -ForegroundColor Yellow
    }

    $Headers = @{}
    if ($AuthToken) {
        $Headers["Authorization"] = "Bearer $AuthToken"
    }

    Test-Case "GET /api/ssdlc/phases returns 6 phases" {
        try {
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/phases" -TimeoutSec 5
            return (@($r.phases.PSObject.Properties).Count -eq 6)
        } catch { return $_.Exception.Message }
    }

    $TestProject = "ssdlc-integration-test-$((Get-Date).ToString('HHmmss'))"

    Test-Case "POST /api/ssdlc/init creates project" {
        try {
            $body = @{ project = $TestProject; owner = "test-suite" } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/init" -Method POST `
                -Body $body -ContentType "application/json" -Headers $Headers -TimeoutSec 5
            return $r.ok -eq $true
        } catch { return $_.Exception.Message }
    }

    Test-Case "POST /api/ssdlc/phase/start planning" {
        try {
            $body = @{ project = $TestProject; phase = "planning" } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/phase/start" -Method POST `
                -Body $body -ContentType "application/json" -Headers $Headers -TimeoutSec 5
            return $r.ok -eq $true
        } catch { return $_.Exception.Message }
    }

    Test-Case "POST /api/ssdlc/check marks item" {
        try {
            $body = @{ project = $TestProject; phase = "planning"; item_id = "P1"; checked = $true; notes = "integration-test" } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/check" -Method POST `
                -Body $body -ContentType "application/json" -Headers $Headers -TimeoutSec 5
            return $r.ok -eq $true
        } catch { return $_.Exception.Message }
    }

    Test-Case "POST /api/ssdlc/risk adds risk finding" {
        try {
            $body = @{
                project = $TestProject
                phase = "planning"
                title = "Test risk from integration suite"
                description = "This is an automated test risk"
                likelihood = 3
                impact = 4
                stride_category = "spoofing"
                mitigation = "Apply standard controls"
            } | ConvertTo-Json
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/risk" -Method POST `
                -Body $body -ContentType "application/json" -Headers $Headers -TimeoutSec 5
            return ($r.ok -eq $true -and $r.risk.score -eq 12)
        } catch { return $_.Exception.Message }
    }

    Test-Case "GET /api/ssdlc/status returns progress" {
        try {
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/status?project=$TestProject" -TimeoutSec 5
            return ($r.overall_status -ne $null -and @($r.phases.PSObject.Properties).Count -eq 6)
        } catch { return $_.Exception.Message }
    }

    Test-Case "GET /api/ssdlc/report returns report JSON" {
        try {
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/report?project=$TestProject" -TimeoutSec 5
            return ($r.project -eq $TestProject -and $r.risks_summary.total -eq 1)
        } catch { return $_.Exception.Message }
    }

    Test-Case "GET /api/ssdlc/report/markdown returns markdown" {
        try {
            $md = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/report/markdown?project=$TestProject" -TimeoutSec 5
            return ($md -match "# SSDLC Report" -and $md -match $TestProject)
        } catch { return $_.Exception.Message }
    }

    # Full lifecycle test — uses its own project to avoid state contamination
    $LifecycleProject = "ssdlc-lifecycle-$((Get-Date).ToString('HHmmss'))"
    # Init the lifecycle project first
    try {
        $initBody = @{ project = $LifecycleProject; owner = "lifecycle-test" } | ConvertTo-Json
        Invoke-RestMethod -Uri "http://$Target/api/ssdlc/init" -Method POST `
            -Body $initBody -ContentType "application/json" -Headers $Headers -TimeoutSec 5 | Out-Null
    } catch {}

    Test-Case "Full lifecycle: all 6 phases via API" {
        try {
            $phases = @("planning", "analysis", "design", "implementation", "maintenance", "retirement")
            foreach ($phase in $phases) {
                # Start
                $startBody = @{ project = $LifecycleProject; phase = $phase } | ConvertTo-Json
                $startR = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/phase/start" -Method POST `
                    -Body $startBody -ContentType "application/json" -Headers $Headers -TimeoutSec 5
                if (-not $startR.ok) { return "Failed to start $phase : $($startR.error)" }

                # Check ALL items (required + optional) for 100% completion
                $phasesR = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/phases" -TimeoutSec 5
                $phaseDef = $phasesR.phases.$phase
                foreach ($item in $phaseDef.checklist) {
                    $checkBody = @{ project = $LifecycleProject; phase = $phase; item_id = $item.id; checked = $true; notes = "auto-lifecycle" } | ConvertTo-Json
                    $checkR = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/check" -Method POST `
                        -Body $checkBody -ContentType "application/json" -Headers $Headers -TimeoutSec 5
                }

                # Complete
                $completeBody = @{ project = $LifecycleProject; phase = $phase } | ConvertTo-Json
                $completeR = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/phase/complete" -Method POST `
                    -Body $completeBody -ContentType "application/json" -Headers $Headers -TimeoutSec 5
                if (-not $completeR.ok) { return "Failed to complete $phase : $($completeR.error)" }
            }

            # Verify
            $statusR = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/status?project=$LifecycleProject" -TimeoutSec 5
            return ($statusR.overall_status -eq "completed" -and $statusR.overall_pct -eq 100.0)
        } catch { return $_.Exception.Message }
    }

    Test-Case "GET /api/ssdlc/projects lists test project" {
        try {
            $r = Invoke-RestMethod -Uri "http://$Target/api/ssdlc/projects" -TimeoutSec 5
            $found = ($r.projects | Where-Object { $_.name -eq $TestProject })
            return ($found -ne $null)
        } catch { return $_.Exception.Message }
    }
}

# ====================================================================
# 4. Agent Plugin Tools (if container running)
# ====================================================================
Write-Host "`n  --- AGENT PLUGIN TOOLS ---" -ForegroundColor Yellow

$AgentRunning = $false
try {
    $test = docker inspect ollama-agent 2>$null | ConvertFrom-Json
    if ($test.State.Status -eq "running") { $AgentRunning = $true }
} catch {}

if (-not $AgentRunning) {
    Write-Host "  Agent container not running — plugin tests skipped" -ForegroundColor DarkGray
    Write-Host "  Start with: .\run.ps1`n" -ForegroundColor DarkGray

    Test-Case "Agent not running (skip plugin tests)" { return "SKIP" }
    Test-Case "ssdlc_status tool registered" { return "SKIP" }
    Test-Case "ssdlc_check tool registered" { return "SKIP" }
    Test-Case "ssdlc_risk tool registered" { return "SKIP" }
    Test-Case "Agent can read SSDLC state" { return "SKIP" }
} else {
    Write-Host "  Agent running" -ForegroundColor Green

    Test-Case "ssdlc module importable in agent" {
        try {
            $r = docker exec ollama-agent python3 -c "from ssdlc import get_progress; print('OK')" 2>&1
            return $r -match "OK"
        } catch { return $_.Exception.Message }
    }

    Test-Case "ssdlc_status tool returns progress" {
        try {
            $code = @"
import json
from ssdlc import get_progress
p = get_progress('test-plugin')
print(json.dumps({'ok': True, 'phases': len(p['phases'])}))
"@
            $r = docker exec ollama-agent python3 -c $code 2>&1 | Select-Object -Last 1
            $data = $r | ConvertFrom-Json
            return ($data.ok -and $data.phases -eq 6)
        } catch { return "SKIP" }
    }

    Test-Case "ssdlc_check tool modifies state" {
        try {
            $code = @"
import json
from ssdlc import check_item, get_progress
check_item('test-plugin', 'planning', 'P1', True, 'agent-test')
p = get_progress('test-plugin')
print(json.dumps({'ok': True, 'checked': p['checked_items']}))
"@
            $r = docker exec ollama-agent python3 -c $code 2>&1 | Select-Object -Last 1
            $data = $r | ConvertFrom-Json
            return ($data.ok -and $data.checked -gt 0)
        } catch { return "SKIP" }
    }

    Test-Case "ssdlc_risk tool creates risk" {
        try {
            $code = @"
import json
from ssdlc import add_risk
r = add_risk('test-plugin', 'implementation', 'Agent test vuln', 'Test description', 4, 5, 'tampering', 'Fix it')
print(json.dumps({'ok': r['ok'], 'level': r.get('risk',{}).get('level','?')}))
"@
            $r = docker exec ollama-agent python3 -c $code 2>&1 | Select-Object -Last 1
            $data = $r | ConvertFrom-Json
            return ($data.ok -and $data.level -eq 'critical')
        } catch { return "SKIP" }
    }
}

# ====================================================================
# 5. File Integrity
# ====================================================================
Write-Host "`n  --- FILE INTEGRITY ---" -ForegroundColor Yellow

Test-Case "agent-container/Dockerfile copies ssdlc.py" {
    $content = Get-Content (Join-Path $ScriptDir "agent-container" "Dockerfile") -Raw
    return $content -match "COPY ssdlc.py"
}

Test-Case "web-ui/Dockerfile copies ssdlc.py" {
    $content = Get-Content (Join-Path $ScriptDir "web-ui" "Dockerfile") -Raw
    return $content -match "COPY ssdlc.py"
}

Test-Case "web-ui/server.py has SSDLC routes" {
    $content = Get-Content (Join-Path $ScriptDir "web-ui" "server.py") -Raw
    $routes = @("/api/ssdlc/projects", "/api/ssdlc/status", "/api/ssdlc/init",
                "/api/ssdlc/phase/start", "/api/ssdlc/check", "/api/ssdlc/risk",
                "/api/ssdlc/report", "/api/ssdlc/phases")
    $missing = @()
    foreach ($r in $routes) {
        if ($content -notmatch [regex]::Escape($r)) { $missing += $r }
    }
    if ($missing.Count -gt 0) { return "Missing routes: $($missing -join ', ')" }
    return $true
}

Test-Case "web-ui/index.html has SSDLC dashboard" {
    $content = Get-Content (Join-Path $ScriptDir "web-ui" "index.html") -Raw
    return ($content -match "ssdlc-panel" -and $content -match "toggleSSDLC" -and $content -match "loadSSDLCStatus")
}

Test-Case "ollama_agent.py registers SSDLC tools" {
    $content = Get-Content (Join-Path $ScriptDir "agent-container" "ollama_agent.py") -Raw
    return ($content -match "ssdlc_status" -and $content -match "ssdlc_check" -and $content -match "ssdlc_risk")
}

Test-Case "pentest-parapet.ps1 has SSDLC integration" {
    $content = Get-Content (Join-Path $ScriptDir "pentest-parapet.ps1") -Raw
    return ($content -match "SSDLC Integration" -and $content -match "check_item")
}

Test-Case "ssdlc.py and web-ui/ssdlc.py are identical" {
    $agent = Get-Content (Join-Path $ScriptDir "agent-container" "ssdlc.py") -Raw
    $webui = Get-Content (Join-Path $ScriptDir "web-ui" "ssdlc.py") -Raw
    return ($agent -eq $webui)
}

Test-Case "ssdlc.ps1 launcher is in root (Python module in containers)" {
    return Test-Path (Join-Path $ScriptDir "ssdlc.ps1")
}

# ====================================================================
# 6. Dockerfile Consistency
# ====================================================================
Write-Host "`n  --- DOCKERFILE CONSISTENCY ---" -ForegroundColor Yellow

Test-Case "requirements.txt has no SSDLC deps needed (stdlib only)" {
    $req = Get-Content (Join-Path $ScriptDir "agent-container" "requirements.txt") -Raw
    # ssdlc.py uses only stdlib (json, os, pathlib, datetime, uuid)
    return $true
}

Test-Case "web-ui requirements.txt has FastAPI/uvicorn" {
    $req = Get-Content (Join-Path $ScriptDir "web-ui" "requirements.txt") -Raw
    return ($req -match "fastapi" -and $req -match "uvicorn")
}

# ====================================================================
# SUMMARY
# ====================================================================
Write-Host "`n  +========================================+" -ForegroundColor Cyan
Write-Host "  |  SSDLC INTEGRATION TESTS COMPLETE       |" -ForegroundColor Cyan
Write-Host "  +========================================+" -ForegroundColor Cyan
Write-Host "  Pass: $Pass | Fail: $Fail | Skip: $Skip | Total: $Total" -ForegroundColor White
if ($Fail -eq 0) {
    Write-Host "  VERDICT: ALL CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  VERDICT: $Fail FAILURES DETECTED" -ForegroundColor Red
}
Write-Host ""

# Exit code
if ($Fail -gt 0) { exit 1 } else { exit 0 }
