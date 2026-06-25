@echo off

if defined PYISIS_OLD_ISISDATA (
  set "ISISDATA=%PYISIS_OLD_ISISDATA%"
  set "PYISIS_OLD_ISISDATA="
) else (
  set "ISISDATA="
)
