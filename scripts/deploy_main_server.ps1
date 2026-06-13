param(
    [string]$Target = "powerpunch@100.92.73.19",
    [string]$InstallDir = "/srv/ai-game-company-server",
    [string]$RepoUrl = "https://github.com/powerpunch080403/ai-game-company-server.git"
)

$ErrorActionPreference = "Stop"

function New-ApiToken {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$existingToken = ssh $Target "if [ -f '$InstallDir/.env' ]; then sed -n 's/^GAME_COMPANY_API_TOKEN=//p' '$InstallDir/.env' | head -n 1; fi" 2>$null
$apiToken = if ($existingToken) { $existingToken.Trim() } else { New-ApiToken }
$tmpEnv = New-TemporaryFile

@"
GAME_COMPANY_DB_PATH=$InstallDir/data/game_company.sqlite3
GAME_COMPANY_HOST=0.0.0.0
GAME_COMPANY_PORT=8080
GAME_COMPANY_DEFAULT_TASK_MINUTES=15
GAME_COMPANY_OWNER_RECALL_MINUTES=30
GAME_COMPANY_API_TOKEN=$apiToken
GAME_COMPANY_BACKUP_DIR=$InstallDir/backups
"@ | Set-Content -LiteralPath $tmpEnv -Encoding UTF8

ssh $Target "sudo apt-get update && sudo apt-get install -y git python3-venv python3-pip sqlite3"
ssh $Target "sudo mkdir -p '$InstallDir' && sudo chown `$(id -un):`$(id -gn) '$InstallDir'"
ssh $Target "if [ -d '$InstallDir/.git' ]; then cd '$InstallDir' && git pull --ff-only; else rm -rf '$InstallDir'/* && git clone '$RepoUrl' '$InstallDir'; fi"
scp $tmpEnv "$Target`:$InstallDir/.env"
Remove-Item -LiteralPath $tmpEnv -Force

ssh $Target "cd '$InstallDir' && chmod +x scripts/*.sh && python3 -m venv .venv && . .venv/bin/activate && python -m pip install --upgrade pip && python -m pip install -r requirements.txt && if [ ! -f data/game_company.sqlite3 ]; then python -m app.seed; fi"

Write-Host "Deployed to $Target`:$InstallDir"
Write-Host "External API URL: http://100.92.73.19:8080"
Write-Host "API token: $apiToken"
Write-Host "Start server: ssh $Target 'cd $InstallDir && ./scripts/start_server.sh'"
