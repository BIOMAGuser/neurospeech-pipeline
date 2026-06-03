# SpeechScribe Docker Startup Script (PowerShell)
# Both dev and prod run on port 8088 — only one mode at a time.

param(
    [ValidateSet("dev", "prod")]
    [string]$Mode = "prod",
    [switch]$Build,
    [switch]$Stop,
    [switch]$Help
)

if ($Help) {
    Write-Host "SpeechScribe Docker Startup" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker-start.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Mode dev    Start dev environment (HMR, live-reload)"
    Write-Host "  -Mode prod   Start production build (default)"
    Write-Host "               Builds frontend to ./www, served by nginx"
    Write-Host "  -Build       Force rebuild (frontend + Docker images)"
    Write-Host "  -Stop        Stop all running services"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "Both modes run on http://localhost:8088"
    Write-Host "Only one mode can run at a time."
    exit 0
}

if ($Stop) {
    Write-Host "Stopping all SpeechScribe services..." -ForegroundColor Yellow
    docker compose --profile dev down
    Write-Host "All services stopped." -ForegroundColor Green
    exit 0
}

Write-Host "Starting SpeechScribe ($Mode) on port 8088..." -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "ERROR: .env not found!" -ForegroundColor Red
    Write-Host "  1. Copy-Item .env.example .env"
    Write-Host "  2. Add your OPENAI_API_KEY"
    Write-Host "  3. Update JWT_SECRET_KEY for production"
    exit 1
}

# Ensure appdata directory exists
if (-not (Test-Path appdata)) {
    New-Item -ItemType Directory -Path appdata | Out-Null
}

$buildArg = if ($Build) { @("--build") } else { @() }

if ($Mode -eq "dev") {
    docker compose rm -sf nginx-prod 2>$null
    $allArgs = @("compose", "--profile", "dev", "up", "-d") + $buildArg + @("backend", "frontend", "nginx")
    & docker @allArgs
}
else {
    docker compose --profile dev rm -sf nginx frontend 2>$null

    # Build frontend to ./www if needed
    if ($Build -or -not (Test-Path "www/index.html")) {
        Write-Host "Building frontend to ./www ..." -ForegroundColor Yellow
        docker compose --profile dev run --rm `
            -e NEXT_PUBLIC_API_URL=http://localhost:8088/api `
            -e NEXT_PUBLIC_APP_NAME="$(if ($env:APP_NAME) { $env:APP_NAME } else { 'PARK_SPEECH' })" `
            -e NEXT_PUBLIC_APP_VERSION="$(if ($env:APP_VERSION) { $env:APP_VERSION } else { '3.0.0' })" `
            frontend sh -c "cd /app && rm -rf .next out && npx next build"
        if (Test-Path www) { Remove-Item -Recurse -Force www }
        Copy-Item -Recurse frontend/out www
        Write-Host "Frontend built to ./www/" -ForegroundColor Green
    }

    # Start backend + nginx
    $allArgs = @("compose", "up", "-d") + $buildArg + @("backend", "nginx-prod")
    & docker @allArgs
}

Write-Host ""
docker compose ps
Write-Host ""
Write-Host "=========================================" -ForegroundColor Green
Write-Host " SpeechScribe is running! ($Mode)" -ForegroundColor Green
Write-Host " http://localhost:8088" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""
Write-Host " Logs:    docker compose logs -f" -ForegroundColor DarkGray
Write-Host " Stop:    .\docker-start.ps1 -Stop" -ForegroundColor DarkGray
Write-Host " Rebuild: .\docker-start.ps1 -Mode $Mode -Build" -ForegroundColor DarkGray
