@echo off
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0isis-launch.ps1" qnet %*
exit /b %ERRORLEVEL%
