#!/bin/bash
# Run all utility scripts to verify they work correctly
# This is a smoke test to ensure scripts are functional

set -uo pipefail  # Removed -e to allow proper signal handling

# Handle Ctrl-C gracefully - allow interruption
INTERRUPTED=0
cleanup() {
    INTERRUPTED=1
    echo ""
    echo "Interrupted by user. Cleaning up..."
    rm -f /tmp/script_output_$$.log
    exit 130
}
trap cleanup INT TERM

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
FLAKY_PASSED=0
FLAKY_FAILED=0
FAILED_SCRIPTS=()
FLAKY_FAILED_SCRIPTS=()

# Function to run a script and track results
run_script() {
    local script_name="$1"
    local description="$2"
    shift 2
    local args=("$@")
    
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
    
    # Run script directly - output will be shown in real-time
    # Use conditional expansion to handle empty args array
    local script_exit_code=0
    if [ ${#args[@]} -gt 0 ]; then
        "$SCRIPT_DIR/$script_name" "${args[@]}" || script_exit_code=$?
    else
        "$SCRIPT_DIR/$script_name" || script_exit_code=$?
    fi
    
    # Check if we were interrupted - if so, exit immediately
    if [ $INTERRUPTED -eq 1 ]; then
        cleanup
    fi
    
    # Check if script was interrupted (SIGINT = 130, SIGTERM = 143)
    if [ $script_exit_code -eq 130 ] || [ $script_exit_code -eq 143 ]; then
        echo -e "${YELLOW}⚠ INTERRUPTED${NC}"
        cleanup
    fi
    
    if [ $script_exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED (exit code: $script_exit_code)${NC}"
        ((FAILED++))
        FAILED_SCRIPTS+=("$script_name")
    fi
}

# Function to run a flaky script (expected to potentially fail, doesn't affect exit code)
run_script_flaky() {
    local script_name="$1"
    local description="$2"
    shift 2
    local args=("$@")
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $script_name (FLAKY - failure expected)"
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
    
    local script_exit_code=0
    if [ ${#args[@]} -gt 0 ]; then
        "$SCRIPT_DIR/$script_name" "${args[@]}" || script_exit_code=$?
    else
        "$SCRIPT_DIR/$script_name" || script_exit_code=$?
    fi
    
    if [ $INTERRUPTED -eq 1 ]; then
        cleanup
    fi
    
    if [ $script_exit_code -eq 130 ] || [ $script_exit_code -eq 143 ]; then
        echo -e "${YELLOW}⚠ INTERRUPTED${NC}"
        cleanup
    fi
    
    if [ $script_exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((FLAKY_PASSED++))
    else
        echo -e "${YELLOW}⚠ XFAIL (exit code: $script_exit_code) - expected, API is flaky${NC}"
        ((FLAKY_FAILED++))
        FLAKY_FAILED_SCRIPTS+=("$script_name")
    fi
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
    run_script "check_all_stations.sh" "Check if all stations in config can be queried" "$CONFIG_FILE"
else
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: check_all_stations.sh"
    echo -e "${YELLOW}⚠ SKIPPED: config.example.toml not found${NC}"
    ((SKIPPED++))
fi

# 2. Analyze complexity script
run_script "analyze_complexity.sh" "Analyze code complexity metrics"

# 3. List routes (MVG)
run_script "list_routes.sh" "List routes for MVG station" "Balanstr."

# 4. List departures (MVG) - base station
run_script "list_departures.sh" "List live departures for MVG station" "de:09162:6" "--limit" "10"

# 5. List departures (MVG) - specific stop point
run_script "list_departures.sh" "List departures for specific stop point (Rotkreuzplatz)" "de:09162:6:1:1" "--limit" "10"

# 6. List routes VBB
run_script "list_routes_vbb.sh" "List routes for VBB station" "blissestr."

# 7. List routes DB (flaky - API often returns 503)
run_script_flaky "list_routes_db.sh" "List routes for DB station (API is flaky)" "blissestr."

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
if [ $FLAKY_PASSED -gt 0 ] || [ $FLAKY_FAILED -gt 0 ]; then
    echo -e "${YELLOW}Flaky tests: $FLAKY_PASSED passed, $FLAKY_FAILED xfailed${NC}"
    if [ $FLAKY_FAILED -gt 0 ]; then
        echo "  (xfailed scripts - expected failures, don't affect exit code):"
        for script in "${FLAKY_FAILED_SCRIPTS[@]}"; do
            echo "    - $script"
        done
    fi
fi
echo ""

# Exit with error if any non-flaky script failed
if [ $FAILED -gt 0 ]; then
    exit 1
fi

exit 0

