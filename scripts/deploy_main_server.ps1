param(
    [string]$Target = "powerpunch@100.92.73.19",
    [string]$InstallDir = "/home/powerpunch/ai-game-company-server"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$env:Path = "C:\Program Files\Git\cmd;C:\Program Files\GitHub CLI;" + $env:Path

function New-ApiToken {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    }
    finally {
        $rng.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function Get-RemoteEnvValue {
    param([string]$Name)
    $value = ssh $Target "if [ -f '$InstallDir/.env' ]; then sed -n 's/^$Name=//p' '$InstallDir/.env' | head -n 1; fi" 2>$null
    if ($value) {
        $clean = $value.Trim()
        if (($clean.StartsWith('"') -and $clean.EndsWith('"')) -or ($clean.StartsWith("'") -and $clean.EndsWith("'"))) {
            return $clean.Substring(1, $clean.Length - 2)
        }
        return $clean
    }
    return ""
}

function Convert-ToEnvValue {
    param([string]$Value)
    $escaped = $Value.Replace("\", "\\")
    $escaped = $escaped.Replace('"', '\"')
    $escaped = $escaped.Replace('$', '\$')
    return '"' + $escaped + '"'
}

$existingToken = Get-RemoteEnvValue "GAME_COMPANY_API_TOKEN"
$apiToken = if ($existingToken) { $existingToken.Trim() } else { New-ApiToken }
$ownerCommand = Get-RemoteEnvValue "GAME_COMPANY_OWNER_COMMAND"
$workerApiBaseUrl = Get-RemoteEnvValue "GAME_COMPANY_WORKER_API_BASE_URL"
$workerApiKey = Get-RemoteEnvValue "GAME_COMPANY_WORKER_API_KEY"
$workerModel = Get-RemoteEnvValue "GAME_COMPANY_WORKER_MODEL"
$workerTimeout = Get-RemoteEnvValue "GAME_COMPANY_WORKER_TIMEOUT_SECONDS"
$workerTemperature = Get-RemoteEnvValue "GAME_COMPANY_WORKER_TEMPERATURE"

if (-not $workerApiBaseUrl) { $workerApiBaseUrl = "https://api.openai.com/v1" }
if (-not $workerTimeout) { $workerTimeout = "120" }
if (-not $workerTemperature) { $workerTemperature = "0.2" }
$tmpEnv = New-TemporaryFile
$tmpArchive = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-game-company-server-" + [System.Guid]::NewGuid().ToString("N") + ".tar.gz")
$remoteArchive = "/tmp/ai-game-company-server.tar.gz"

$envContent = @"
GAME_COMPANY_DB_PATH=$(Convert-ToEnvValue "$InstallDir/data/game_company.sqlite3")
GAME_COMPANY_HOST=$(Convert-ToEnvValue "0.0.0.0")
GAME_COMPANY_PORT=$(Convert-ToEnvValue "8080")
GAME_COMPANY_DEFAULT_TASK_MINUTES=$(Convert-ToEnvValue "15")
GAME_COMPANY_OWNER_RECALL_MINUTES=$(Convert-ToEnvValue "30")
GAME_COMPANY_API_TOKEN=$(Convert-ToEnvValue $apiToken)
GAME_COMPANY_BACKUP_DIR=$(Convert-ToEnvValue "$InstallDir/backups")
GAME_COMPANY_OWNER_COMMAND=$(Convert-ToEnvValue $ownerCommand)
GAME_COMPANY_OWNER_TIMEOUT_SECONDS=$(Convert-ToEnvValue "900")
GAME_COMPANY_OWNER_RUNS_DIR=$(Convert-ToEnvValue "$InstallDir/owner-runs")
GAME_COMPANY_WORKER_API_BASE_URL=$(Convert-ToEnvValue $workerApiBaseUrl)
GAME_COMPANY_WORKER_API_KEY=$(Convert-ToEnvValue $workerApiKey)
GAME_COMPANY_WORKER_MODEL=$(Convert-ToEnvValue $workerModel)
GAME_COMPANY_WORKER_TIMEOUT_SECONDS=$(Convert-ToEnvValue $workerTimeout)
GAME_COMPANY_WORKER_TEMPERATURE=$(Convert-ToEnvValue $workerTemperature)
"@
[System.IO.File]::WriteAllText($tmpEnv, $envContent, [System.Text.UTF8Encoding]::new($false))

ssh $Target "command -v git >/dev/null && command -v python3 >/dev/null && python3 -m venv --help >/dev/null"
ssh $Target "mkdir -p '$InstallDir'"
git archive --format=tar.gz -o $tmpArchive HEAD
scp $tmpArchive "$Target`:$remoteArchive"
Remove-Item -LiteralPath $tmpArchive -Force
ssh $Target "rm -rf '$InstallDir/.deploy_tmp' && mkdir -p '$InstallDir/.deploy_tmp' && tar -xzf '$remoteArchive' -C '$InstallDir/.deploy_tmp' && find '$InstallDir' -mindepth 1 -maxdepth 1 ! -name data ! -name backups ! -name .env ! -name .deploy_tmp -exec rm -rf {} + && cp -a '$InstallDir/.deploy_tmp/.' '$InstallDir/' && rm -rf '$InstallDir/.deploy_tmp' '$remoteArchive'"
scp $tmpEnv "$Target`:$InstallDir/.env"
Remove-Item -LiteralPath $tmpEnv -Force

$setupCommand = @"
cd '$InstallDir' &&
sed -i 's/\r$//' scripts/*.sh &&
chmod +x scripts/*.sh &&
if ! command -v uv >/dev/null 2>&1 && [ ! -x "`$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi &&
UV_BIN="`$(command -v uv || echo "`$HOME/.local/bin/uv")" &&
"`$UV_BIN" venv --clear .venv &&
"`$UV_BIN" pip install -r requirements.txt &&
if [ ! -f data/game_company.sqlite3 ]; then .venv/bin/python -m app.seed; fi
"@
ssh $Target $setupCommand

Write-Host "Deployed to $Target`:$InstallDir"
Write-Host "External API URL: http://100.92.73.19:8080"
Write-Host "API token: $apiToken"
Write-Host "Start server: ssh $Target 'cd $InstallDir && ./scripts/start_server.sh'"
