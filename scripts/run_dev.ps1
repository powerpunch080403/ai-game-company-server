$ErrorActionPreference = "Stop"
if (-not $env:GAME_COMPANY_DB_PATH) {
    $env:GAME_COMPANY_DB_PATH = "./data/game_company.sqlite3"
}
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
