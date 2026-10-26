#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$project_dir"
if ! command -v conda >/dev/null 2>&1; then
  echo 'Conda debe estar instalado y disponible en PATH.' >&2
  exit 1
fi
export CONDA_PKGS_DIRS="${CONDA_PKGS_DIRS:-$project_dir/.conda-pkgs}"
env_prefix="${CEMEC_ENV_PREFIX:-$project_dir/.conda-env}"
if [[ ! -f "$env_prefix/conda-meta/history" ]]; then
  conda env create --prefix "$env_prefix" --file environment.yml --yes
else
  if [[ ! -x "$env_prefix/bin/node" ]] || ! "$env_prefix/bin/python" -c 'import yaml, shapely, pyarrow, eumdac' >/dev/null 2>&1; then
    conda env update --prefix "$env_prefix" --file environment.yml
  else
    echo "Entorno completo: $env_prefix (se conservan las versiones instaladas)."
  fi
fi
"$env_prefix/bin/python" scripts/replicate.py
conda list --prefix "$env_prefix" --explicit --sha256 > environment-linux-64.lock.txt
echo 'Instalación lista. Inicia con ./Start-CEMEC.sh'
