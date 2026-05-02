# pyisis build commands

优先使用脚本入口，避免每次手写整串环境变量与 CMake 参数。

在仓库根目录执行：

## full

```bash
scripts/build_test_smoke.sh full
```

## build-only

```bash
scripts/build_test_smoke.sh build-only
```

## test-only

```bash
scripts/build_test_smoke.sh test-only
```

## verbose-test

用于定位 Python unit test 的具体失败 case。相比 `test-only`，这里改为使用更详细的 `unittest -v` 输出，然后再跑 `smoke_import.py`。

```bash
scripts/build_test_smoke.sh verbose-test
```

## clean-full

仅在用户明确要求清理缓存或怀疑构建缓存失效时使用。

```bash
scripts/build_test_smoke.sh clean-full
```

## unit-module

仅运行单个 unittest 模块。

```bash
scripts/build_test_smoke.sh unit-module tests.unitTest.controlnet_construct_e2e_unit_test
```

## raw full command

如果需要展开后的原始命令，可使用：

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

说明：默认不要预先导出 `LD_LIBRARY_PATH="$CONDA_PREFIX/lib:..."` 给系统 `/usr/bin/cmake` 或 `/usr/bin/ctest`，否则容易出现 `libcurl.so.4: no version information available` 告警；当前仓库这几套命令在不设置该变量时已可正常完成 build、ctest 和 smoke。