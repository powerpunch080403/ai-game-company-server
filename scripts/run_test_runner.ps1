$ErrorActionPreference = "Stop"
if (-not $env:SDL_VIDEODRIVER) { $env:SDL_VIDEODRIVER = "dummy" }
if (-not $env:SDL_AUDIODRIVER) { $env:SDL_AUDIODRIVER = "dummy" }
python -m app.test_runner @args
