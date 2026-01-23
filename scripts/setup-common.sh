#!/bin/sh
# Common setup functions for installation scripts
# Source this file to get shared setup utilities
# POSIX-compatible - works with /bin/sh (dash, ash, etc.)

# Setup virtual environment and determine paths
# Sets: VENV_PATH, PYTHON, PIP, POETRY, UV
setup_venv() {
    project_root="$1"
    venv_path="${project_root}/.venv"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_path" ]; then
        echo "Creating virtual environment at ${venv_path}..." >&2
        python3 -m venv "$venv_path"
        echo "✓ Virtual environment created." >&2
        echo "" >&2
    else
        echo "✓ Virtual environment already exists at ${venv_path}" >&2
        echo "" >&2
    fi
    
    # Determine Python and pip paths (cross-platform)
    if [ -f "${venv_path}/bin/python" ]; then
        VENV_PATH="$venv_path"
        PYTHON="${venv_path}/bin/python"
        PIP="${venv_path}/bin/pip"
        POETRY="${venv_path}/bin/poetry"
        UV="${venv_path}/bin/uv"
        export VENV_PATH PYTHON PIP POETRY UV
    elif [ -f "${venv_path}/Scripts/python.exe" ]; then
        VENV_PATH="$venv_path"
        PYTHON="${venv_path}/Scripts/python.exe"
        PIP="${venv_path}/Scripts/pip.exe"
        POETRY="${venv_path}/Scripts/poetry.exe"
        UV="${venv_path}/Scripts/uv.exe"
        export VENV_PATH PYTHON PIP POETRY UV
    else
        echo "Error: Could not find Python in virtual environment" >&2
        exit 1
    fi
    
    # Upgrade pip
    echo "Upgrading pip..." >&2
    "$PYTHON" -m pip install --upgrade pip --quiet >&2
    echo "✓ pip upgraded." >&2
    echo "" >&2
}

# Install numpy system dependencies on Linux (required even when numpy is installed from wheels)
# NumPy wheels require system libraries like libopenblas.so.0
# Returns 0 if successful or skipped, 1 if failed
install_numpy_for_pi() {
    if [ "$(uname)" != "Linux" ]; then
        return 0  # Skip on non-Linux
    fi
    
    if ! command -v apt-get >/dev/null 2>&1; then
        echo "Warning: apt-get not found. NumPy may require system libraries." >&2
        return 0
    fi
    
    # Check if numpy is already installed
    numpy_installed=false
    if "$PYTHON" -c "import numpy" >/dev/null 2>&1; then
        numpy_installed=true
        echo "✓ numpy already installed (from wheel/pip)." >&2
    fi
    
    # Always install system libraries needed by numpy wheels (libopenblas, etc.)
    echo "Installing NumPy system dependencies (libopenblas, etc.)..." >&2
    if sudo apt-get update -qq >/dev/null 2>&1 && sudo apt-get install -y libopenblas0 python3-numpy >/dev/null 2>&1; then
        if [ "$numpy_installed" = "false" ]; then
            echo "✓ numpy installed via apt." >&2
        else
            echo "✓ NumPy system libraries installed." >&2
        fi
        return 0
    else
        echo "Warning: Could not install NumPy system libraries via apt." >&2
        if [ "$numpy_installed" = "false" ]; then
            echo "  Will try pip with larger temp directory..." >&2
            TMPDIR="${HOME}/.tmp"
            export TMPDIR
            mkdir -p "$TMPDIR"
            echo "  Using ${TMPDIR} for build temporary files (has more space than /tmp)" >&2
        fi
        return 0
    fi
}

# Try to install package using available package managers
# Args: project_root, extras (e.g., ".[dev,hardware]" or ".[dev]")
# Returns 0 on success, 1 on failure
install_with_available_manager() {
    project_root="$1"
    extras="$2"
    
    cd "$project_root"
    
    # Try Poetry first
    if [ -f "${project_root}/poetry.lock" ] && [ -f "$POETRY" ]; then
        echo "Using Poetry to install dependencies..." >&2
        if "$POETRY" install --with dev 2>&1; then
            echo "✓ Dependencies installed with Poetry." >&2
            return 0
        fi
        echo "Warning: Poetry installation failed, trying alternatives..." >&2
    fi
    
    # Try uv
    uv_cmd=""
    if [ -f "$UV" ]; then
        uv_cmd="$UV"
    elif command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
        uv_cmd="uv"
    else
        echo "Installing uv..." >&2
        if "$PYTHON" -m pip install uv --quiet >&2; then
            uv_cmd="$UV"
            echo "✓ uv installed." >&2
        fi
    fi
    
    if [ -n "$uv_cmd" ]; then
        echo "Installing dependencies with uv..." >&2
        # piwheels is configured in pyproject.toml - uv will automatically use it on ARM
        if "$uv_cmd" pip install -e "$extras" 2>&1; then
            echo "✓ Dependencies installed with uv." >&2
            return 0
        fi
    fi
    
    # Fall back to pip
    echo "Using pip to install dependencies (preferring binary wheels to avoid Rust builds)..." >&2
    # Use --only-binary=:all: to force binary wheels and prevent Rust compilation
    # This applies to dependencies, not the editable package itself
    if "$PIP" install --only-binary=:all: --prefer-binary -e "$extras" 2>&1; then
        echo "✓ Dependencies installed with pip (binary wheels only, no Rust builds)." >&2
        return 0
    else
        echo "Warning: Binary-only install failed, trying with prefer-binary only..." >&2
        # Fall back to prefer-binary (still tries to use wheels but allows source builds if absolutely needed)
        if "$PIP" install --prefer-binary -e "$extras" 2>&1; then
            echo "✓ Dependencies installed with pip (wheels preferred)." >&2
            return 0
        fi
    fi
    
    return 1
}
