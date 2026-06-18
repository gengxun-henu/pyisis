#!/usr/bin/env bash

if [ -n "${PYISIS_OLD_ISISDATA+x}" ]; then
  export ISISDATA="${PYISIS_OLD_ISISDATA}"
  unset PYISIS_OLD_ISISDATA
else
  unset ISISDATA
fi
