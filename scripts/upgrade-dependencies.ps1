# Upgrade script for MVG Departures (PowerShell mirror of upgrade-dependencies.sh)
# Upgrade every dependency of every sub-project to its latest major version.
#
# Standard tools do the work - no hand-rolled version logic:
#   npm projects    taze   ->  npx --yes taze@latest major --write --install
#   python projects uv     ->  uv pip install --upgrade -e ".[dev]"
#
# Both python projects share the repository virtual environment (.venv).
# The GitHub Actions pins under .github/workflows are deliberately left alone.

param(
    [switch]$DryRun,
    [switch]$NodeOnly,
    [switch]$PythonOnly,
    [switch]$RecreateVenv,
    [switch]$Verify
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

$DoNode = -not $PythonOnly
$DoPython = -not $NodeOnly
$VenvPython = $null

function Write-Section($title) {
    Write-Host ""
    Write-Host "━━━ $title ━━━" -ForegroundColor Cyan
}

function Write-Warn($message) {
    Write-Host "⚠ $message" -ForegroundColor Yellow
}

function Get-RequiredPython {
    $line = Select-String -Path "pyproject.toml" -Pattern 'requires-python\s*=\s*"[^0-9]*([0-9]+\.[0-9]+)' |
        Select-Object -First 1
    if (-not $line) {
        throw "Could not read requires-python from pyproject.toml"
    }
    return $line.Matches[0].Groups[1].Value
}

function Get-VenvPythonPath {
    $posix = Join-Path $PROJECT_ROOT ".venv/bin/python"
    if (Test-Path $posix) {
        return $posix
    }
    return (Join-Path $PROJECT_ROOT ".venv/Scripts/python.exe")
}

function Initialize-Venv {
    $script:VenvPython = Get-VenvPythonPath

    if (-not (Test-Path $script:VenvPython)) {
        throw "No virtual environment found. Run .\scripts\setup.ps1 first."
    }

    $required = [version](Get-RequiredPython)
    $actual = [version](& $script:VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

    if ($actual -ge $required) {
        Write-Host "Using .venv (Python $actual)"
        return
    }

    if (-not $RecreateVenv) {
        throw ".venv runs Python $actual, but pyproject.toml requires >= $required. Re-run with -RecreateVenv."
    }

    Write-Warn "Recreating .venv: Python $actual does not satisfy requires-python >= $required"
    Remove-Item -Recurse -Force (Join-Path $PROJECT_ROOT ".venv")
    python3 -m venv (Join-Path $PROJECT_ROOT ".venv")
    $script:VenvPython = Get-VenvPythonPath
}

function Invoke-NodeUpgrade($dir, $exclude = "") {
    Write-Section "npm: $dir"

    $taze = @("--yes", "taze@latest", "major", "--no-github-actions", "--no-node-version")
    if ($exclude) {
        $taze += @("--exclude", $exclude)
    }
    if (-not $DryRun) {
        $taze += "--write"
    }

    Push-Location (Join-Path $PROJECT_ROOT $dir)
    try {
        & npx @taze

        # Installing is left to npm: taze's bundled installer passes --allow-scripts,
        # which npm rejects for project-scoped installs.
        $npmInstall = @("install")
        if ($DryRun) {
            $npmInstall += "--dry-run"
        }
        & npm @npmInstall

        # Clear transitive advisories npm can fix inside the declared ranges. A
        # non-zero exit only means advisories remain (often nothing to fix
        # upstream), so report them instead of aborting the rest of the upgrade.
        $auditFix = @("audit", "fix")
        if ($DryRun) {
            $auditFix += "--dry-run"
        }
        & npm @auditFix
        if ($LASTEXITCODE -ne 0) {
            Write-Warn "npm audit reports advisories in $dir - review the output above"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-PythonUpgrade($dir, $extras) {
    Write-Section "python: $dir ($extras)"

    # piwheels is configured as an extra index in both pyproject.toml files, so uv
    # needs unsafe-best-match to also consider PyPI for packages piwheels mirrors.
    $uvInstall = @("pip", "install", "--upgrade", "--index-strategy", "unsafe-best-match",
        "--python", $VenvPython)
    if ($DryRun) {
        $uvInstall += "--dry-run"
    }

    Push-Location (Join-Path $PROJECT_ROOT $dir)
    try {
        & uv @uvInstall -e $extras

        Write-Host ""
        Write-Host "Behind latest (transitive pins or venv tooling, not our declared dependencies):"
        & uv pip list --outdated --python $VenvPython
    } finally {
        Pop-Location
    }
}

function Invoke-Verify {
    Write-Section "verifying"

    & (Join-Path $PROJECT_ROOT "scripts/test.sh")

    if (Test-Path (Join-Path $PROJECT_ROOT "spa/node_modules")) {
        Push-Location (Join-Path $PROJECT_ROOT "spa")
        try {
            & npm test
        } finally {
            Pop-Location
        }
    } else {
        Write-Warn "spa/node_modules missing - skipping spa tests (run: cd spa; npm ci)"
    }
}

function Write-Summary {
    Write-Section "summary"
    Write-Host "Changed manifests and lock files:"
    git diff --stat -- '*.json' '*.toml'

    Write-Host ""
    Write-Host "Not touched by design:"
    Write-Host "  - .github/workflows/*.yml  (actions are pinned by SHA, upgraded separately)"
    Write-Host "  - requires-python / version ranges in pyproject.toml (uv has no taze equivalent);"
    Write-Host '    use uv add "<package>>=<version>" to raise a minimum on purpose'
}

Write-Host "Upgrading dependencies to their latest major versions"
Write-Host "Project root: $PROJECT_ROOT"

if ($DoNode) {
    Invoke-NodeUpgrade "."
    # typescript-eslint still caps its typescript peer at <6.1.0
    Invoke-NodeUpgrade "spa" "typescript@7"
}

if ($DoPython) {
    Initialize-Venv
    Invoke-PythonUpgrade "." ".[dev]"
    Invoke-PythonUpgrade "inky" ".[dev]"
}

if ($Verify) {
    Invoke-Verify
}

Write-Summary

Write-Host ""
Write-Host "✓ Dependency upgrade complete." -ForegroundColor Green
