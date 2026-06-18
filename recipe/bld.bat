@echo on
setlocal enabledelayedexpansion

if "%SRC_DIR%"=="" set "SRC_DIR=%CD%"
if "%PREFIX%"=="" (
  echo PREFIX is required by conda-build.
  exit /b 1
)
if "%PYTHON%"=="" (
  echo PYTHON is required by conda-build.
  exit /b 1
)
if "%ISIS_PREFIX%"=="" set "ISIS_PREFIX=%PREFIX%"
if "%PYISIS_DEP_PREFIX%"=="" set "PYISIS_DEP_PREFIX=%PREFIX%"
if "%CPU_COUNT%"=="" set "CPU_COUNT=2"
if "%SP_DIR%"=="" set "SP_DIR=%PREFIX%\Lib\site-packages"

set "ISIS_INCLUDE_DIR=%ISIS_PREFIX%\include\isis"
if not exist "%ISIS_INCLUDE_DIR%" set "ISIS_INCLUDE_DIR=%ISIS_PREFIX%\Library\include\isis"

set "ISIS_LIBRARY_DIR=%ISIS_PREFIX%\lib"
if not exist "%ISIS_LIBRARY_DIR%\isis.lib" set "ISIS_LIBRARY_DIR=%ISIS_PREFIX%\Library\lib"

set "ISIS_RUNTIME_DIR=%ISIS_PREFIX%\bin"
if not exist "%ISIS_RUNTIME_DIR%\isis.dll" set "ISIS_RUNTIME_DIR=%ISIS_PREFIX%\Library\bin"
if not exist "%ISIS_RUNTIME_DIR%\isis.dll" set "ISIS_RUNTIME_DIR=%ISIS_PREFIX%\lib"
if not exist "%ISIS_RUNTIME_DIR%\isis.dll" set "ISIS_RUNTIME_DIR=%ISIS_PREFIX%\Library\lib"

set "ISIS_CORE_LIBRARY=%ISIS_LIBRARY_DIR%\isis.lib"
set "ISIS_PLUGIN_FILE=%ISIS_LIBRARY_DIR%\Camera.plugin"
if not exist "%ISIS_PLUGIN_FILE%" set "ISIS_PLUGIN_FILE=%ISIS_RUNTIME_DIR%\Camera.plugin"

if not exist "%ISIS_INCLUDE_DIR%" (
  echo ISIS include directory was not found: %ISIS_INCLUDE_DIR%
  exit /b 1
)
if not exist "%ISIS_LIBRARY_DIR%" (
  echo ISIS library directory was not found: %ISIS_LIBRARY_DIR%
  exit /b 1
)
if not exist "%ISIS_RUNTIME_DIR%" (
  echo ISIS runtime directory was not found: %ISIS_RUNTIME_DIR%
  exit /b 1
)
if not exist "%ISIS_CORE_LIBRARY%" (
  echo ISIS core import library was not found: %ISIS_CORE_LIBRARY%
  exit /b 1
)
if not exist "%ISIS_PLUGIN_FILE%" (
  echo Camera.plugin was not found: %ISIS_PLUGIN_FILE%
  exit /b 1
)

set "DEP_INCLUDE_DIR=%PYISIS_DEP_PREFIX%\Library\include"
if not exist "%DEP_INCLUDE_DIR%" set "DEP_INCLUDE_DIR=%PYISIS_DEP_PREFIX%\include"
if not exist "%DEP_INCLUDE_DIR%" set "DEP_INCLUDE_DIR=%ISIS_PREFIX%\include"
if not exist "%DEP_INCLUDE_DIR%" set "DEP_INCLUDE_DIR=%ISIS_PREFIX%\Library\include"

set "DEP_LIBRARY_DIR=%PYISIS_DEP_PREFIX%\Library\lib"
if not exist "%DEP_LIBRARY_DIR%" set "DEP_LIBRARY_DIR=%PYISIS_DEP_PREFIX%\lib"
if not exist "%DEP_LIBRARY_DIR%" set "DEP_LIBRARY_DIR=%ISIS_LIBRARY_DIR%"

if not exist "%DEP_INCLUDE_DIR%" (
  echo No dependency include directory was found.
  exit /b 1
)
if not exist "%DEP_LIBRARY_DIR%" (
  echo No dependency library directory was found.
  exit /b 1
)

set "DEP_INCLUDE_DIRS=%DEP_INCLUDE_DIR%"
if exist "%PYISIS_DEP_PREFIX%\include" set "DEP_INCLUDE_DIRS=%DEP_INCLUDE_DIRS%;%PYISIS_DEP_PREFIX%\include"
if exist "%PYISIS_DEP_PREFIX%\Library\include" set "DEP_INCLUDE_DIRS=%DEP_INCLUDE_DIRS%;%PYISIS_DEP_PREFIX%\Library\include"
if exist "%ISIS_PREFIX%\include" set "DEP_INCLUDE_DIRS=%DEP_INCLUDE_DIRS%;%ISIS_PREFIX%\include"
if exist "%ISIS_PREFIX%\Library\include" set "DEP_INCLUDE_DIRS=%DEP_INCLUDE_DIRS%;%ISIS_PREFIX%\Library\include"

set "DEP_LIBRARY_DIRS=%DEP_LIBRARY_DIR%"
if exist "%PYISIS_DEP_PREFIX%\lib" set "DEP_LIBRARY_DIRS=%DEP_LIBRARY_DIRS%;%PYISIS_DEP_PREFIX%\lib"
if exist "%PYISIS_DEP_PREFIX%\Library\lib" set "DEP_LIBRARY_DIRS=%DEP_LIBRARY_DIRS%;%PYISIS_DEP_PREFIX%\Library\lib"
if exist "%ISIS_LIBRARY_DIR%" set "DEP_LIBRARY_DIRS=%DEP_LIBRARY_DIRS%;%ISIS_LIBRARY_DIR%"
set "PYISIS_CMAKE_PREFIX_PATH=%PYISIS_DEP_PREFIX%;%ISIS_PREFIX%"
if "%PYISIS_BUILD_DIR%"=="" set "PYISIS_BUILD_DIR=%SRC_DIR%\build-conda"
set "BUILD_DIR=%PYISIS_BUILD_DIR%"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G Ninja %CMAKE_ARGS% ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DPython3_EXECUTABLE="%PYTHON%" ^
  -DPYISIS_INSTALL_SITELIB="%SP_DIR%" ^
  -DPYISIS_INSTALL_SITEARCH="%SP_DIR%" ^
  -DCMAKE_INSTALL_PREFIX="%PREFIX%" ^
  -DCMAKE_PREFIX_PATH="%PYISIS_CMAKE_PREFIX_PATH%" ^
  -DISIS_PREFIX="%ISIS_PREFIX%" ^
  -DISIS_INCLUDE_DIR="%ISIS_INCLUDE_DIR%" ^
  -DISIS_DEP_INCLUDE_DIR="%DEP_INCLUDE_DIR%" ^
  -DISIS_DEP_INCLUDE_DIRS="%DEP_INCLUDE_DIRS%" ^
  -DISIS_LIBRARY_DIR="%ISIS_LIBRARY_DIR%" ^
  -DISIS_DEP_LIBRARY_DIRS="%DEP_LIBRARY_DIRS%" ^
  -DISIS_RUNTIME_DIR="%ISIS_RUNTIME_DIR%" ^
  -DISIS_CORE_LIBRARY="%ISIS_CORE_LIBRARY%" ^
  -DISIS_PLUGIN_FILE="%ISIS_PLUGIN_FILE%" ^
  -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config Release --parallel "%CPU_COUNT%"
if errorlevel 1 exit /b 1

cmake --install "%BUILD_DIR%" --config Release
if errorlevel 1 exit /b 1
