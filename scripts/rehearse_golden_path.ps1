# PowerShell script for AI Game Company Server v1 Golden Path Rehearsal
# Validates the full loop: scaffold -> seed -> server -> worker -> test -> artifact -> merge

$ProjectRoot = [System.IO.Path]::GetFullPath("$PSScriptRoot\..")
$RehearsalDir = Join-Path $ProjectRoot "rehearsal"

$DbPath = Join-Path $RehearsalDir "rehearsal.db"
$BareRepoPath = Join-Path $RehearsalDir "demo-game.git"
$DevWorkspacePath = Join-Path $RehearsalDir "workspace-dev"
$TestWorkspacePath = Join-Path $RehearsalDir "workspace-test"
$RunsDir = Join-Path $RehearsalDir "runs"
$ArtifactRoot = Join-Path $RehearsalDir "server-artifacts"
$WorkerScript = Join-Path $RehearsalDir "modify_code.py"

function Run-Git {
    param([string[]]$Arguments, [string]$WorkDir = $null)
    # Use .NET Process to avoid PowerShell converting git's stderr into ErrorRecords.
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "git"
    if ($WorkDir) {
        $psi.Arguments = "-C `"$WorkDir`" $($Arguments | ForEach-Object { if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ } })"
    } else {
        $psi.Arguments = ($Arguments | ForEach-Object { if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ } })
    }
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    if ($WorkDir -and -not $Arguments[0].StartsWith("-C")) {
        # WorkDir is already handled via -C flag
    }
    $proc = [System.Diagnostics.Process]::Start($psi)
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit $($proc.ExitCode)): $stdout $stderr"
    }
    return ($stdout + $stderr).Trim()
}

function Run-Python {
    param([string[]]$Arguments)
    & python @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "python $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
}

Write-Host "=================================================="
Write-Host "STARTING GOLDEN PATH REHEARSAL"
Write-Host "Rehearsal directory: $RehearsalDir"
Write-Host "=================================================="

# ---- 1. Cleanup and directory creation ----
if (Test-Path $RehearsalDir) {
    Write-Host "[1/13] Cleaning up existing rehearsal directory..."
    Remove-Item -Recurse -Force $RehearsalDir
}
New-Item -ItemType Directory -Force $RehearsalDir | Out-Null
New-Item -ItemType Directory -Force $RunsDir | Out-Null

# ---- 2. Setup bare repository ----
Write-Host "[2/13] Initializing bare repository..."
Run-Git @("init", "--bare", $BareRepoPath)
Run-Git @("symbolic-ref", "HEAD", "refs/heads/main") -WorkDir $BareRepoPath

# ---- 3. Scaffold project template and push to bare repo ----
$TempSeed = Join-Path $RehearsalDir "temp-seed"
Write-Host "[3/13] Scaffolding game-pygame-mini template..."
Run-Git @("clone", "--quiet", $BareRepoPath, $TempSeed)
Run-Git @("config", "user.email", "ai-game-company@example.local") -WorkDir $TempSeed
Run-Git @("config", "user.name", "AI Game Company") -WorkDir $TempSeed

Run-Python @("-m", "app.project_template", $TempSeed, "--name", "AI Survival Mini", "--type", "game-pygame-mini", "--force")

Run-Git @("add", ".") -WorkDir $TempSeed
Run-Git @("commit", "--quiet", "-m", "Initial game-pygame-mini template scaffold") -WorkDir $TempSeed
Run-Git @("push", "--quiet", "-u", "origin", "main") -WorkDir $TempSeed
Remove-Item -Recurse -Force $TempSeed

# ---- 4. Clone dev and test workspaces ----
Write-Host "[4/13] Cloning dev and test workspaces..."
Run-Git @("clone", "--quiet", $BareRepoPath, $DevWorkspacePath)
Run-Git @("config", "user.email", "ai-game-company-worker@example.local") -WorkDir $DevWorkspacePath
Run-Git @("config", "user.name", "AI Game Company Worker") -WorkDir $DevWorkspacePath

Run-Git @("clone", "--quiet", $BareRepoPath, $TestWorkspacePath)
Run-Git @("config", "user.email", "ai-game-company-test@example.local") -WorkDir $TestWorkspacePath
Run-Git @("config", "user.name", "AI Game Company Test") -WorkDir $TestWorkspacePath

# ---- 5. Seed database BEFORE starting the server ----
Write-Host "[5/13] Seeding rehearsal database..."
$env:PYTHONPATH = $ProjectRoot
Run-Python @("$PSScriptRoot\rehearsal_seed.py", "--db-path", $DbPath, "--repo-url", $BareRepoPath, "--workspace-path", $DevWorkspacePath)

# ---- 6. Create the worker modification script ----
Write-Host "[6/13] Creating worker modification script..."
@"
import pathlib
p = pathlib.Path('src/ai_survival_mini/game_state.py')
content = p.read_text(encoding='utf-8')
content = content.replace('speed: float = 220.0', 'speed: float = 250.0')
p.write_text(content, encoding='utf-8')
print('Modified player speed from 220.0 to 250.0')
"@ | Set-Content -Path $WorkerScript -Encoding utf8

# ---- 7. Set up server environment and start server ----
Write-Host "[7/13] Starting FastAPI server on port 8082..."
$env:GAME_COMPANY_DB_PATH = $DbPath
$env:GAME_COMPANY_HOST = "127.0.0.1"
$env:GAME_COMPANY_PORT = "8082"
$env:GAME_COMPANY_API_TOKEN = ""
$env:GAME_COMPANY_OWNER_TOKEN = ""
$env:GAME_COMPANY_WORKER_TOKEN = ""
$env:GAME_COMPANY_READONLY_TOKEN = ""
$env:GAME_COMPANY_ARTIFACT_TOKEN = ""
$env:GAME_COMPANY_SERVER = "http://127.0.0.1:8082"
$env:GAME_COMPANY_ARTIFACT_ROOT = $ArtifactRoot

$ServerProcess = $null

try {
    $ServerProcess = Start-Process python -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8082" -PassThru -NoNewWindow
    Write-Host "  Server PID: $($ServerProcess.Id). Waiting for boot..."
    Start-Sleep -Seconds 5

    # Health check with retry
    $retries = 0
    while ($retries -lt 5) {
        try {
            $Health = Invoke-RestMethod -Uri "http://127.0.0.1:8082/health" -TimeoutSec 3
            break
        } catch {
            $retries++
            if ($retries -ge 5) { throw "Server health check failed after 5 retries" }
            Start-Sleep -Seconds 2
        }
    }
    Write-Host "  Server Health: OK"

    # Verify seed data
    $Tasks = Invoke-RestMethod -Uri "http://127.0.0.1:8082/tasks"
    Write-Host "  Tasks in DB: $($Tasks.Count)"
    if ($Tasks.Count -eq 0) { throw "No tasks found after seeding" }

    # ---- 8. Run Workspace Worker ----
    Write-Host "[8/13] Running Workspace Worker (lease, modify, commit, push)..."
    Run-Python @("-m", "app.workspace_worker",
        "--server", "http://127.0.0.1:8082",
        "--worker-id", "code-worker-1",
        "--role", "code_worker",
        "--runs-dir", "$RunsDir\workspace-worker",
        "--command", "python $WorkerScript",
        "--push")

    # Verify worker branch was pushed
    $Branches = Run-Git @("branch") -WorkDir $BareRepoPath
    Write-Host "  Bare repo branches: $Branches"

    # ---- 9. Run Test Runner against worker branch ----
    Write-Host "[9/13] Running Test Runner against worker branch..."
    # Fetch and checkout the worker branch in the test workspace
    Run-Git @("fetch", "--quiet", "origin") -WorkDir $TestWorkspacePath
    Run-Git @("checkout", "worker/player-movement-stub") -WorkDir $TestWorkspacePath

    # Run test runner locally (no server interaction needed)
    Run-Python @("-m", "app.test_runner",
        "--package", "$RunsDir\workspace-worker\workspace-task-1\task_package.json",
        "--workspace", $TestWorkspacePath)
    Write-Host "  Test Runner completed successfully."

    # ---- 10. Locate test runner report ----
    Write-Host "[10/13] Locating test runner report..."
    $ReportFile = Get-ChildItem -Path "$TestWorkspacePath\.game-company\artifacts\task-1" -Filter "test-runner-report.json" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $ReportFile) {
        throw "Test runner report not found under $TestWorkspacePath\.game-company\artifacts\task-1"
    }
    Write-Host "  Found: $($ReportFile.FullName)"
    $ReportContent = Get-Content $ReportFile.FullName -Raw | ConvertFrom-Json
    Write-Host "  Report status: $($ReportContent.status)"

    # ---- 11. Register and upload artifact ----
    Write-Host "[11/13] Registering and uploading artifact..."
    $ArtifactPayload = @{
        artifact_id    = "rehearsal-smoke-report"
        project_id     = 1
        task_id        = 1
        worker_id      = "test-runner-1"
        machine_id     = "rehearsal_machine"
        artifact_type  = "test_report"
        filename       = "test-runner-report.json"
        content_type   = "application/json"
        summary        = "Rehearsal test runner execution report."
        tags           = @("rehearsal", "test-runner", "smoke")
        important      = $true
    } | ConvertTo-Json -Depth 5

    Invoke-RestMethod -Uri "http://127.0.0.1:8082/artifacts" -Method Post -Body $ArtifactPayload -ContentType "application/json" | Out-Null
    Write-Host "  Artifact metadata registered."

    $UploadUri = "http://127.0.0.1:8082/artifacts/rehearsal-smoke-report/content?filename=test-runner-report.json&content_type=application/json"
    $FileContentBytes = [System.IO.File]::ReadAllBytes($ReportFile.FullName)
    Invoke-RestMethod -Uri $UploadUri -Method Put -Body $FileContentBytes -ContentType "application/json" | Out-Null
    Write-Host "  Artifact content uploaded."

    # ---- 12. Check merge candidates and merge ----
    Write-Host "[12/13] Checking merge candidates and merging..."
    $Candidates = Invoke-RestMethod -Uri "http://127.0.0.1:8082/owner/merge-candidates"
    Write-Host "  Merge candidates: $($Candidates.Count)"

    $MergeStatus = "skipped"
    if ($Candidates.Count -gt 0) {
        $MergePayload = @{ dry_run = $false; push = $true } | ConvertTo-Json
        $MergeResult = Invoke-RestMethod -Uri "http://127.0.0.1:8082/owner/tasks/1/merge" -Method Post -Body $MergePayload -ContentType "application/json"
        $MergeStatus = $MergeResult.status
        Write-Host "  Merge result: $MergeStatus"
    } else {
        $Task = Invoke-RestMethod -Uri "http://127.0.0.1:8082/tasks/1"
        Write-Host "  Task status: $($Task.status) (no merge candidates - task already completed)"
    }

    # ---- 13. Final verification ----
    Write-Host "[13/13] Final verification..."
    $GitLog = Run-Git @("log", "-n", "5", "--oneline") -WorkDir $BareRepoPath
    Write-Host "  Git log (bare repo):"
    $GitLog -split "`n" | ForEach-Object { Write-Host "    $_" }

    $Dashboard = Invoke-RestMethod -Uri "http://127.0.0.1:8082/owner/dashboard"
    Write-Host "  Dashboard success count: $($Dashboard.counts.success)"

    $Artifacts = Invoke-RestMethod -Uri "http://127.0.0.1:8082/artifacts?project_id=1&important=true"
    Write-Host "  Important artifacts: $($Artifacts.Count)"

    Write-Host ""
    Write-Host "=================================================="
    Write-Host "GOLDEN PATH REHEARSAL COMPLETED SUCCESSFULLY!"
    Write-Host "=================================================="
    Write-Host ""
    Write-Host "What was validated:"
    Write-Host "  [OK] Project scaffold (game-pygame-mini)"
    Write-Host "  [OK] Database seeding (project, epic, sub-epic, task)"
    Write-Host "  [OK] FastAPI server startup and health check"
    Write-Host "  [OK] Workspace Worker: lease, modify, commit, push"
    Write-Host "  [OK] Test Runner: build, test, smoke phases"
    Write-Host "  [OK] Artifact: register metadata and upload content"
    if ($MergeStatus -eq "merged") {
        Write-Host "  [OK] Owner merge: worker branch merged into main"
    }
    Write-Host ""

} finally {
    if ($null -ne $ServerProcess -and !$ServerProcess.HasExited) {
        Write-Host "Stopping FastAPI server (PID $($ServerProcess.Id))..."
        Stop-Process -Id $ServerProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
