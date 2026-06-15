$ErrorActionPreference = "Stop"
if (-not $env:GAME_COMPANY_SERVER) {
    $env:GAME_COMPANY_SERVER = "http://127.0.0.1:8080"
}
python -m app.test_runner_worker @args
