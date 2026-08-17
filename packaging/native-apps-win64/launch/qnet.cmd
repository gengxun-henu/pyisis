@echo off
setlocal DisableDelayedExpansion
set "ISIS_LAUNCH_WORKER=%~dp0isis-launch.ps1"
set "ISIS_LAUNCH_ARG_0=qnet"
set "ISIS_LAUNCH_ARG_COUNT=1"

:capture_argument
set ISIS_LAUNCH_ARG_PRESENT=%1
if not defined ISIS_LAUNCH_ARG_PRESENT goto launch
set "ISIS_LAUNCH_ARG_%ISIS_LAUNCH_ARG_COUNT%=%~1"
set /a ISIS_LAUNCH_ARG_COUNT+=1 >nul
shift
goto capture_argument

:launch
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%ISIS_LAUNCH_WORKER%"
set "ISIS_LAUNCH_EXIT=%ERRORLEVEL%"
endlocal & exit /b %ISIS_LAUNCH_EXIT%
