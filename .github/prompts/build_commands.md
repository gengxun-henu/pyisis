# pyisis build commands

在仓库根目录执行以下命令。默认优先保留 `build/` 缓存，不主动删除构建目录。

## full

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" -DISIS_PREFIX="$CONDA_PREFIX" -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
cmake --build build -j"$(nproc)"
ctest --test-dir build -R python-unit-tests --output-on-failure
"$CONDA_PREFIX/bin/python" tests/smoke_import.py
```

## build-only

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" -DISIS_PREFIX="$CONDA_PREFIX" -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
cmake --build build -j"$(nproc)"
```

## test-only

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
ctest --test-dir build -R python-unit-tests --output-on-failure
"$CONDA_PREFIX/bin/python" tests/smoke_import.py
```

## verbose-test

用于定位 Python unit test 的具体失败 case。相比 `test-only`，这里改为使用更详细的 `unittest -v` 输出，然后再跑 `smoke_import.py`。

```bash
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
PYTHONUNBUFFERED=1 "$CONDA_PREFIX/bin/python" -X faulthandler -m unittest discover -s tests/unitTest -p "*_unit_test.py" -v
"$CONDA_PREFIX/bin/python" tests/smoke_import.py
```

## clean-full

仅在用户明确要求清理缓存或怀疑构建缓存失效时使用。

```bash
rm -rf build
source /home/gengxun/miniconda3/etc/profile.d/conda.sh
conda activate asp360_new
export ISIS_PREFIX="$CONDA_PREFIX"
export ISISROOT="$CONDA_PREFIX"
export ISISDATA="$PWD/tests/data/isisdata/mockup"
export CMAKE_PREFIX_PATH="$CONDA_PREFIX"
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$CONDA_PREFIX/bin/python" -DISIS_PREFIX="$CONDA_PREFIX" -DISIS_EXCLUDE_ASP_VW_CAMERA_LIBS=ON
cmake --build build -j"$(nproc)"
ctest --test-dir build -R python-unit-tests --output-on-failure
"$CONDA_PREFIX/bin/python" tests/smoke_import.py

说明：默认不要预先导出 `LD_LIBRARY_PATH="$CONDA_PREFIX/lib:..."` 给系统 `/usr/bin/cmake` 或 `/usr/bin/ctest`，否则容易出现 `libcurl.so.4: no version information available` 告警；当前仓库这几套命令在不设置该变量时已可正常完成 build、ctest 和 smoke。

```