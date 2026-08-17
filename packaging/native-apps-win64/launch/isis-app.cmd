@echo off
setlocal DisableDelayedExpansion
set "ISIS_LAUNCH_DIR=%~dp0"
set "ISIS_LAUNCH_ARG_COUNT=0"

:capture_argument
set ISIS_LAUNCH_ARG_PRESENT=%1
if not defined ISIS_LAUNCH_ARG_PRESENT goto launch
set "ISIS_LAUNCH_ARG_%ISIS_LAUNCH_ARG_COUNT%=%~1"
set /a ISIS_LAUNCH_ARG_COUNT+=1 >nul
shift
goto capture_argument

:launch
pushd "%ISIS_LAUNCH_DIR%"
"%ComSpec%" /d /s /c ""%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File .\isis-launch.ps1"
set "ISIS_LAUNCH_EXIT=%ERRORLEVEL%"
popd
endlocal & exit /b %ISIS_LAUNCH_EXIT%
