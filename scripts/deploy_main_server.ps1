param(
    [string]$Target = "powerpunch@100.92.73.19",
    [string]$InstallDir = "/home/powerpunch/ai-game-company-server"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

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

$existingToken = ssh $Target "if [ -f '$InstallDir/.env' ]; then sed -n 's/^GAME_COMPANY_API_TOKEN=//p' '$InstallDir/.env' | head -n 1; fi" 2>$null
$apiToken = if ($existingToken) { $existingToken.Trim() } else { New-ApiToken }
$tmpEnv = New-TemporaryFile
$tmpArchive = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-game-company-server-" + [System.Guid]::NewGuid().ToString("N") + ".tar.gz")
$remoteArchive = "/tmp/ai-game-company-server.tar.gz"

@"
GAME_COMPANY_DB_PATH=$InstallDir/data/game_company.sqlite3
GAME_COMPANY_HOST=0.0.0.0
GAME_COMPANY_PORT=8080
GAME_COMPANY_DEFAULT_TASK_MINUTES=15
GAME_COMPANY_OWNER_RECALL_MINUTES=30
GAME_COMPANY_API_TOKEN=$apiToken
GAME_COMPANY_BACKUP_DIR=$InstallDir/backups
"@ | Set-Content -LiteralPath $tmpEnv -Encoding UTF8

ssh $Target "command -v git >/dev/null && command -v python3 >/dev/null && python3 -m venv --help >/dev/null"
ssh $Target "mkdir -p '$InstallDir'"
git archive --format=tar.gz -o $tmpArchive HEAD
scp $tmpArchive "$Target`:$remoteArchive"
Remove-Item -LiteralPath $tmpArchive -Force
ssh $Target "rm -rf '$InstallDir/.deploy_tmp' && mkdir -p '$InstallDir/.deploy_tmp' && tar -xzf '$remoteArchive' -C '$InstallDir/.deploy_tmp' && find '$InstallDir' -mindepth 1 -maxdepth 1 ! -name data ! -name backups ! -name .env ! -name .deploy_tmp -exec rm -rf {} + && cp -a '$InstallDir/.deploy_tmp/.' '$InstallDir/' && rm -rf '$InstallDir/.deploy_tmp' '$remoteArchive'"
scp $tmpEnv "$Target`:$InstallDir/.env"
Remove-Item -LiteralPath $tmpEnv -Force

ssh $Target "cd '$InstallDir' && chmod +x scripts/*.sh && python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt && if [ ! -f data/game_company.sqlite3 ]; then python -m app.seed; fi"

Write-Host "Deployed to $Target`:$InstallDir"
Write-Host "External API URL: http://100.92.73.19:8080"
Write-Host "API token: $apiToken"
Write-Host "Start server: ssh $Target 'cd $InstallDir && ./scripts/start_server.sh'"
