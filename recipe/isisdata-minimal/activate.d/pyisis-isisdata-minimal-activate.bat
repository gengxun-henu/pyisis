@echo off

if defined ISISDATA (
  set "PYISIS_OLD_ISISDATA=%ISISDATA%"
) else (
  set "PYISIS_OLD_ISISDATA="
)

if not defined ISISDATA (
  if exist "%CONDA_PREFIX%\share\isisdata" set "ISISDATA=%CONDA_PREFIX%\share\isisdata"
)
