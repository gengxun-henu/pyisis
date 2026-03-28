# CMake generated Testfile for 
# Source directory: /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone
# Build directory: /home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/build_conda
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(python-unit-tests "/home/gengxun/miniconda3/envs/asp360_new/bin/python" "-m" "unittest" "discover" "-s" "/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/unitTest" "-p" "*_unit_test.py")
set_tests_properties(python-unit-tests PROPERTIES  ENVIRONMENT "PYTHONPATH=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/build_conda/python" LD_LIBRARY_PATH=/home/gengxun/miniconda3/envs/asp360_new/lib "ISISDATA=/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/tests/data/isisdata/mockup" WORKING_DIRECTORY "/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone" _BACKTRACE_TRIPLES "/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/CMakeLists.txt;240;add_test;/home/gengxun/PlanetaryMapping/asp360_new/pyisis/ISIS3-9.0.0-ext/isis_pybind_standalone/CMakeLists.txt;0;")
