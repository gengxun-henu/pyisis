@echo off
call "%~dp0isis-env.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%
cmd.exe /d /k
exit /b %ERRORLEVEL%
