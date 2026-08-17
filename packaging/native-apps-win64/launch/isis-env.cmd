@echo off
set "ISIS_PACKAGE_ROOT=%~dp0.."
for %%I in ("%ISIS_PACKAGE_ROOT%") do set "ISIS_PACKAGE_ROOT=%%~fI"

if defined ISISDATA (
  if not exist "%ISISDATA%\." (
    >&2 echo Explicit ISISDATA directory does not exist: %ISISDATA%
    exit /b 3
  )
) else (
  set "ISISDATA=%ISIS_PACKAGE_ROOT%\data"
)

set "ISISROOT=%ISIS_PACKAGE_ROOT%"
set "ISIS_PREFIX=%ISIS_PACKAGE_ROOT%"
set "QT_PLUGIN_PATH=%ISIS_PACKAGE_ROOT%\plugins"
set "PATH=%ISIS_PACKAGE_ROOT%\bin;%ISIS_PACKAGE_ROOT%\lib;%PATH%"
exit /b 0
