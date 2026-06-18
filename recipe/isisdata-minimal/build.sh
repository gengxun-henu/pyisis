#!/usr/bin/env bash
set -euo pipefail

data_dir="${PREFIX}/share/isisdata"
mkdir -p "${data_dir}"
for data_subdir in "${SRC_DIR}"/*; do
  [ -d "${data_subdir}" ] || continue
  cp -a "${data_subdir}" "${data_dir}/"
done

activate_dir="${PREFIX}/etc/conda/activate.d"
deactivate_dir="${PREFIX}/etc/conda/deactivate.d"
mkdir -p "${activate_dir}" "${deactivate_dir}"

cp "${RECIPE_DIR}/activate.d/pyisis-isisdata-minimal-activate.sh" "${activate_dir}/"
cp "${RECIPE_DIR}/deactivate.d/pyisis-isisdata-minimal-deactivate.sh" "${deactivate_dir}/"
cp "${RECIPE_DIR}/activate.d/pyisis-isisdata-minimal-activate.bat" "${activate_dir}/"
cp "${RECIPE_DIR}/deactivate.d/pyisis-isisdata-minimal-deactivate.bat" "${deactivate_dir}/"
