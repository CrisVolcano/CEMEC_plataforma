#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
env_prefix="${CEMEC_ENV_PREFIX:-$project_dir/.conda-env}"
if [[ ! -x "$env_prefix/bin/python" || ! -x "$env_prefix/bin/node" ]]; then
  echo 'Falta el entorno Conda. Ejecuta ./Setup-CEMEC.sh' >&2
  exit 1
fi
export PATH="$env_prefix/bin:$PATH"
exec "$env_prefix/bin/python" "$project_dir/scripts/start.py" "$@"
