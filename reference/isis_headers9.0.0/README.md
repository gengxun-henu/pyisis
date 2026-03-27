# ISIS reference headers

This directory contains reference header files copied from a local ISIS/conda environment
to make GitHub web-based inspection and pybind authoring easier.

## Purpose
- Read header declarations in GitHub web UI
- Search classes/functions/namespaces
- Help write pybind bindings

## Not the default build source
CI and actual compilation should prefer the ISIS headers and libraries prepared in the runner environment.

## Version
These headers were copied from ISIS 9.0.0.

## Notes
Keep the runner ISIS version aligned with this reference snapshot when possible.