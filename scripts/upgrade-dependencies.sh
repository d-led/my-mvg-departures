#!/bin/bash
# Upgrade every dependency of every sub-project to its latest major version.
#
# Standard tools do the work - no hand-rolled version logic:
#   npm projects    taze   ->  npx --yes taze@latest major --write --install
#   python projects uv     ->  uv pip install --upgrade -e ".[dev]"
#
# Both python projects share the repository virtual environment (.venv), see
# inky/scripts/setup_dev.sh - that is why uv is pointed at .venv explicitly.
#
# The GitHub Actions pins under .github/workflows are deliberately left alone:
# they are pinned by commit SHA and are upgraded separately.
#
# Usage: ./scripts/upgrade-dependencies.sh [options]
#
#   --dry-run        Show what would change, write nothing
#   --node-only      Upgrade only the npm projects (root, spa/)
#   --python-only    Upgrade only the python projects (root, inky/)
#   --recreate-venv  Recreate .venv when its interpreter no longer satisfies
#                    requires-python (needed after a python upgrade)
#   --verify         Run the test suites after upgrading
#   -h, --help       Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

DRY_RUN=false
DO_NODE=true
DO_PYTHON=true
RECREATE_VENV=false
VERIFY=false
VENV_PYTHON=""

usage() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \{0,1\}//'
}

section() {
    echo ""
    echo -e "${BLUE}━━━ $1 ━━━${NC}"
}

warn() {
    echo -e "${YELLOW}⚠ $1${NC}" >&2
}

die() {
    echo -e "${RED}✗ $1${NC}" >&2
    exit 1
}

parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --dry-run) DRY_RUN=true ;;
            --node-only) DO_PYTHON=false ;;
            --python-only) DO_NODE=false ;;
            --recreate-venv) RECREATE_VENV=true ;;
            --verify) VERIFY=true ;;
            -h|--help) usage; exit 0 ;;
            *) die "Unknown option: $1 (try --help)" ;;
        esac
        shift
    done
}

# Lower bound of requires-python, e.g. ">=3.13,<3.14" -> "3.13"
required_python() {
    sed -n 's/.*requires-python *= *"[^0-9]*\([0-9][0-9]*\.[0-9][0-9]*\).*/\1/p' \
        "${PROJECT_ROOT}/pyproject.toml" | head -n1
}

# Version comparison in the style used by scripts/setup.sh
version_satisfies() {
    local required="$1" actual="$2"
    [ "$(printf '%s\n' "$required" "$actual" | sort -V | head -n1)" = "$required" ]
}

venv_python_path() {
    if [ -f "${PROJECT_ROOT}/.venv/bin/python" ]; then
        echo "${PROJECT_ROOT}/.venv/bin/python"
    else
        echo "${PROJECT_ROOT}/.venv/Scripts/python.exe"
    fi
}

prepare_venv() {
    VENV_PYTHON="$(venv_python_path)"

    if [ ! -f "$VENV_PYTHON" ]; then
        die "No virtual environment found. Run ./scripts/setup.sh first."
    fi

    local required actual
    required="$(required_python)"
    [ -n "$required" ] || die "Could not read requires-python from pyproject.toml"

    actual="$("$VENV_PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    if version_satisfies "$required" "$actual"; then
        echo "Using .venv (Python ${actual})"
        return 0
    fi

    if [ "$RECREATE_VENV" = true ] && [ "$DRY_RUN" = false ]; then
        warn "Recreating .venv: Python ${actual} does not satisfy requires-python >= ${required}"
        rm -rf "${PROJECT_ROOT}/.venv"
        python3 -m venv "${PROJECT_ROOT}/.venv"
        VENV_PYTHON="$(venv_python_path)"
        return 0
    fi

    die ".venv runs Python ${actual}, but pyproject.toml requires >= ${required}.\
  Recreate it with: ./scripts/upgrade-dependencies.sh --recreate-venv"
}

upgrade_node_project() {
    local dir="$1"
    local exclude="${2:-}"

    section "npm: ${dir}"

    local taze=(npx --yes taze@latest major --no-github-actions --no-node-version)
    if [ -n "$exclude" ]; then
        taze+=(--exclude "$exclude")
    fi
    if [ "$DRY_RUN" = false ]; then
        taze+=(--write)
    fi

    (cd "${PROJECT_ROOT}/${dir}" && "${taze[@]}")

    # Installing is left to npm: taze's bundled installer passes --allow-scripts,
    # which npm rejects for project-scoped installs.
    local npm_install=(npm install)
    if [ "$DRY_RUN" = true ]; then
        npm_install+=(--dry-run)
    fi
    (cd "${PROJECT_ROOT}/${dir}" && "${npm_install[@]}")

    # Clear transitive advisories npm can fix inside the declared ranges. A non-zero
    # exit only means advisories remain (often nothing to fix upstream), so report
    # them instead of aborting the rest of the upgrade.
    local audit_fix=(npm audit fix)
    if [ "$DRY_RUN" = true ]; then
        audit_fix+=(--dry-run)
    fi
    if ! (cd "${PROJECT_ROOT}/${dir}" && "${audit_fix[@]}"); then
        warn "npm audit reports advisories in ${dir} - review the output above"
    fi
}

upgrade_python_project() {
    local dir="$1"
    local extras="$2"

    section "python: ${dir} (${extras})"

    # piwheels is configured as an extra index in both pyproject.toml files, so uv
    # needs unsafe-best-match to also consider PyPI for packages piwheels mirrors.
    local uv_install=(uv pip install --upgrade --index-strategy unsafe-best-match
        --python "$VENV_PYTHON")
    if [ "$DRY_RUN" = true ]; then
        uv_install+=(--dry-run)
    fi

    (cd "${PROJECT_ROOT}/${dir}" && "${uv_install[@]}" -e "$extras")

    echo ""
    echo "Behind latest (transitive pins or venv tooling, not our declared dependencies):"
    (cd "${PROJECT_ROOT}/${dir}" && uv pip list --outdated --python "$VENV_PYTHON")
}

verify() {
    section "verifying"
    ./scripts/test.sh
    if [ -d "${PROJECT_ROOT}/spa/node_modules" ]; then
        (cd "${PROJECT_ROOT}/spa" && npm test)
    else
        warn "spa/node_modules missing - skipping spa tests (run: cd spa && npm ci)"
    fi
    echo ""
    echo "Note: the Cypress end-to-end suite needs a running app, run it manually:"
    echo "  ./scripts/start.sh   (in one shell)"
    echo "  npm run e2e          (in another shell)"
}

summary() {
    section "summary"
    echo "Changed manifests and lock files:"
    git diff --stat -- '*.json' '*.toml'
    echo "Not touched by design:"
    echo "  - .github/workflows/*.yml  (actions are pinned by SHA, upgraded separately)"
    echo "  - requires-python / version ranges in pyproject.toml (uv has no taze equivalent);"
    echo "    use 'uv add \"<package>>=<version>\"' to raise a minimum on purpose"
}

main() {
    parse_args "$@"

    echo "Upgrading dependencies to their latest major versions"
    echo "Project root: ${PROJECT_ROOT}"

    if [ "$DO_NODE" = true ]; then
        upgrade_node_project "."
        # typescript-eslint still caps its typescript peer at <6.1.0
        upgrade_node_project "spa" "typescript@7"
    fi

    if [ "$DO_PYTHON" = true ]; then
        prepare_venv
        upgrade_python_project "." ".[dev]"
        upgrade_python_project "inky" ".[dev]"
    fi

    if [ "$VERIFY" = true ]; then
        verify
    fi

    summary

    echo ""
    echo -e "${GREEN}✓ Dependency upgrade complete.${NC}"
}

main "$@"
