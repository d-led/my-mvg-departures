#!/bin/bash
# Run all utility scripts to verify they work correctly
# This is a smoke test to ensure scripts are functional

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track results
PASSED=0
FAILED=0
SKIPPED=0
FAILED_SCRIPTS=()

# Function to run a script and track results
run_script() {
    local script_name="$1"
    local description="$2"
    local timeout_seconds="${3:-30}"  # Default 30 seconds, can be overridden
    shift 3
    local args=("${@:-}")
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $script_name"
    echo "Description: $description"
    if [ ${#args[@]} -gt 0 ]; then
        echo "Arguments: ${args[*]}"
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
        echo -e "${YELLOW}⚠ SKIPPED: Script not found${NC}"
        ((SKIPPED++))
        return
    fi
    
    if [ ! -x "$SCRIPT_DIR/$script_name" ]; then
        chmod +x "$SCRIPT_DIR/$script_name" 2>/dev/null || {
            echo -e "${YELLOW}⚠ SKIPPED: Script not executable${NC}"
            ((SKIPPED++))
            return
        }
    fi
    
    # Run script with timeout and capture output
    # Use conditional expansion to handle empty args array
    local script_exit_code=0
    if [ ${#args[@]} -gt 0 ]; then
        timeout "$timeout_seconds" "$SCRIPT_DIR/$script_name" "${args[@]}" >/tmp/script_output_$$.log 2>&1 || script_exit_code=$?
    else
        timeout "$timeout_seconds" "$SCRIPT_DIR/$script_name" >/tmp/script_output_$$.log 2>&1 || script_exit_code=$?
    fi
    
    if [ $script_exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        # Show last few lines of output for context
        if [ -s /tmp/script_output_$$.log ]; then
            echo "Last output lines:"
            tail -3 /tmp/script_output_$$.log | sed 's/^/  /'
        fi
    else
        echo -e "${RED}✗ FAILED (exit code: $script_exit_code)${NC}"
        ((FAILED++))
        FAILED_SCRIPTS+=("$script_name")
        echo "Error output:"
        tail -10 /tmp/script_output_$$.log | sed 's/^/  /' || true
    fi
    
    rm -f /tmp/script_output_$$.log
}

# Check if config.example.toml exists
CONFIG_FILE="config.example.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}Warning: $CONFIG_FILE not found. Some tests will be skipped.${NC}"
    CONFIG_FILE=""
fi

echo "════════════════════════════════════════════════════════════════════════════════"
echo "Running all utility scripts smoke tests"
echo "════════════════════════════════════════════════════════════════════════════════"

# 1. Check all stations script
if [ -n "$CONFIG_FILE" ]; then
    run_script "check_all_stations.sh" "Check if all stations in config can be queried" 60 "$CONFIG_FILE"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: check_all_stations.sh"
    echo -e "${YELLOW}⚠ SKIPPED: config.example.toml not found${NC}"
    ((SKIPPED++))
fi

# 2. Analyze complexity script (needs more time)
run_script "analyze_complexity.sh" "Analyze code complexity metrics" 120

# 3. List routes (MVG)
run_script "list_routes.sh" "List routes for MVG station" 30 "Balanstr."

# 4. List routes VBB
run_script "list_routes_vbb.sh" "List routes for VBB station" 30 "blissestr."

# 5. List routes DB
run_script "list_routes_db.sh" "List routes for DB station" 30 "blissestr."

# Print summary
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "SUMMARY"
echo "════════════════════════════════════════════════════════════════════════════════"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
    echo "Failed scripts:"
    for script in "${FAILED_SCRIPTS[@]}"; do
        echo "  - $script"
    done
else
    echo -e "${GREEN}Failed: $FAILED${NC}"
fi
if [ $SKIPPED -gt 0 ]; then
    echo -e "${YELLOW}Skipped: $SKIPPED${NC}"
fi
echo ""

# Exit with error if any script failed
if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0

