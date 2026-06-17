$ErrorActionPreference = "Stop"
if (-not $env:GAME_COMPANY_SERVER) {
    $env:GAME_COMPANY_SERVER = "http://127.0.0.1:8080"
}
if (-not $env:SDL_VIDEODRIVER) { $env:SDL_VIDEODRIVER = "dummy" }
if (-not $env:SDL_AUDIODRIVER) { $env:SDL_AUDIODRIVER = "dummy" }
python -m app.test_runner_worker @args
