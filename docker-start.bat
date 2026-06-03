@echo off
REM SpeechScribe Docker Startup Script (Windows CMD)
REM Both dev and prod run on port 8088 — only one mode at a time.

setlocal enabledelayedexpansion

set MODE=prod
set BUILD_FLAG=

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_args
if "%~1"=="--dev"       set MODE=dev& shift & goto :parse_args
if "%~1"=="--prod"      set MODE=prod& shift & goto :parse_args
if "%~1"=="--build"     set BUILD_FLAG=--build& shift & goto :parse_args
if "%~1"=="--stop"      goto :do_stop
if "%~1"=="--help"      goto :show_help
if "%~1"=="-h"          goto :show_help
echo Unknown option: %~1 (use --help for usage)
exit /b 1

:done_args

echo Starting SpeechScribe (%MODE%) on port 8088...

REM Check if .env exists
if not exist .env (
    echo ERROR: .env not found!
    echo   1. copy .env.example .env
    echo   2. Add your OPENAI_API_KEY
    echo   3. Update JWT_SECRET_KEY for production
    exit /b 1
)

REM Ensure appdata directory exists
if not exist appdata mkdir appdata

if "%MODE%"=="dev" (
    docker compose rm -sf nginx-prod 2>nul
    docker compose --profile dev up -d %BUILD_FLAG% backend frontend nginx
) else (
    docker compose --profile dev rm -sf nginx frontend 2>nul

    REM Build frontend to ./www if needed
    if "%BUILD_FLAG%"=="--build" goto :do_build
    if not exist www\index.html goto :do_build
    goto :skip_build

    :do_build
    echo Building frontend to ./www ...
    docker compose --profile dev run --rm -e NEXT_PUBLIC_API_URL=http://localhost:8088/api frontend sh -c "cd /app && rm -rf .next out && npx next build"
    if exist www rmdir /s /q www
    xcopy /e /i /q frontend\out www
    echo Frontend built to ./www/

    :skip_build
    docker compose up -d %BUILD_FLAG% backend nginx-prod
)

echo.
docker compose ps
echo.
echo =========================================
echo  SpeechScribe is running! (%MODE%)
echo  http://localhost:8088
echo =========================================
echo.
echo  Logs:    docker compose logs -f
echo  Stop:    docker-start.bat --stop
echo  Rebuild: docker-start.bat --%MODE% --build
exit /b 0

:do_stop
echo Stopping all SpeechScribe services...
docker compose --profile dev down
echo All services stopped.
exit /b 0

:show_help
echo SpeechScribe Docker Startup
echo.
echo Usage: docker-start.bat [OPTIONS]
echo.
echo Options:
echo   --dev        Start dev environment (HMR, live-reload)
echo   --prod       Start production build (default)
echo                Builds frontend to ./www, served by nginx
echo   --build      Force rebuild (frontend + Docker images)
echo   --stop       Stop all running services
echo   --help       Show this help message
echo.
echo Both modes run on http://localhost:8088
echo Only one mode can run at a time.
exit /b 0
