$ErrorActionPreference = "Stop"
if ($args.Count -lt 1) {
    throw "Usage: .\scripts\check_remote.ps1 user@host"
}

$hostTarget = $args[0]
ssh $hostTarget 'set -e; hostname; uname -a; command -v git; command -v python3'
