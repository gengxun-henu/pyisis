#!/usr/bin/env bash

if [ -n "${ISISDATA+x}" ]; then
  export PYISIS_OLD_ISISDATA="${ISISDATA}"
else
  unset PYISIS_OLD_ISISDATA
fi

if [ -z "${ISISDATA:-}" ] && [ -d "${CONDA_PREFIX}/share/isisdata" ]; then
  export ISISDATA="${CONDA_PREFIX}/share/isisdata"
fi
