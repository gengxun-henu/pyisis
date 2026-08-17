@echo off
call "%~dp0isis-app.cmd" qnet %*
exit /b %ERRORLEVEL%
