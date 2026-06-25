@echo on
setlocal EnableExtensions EnableDelayedExpansion

set "DATA_DIR=%PREFIX%\share\isisdata"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

for /D %%D in ("%SRC_DIR%\*") do (
  robocopy "%%~fD" "%DATA_DIR%\%%~nxD" /E
  set "ROBOCOPY_EXIT=!ERRORLEVEL!"
  if !ROBOCOPY_EXIT! GEQ 8 exit /b !ROBOCOPY_EXIT!
)

set "ACTIVATE_DIR=%PREFIX%\etc\conda\activate.d"
set "DEACTIVATE_DIR=%PREFIX%\etc\conda\deactivate.d"
if not exist "%ACTIVATE_DIR%" mkdir "%ACTIVATE_DIR%"
if not exist "%DEACTIVATE_DIR%" mkdir "%DEACTIVATE_DIR%"

copy "%RECIPE_DIR%\activate.d\pyisis-isisdata-minimal-activate.bat" "%ACTIVATE_DIR%\"
if errorlevel 1 exit /b 1
copy "%RECIPE_DIR%\deactivate.d\pyisis-isisdata-minimal-deactivate.bat" "%DEACTIVATE_DIR%\"
if errorlevel 1 exit /b 1
copy "%RECIPE_DIR%\activate.d\pyisis-isisdata-minimal-activate.sh" "%ACTIVATE_DIR%\"
if errorlevel 1 exit /b 1
copy "%RECIPE_DIR%\deactivate.d\pyisis-isisdata-minimal-deactivate.sh" "%DEACTIVATE_DIR%\"
if errorlevel 1 exit /b 1

exit /b 0
