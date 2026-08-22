#!/usr/bin/env bash
# Create a project-local dbt profile for one workshop participant.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./scripts/bootstrap_dbt_project.sh --project-id PROJECT --dataset DATASET [options]

Required:
  --project-id PROJECT    GCP project that contains the workshop resources
  --dataset DATASET       Participant-owned BigQuery dataset, e.g. workshop_alice

Options:
  --location LOCATION     BigQuery location (default: EU)
  --force                 Replace an existing local profiles.yml file
  --help                  Show this help text
EOF
}

project_id=""
dataset=""
location="EU"
force=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-id)
            project_id="${2:-}"
            shift 2
            ;;
        --dataset)
            dataset="${2:-}"
            shift 2
            ;;
        --location)
            location="${2:-}"
            shift 2
            ;;
        --force)
            force=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$project_id" || -z "$dataset" ]]; then
    printf '%s\n\n' '--project-id and --dataset are required.' >&2
    usage >&2
    exit 2
fi

if [[ ! "$dataset" =~ ^[A-Za-z_][A-Za-z0-9_]{0,1023}$ ]]; then
    printf '%s\n' 'Dataset must start with a letter or underscore and contain only letters, numbers, and underscores.' >&2
    exit 2
fi

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
template="$project_root/dbt-workshop/profiles.yml.example"
profile="$project_root/dbt-workshop/profiles.yml"

if [[ ! -f "$template" ]]; then
    printf 'Profile template not found: %s\n' "$template" >&2
    exit 1
fi

if [[ -f "$profile" && "$force" != true ]]; then
    printf 'Profile already exists: %s (use --force to replace it)\n' "$profile" >&2
    exit 1
fi

python3 - "$template" "$profile" "$project_id" "$dataset" "$location" <<'PY'
from pathlib import Path
import sys

template_path, output_path = map(Path, sys.argv[1:3])
project_id, dataset, location = sys.argv[3:]

contents = template_path.read_text()
for placeholder, value in {
    "__GCP_PROJECT_ID__": project_id,
    "__BQ_DATASET__": dataset,
    "__BQ_LOCATION__": location,
}.items():
    contents = contents.replace(placeholder, value)

output_path.write_text(contents)
print(f"Wrote {output_path}")
PY

printf '%s\n' 'Next steps:'
printf '  cd %s\n' "$project_root/dbt-workshop"
printf '  python3 -m pip install -r requirements.txt\n'
printf '  dbt run-operation create_workshop_dataset --profiles-dir .\n'
printf '  dbt debug --profiles-dir .\n'
