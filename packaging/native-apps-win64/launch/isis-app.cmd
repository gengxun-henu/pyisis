@echo off
set "ISIS_APP_NAME=%~1"
set "ISIS_APP_MANIFEST=%~dp0..\manifest\apps.json"

if not defined ISIS_APP_NAME (
  >&2 echo Missing APP name; not a public ISIS APP.
  exit /b 2
)

powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $manifest=Get-Content -Raw -LiteralPath $env:ISIS_APP_MANIFEST | ConvertFrom-Json; if ($env:ISIS_APP_NAME -notmatch '^[A-Za-z0-9_-]+$' -or @($manifest.public_apps) -cnotcontains $env:ISIS_APP_NAME) { exit 4 } } catch { exit 5 }"
set "ISIS_APP_CHECK=%ERRORLEVEL%"
if "%ISIS_APP_CHECK%"=="5" (
  >&2 echo Unable to read ISIS APP manifest: %ISIS_APP_MANIFEST%
  exit /b 5
)
if not "%ISIS_APP_CHECK%"=="0" (
  >&2 echo Requested name is not a public ISIS APP.
  exit /b 4
)

call "%~dp0isis-env.cmd"
if errorlevel 1 exit /b %ERRORLEVEL%

shift
"%ISISROOT%\bin\%ISIS_APP_NAME%.exe" %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %ERRORLEVEL%
