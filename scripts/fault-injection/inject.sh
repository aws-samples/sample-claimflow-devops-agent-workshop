#!/bin/bash
set -e

# ──────────────────────────────────────────────────────────────
# Fault Injection Script — DevOps Agent Demo
#
# Usage:
#   ./inject.sh <scenario> [aws-profile]
#
# Provide an AWS profile name to use named credentials, or omit it to use the
# ambient credentials in your environment (for example, in AWS CloudShell).
#
# Scenarios:
#   1 | bad-query       — High CPU (bad INNER JOIN on claim-service)
#   2 | memory-sidecar  — OOM Kill (memory leak on fraud-service)
#   3 | ddos            — DDoS HTTP flood (attacker ECS tasks)
#
# Examples:
#   ./inject.sh 1                  # use ambient credentials (CloudShell)
#   ./inject.sh 1 my-profile       # use a named profile
#   ./inject.sh bad-query my-profile
#   ./inject.sh ddos my-profile --attackers 5
# ──────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo ""
    echo -e "${CYAN}Fault Injection — DevOps Agent Demo${NC}"
    echo ""
    echo "Usage: ./inject.sh <scenario> [aws-profile] [options]"
    echo ""
    echo "Provide an AWS profile name to use named credentials, or omit it to use"
    echo "the ambient credentials in your environment (for example, in CloudShell)."
    echo ""
    echo "Scenarios:"
    echo "  1 | bad-query        Scenario 1: Bad INNER JOIN query (High CPU on claim-service)"
    echo "  2 | memory-sidecar   Scenario 2: ML model sidecar memory leak (OOM on fraud-service)"
    echo "  3 | ddos             Scenario 3: DDoS HTTP flood (attacker ECS tasks)"
    echo ""
    echo "Options (Scenario 3 only):"
    echo "  --attackers N        Number of attacker tasks (default: 50)"
    echo "  --duration N         Attack duration in seconds (default: 600)"
    echo ""
    echo "  The defaults are tuned to reliably drive claim-service CPU past the"
    echo "  alarm threshold. Lower values may not raise the alarm."
    echo ""
    echo "Examples:"
    echo "  ./inject.sh 1"
    echo "  ./inject.sh 1 my-profile"
    echo "  ./inject.sh memory-sidecar my-profile"
    echo "  ./inject.sh 3 my-profile --attackers 5 --duration 180"
    echo ""
    exit 1
}

if [ $# -lt 1 ]; then
    usage
fi

SCENARIO="$1"
shift

# The next argument is an optional profile name. Anything starting with "-" is
# treated as an option (for scenario 3), not a profile.
PROFILE=""
if [ $# -gt 0 ] && [[ "$1" != -* ]]; then
    PROFILE="$1"
    shift
fi

# Parse extra args for scenario 3
EXTRA_ARGS=""
while [ $# -gt 0 ]; do
    EXTRA_ARGS="$EXTRA_ARGS $1"
    shift
done

# Build the --profile argument only when a profile was supplied.
PROFILE_ARG=""
if [ -n "$PROFILE" ]; then
    PROFILE_ARG="--profile $PROFILE"
    aws sts get-caller-identity --profile "$PROFILE" > /dev/null 2>&1 || {
        echo -e "${RED}Error: AWS profile '$PROFILE' is not valid or not configured.${NC}"
        exit 1
    }
else
    aws sts get-caller-identity > /dev/null 2>&1 || {
        echo -e "${RED}Error: no valid AWS credentials found in the environment.${NC}"
        exit 1
    }
fi

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"

case "$SCENARIO" in
    1|bad-query)
        echo -e "${CYAN}  INJECTING SCENARIO 1: Bad Query (High CPU)${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}  Target:${NC}  claim-service"
        echo -e "${YELLOW}  Fault:${NC}   Expensive INNER JOIN query burning CPU"
        echo -e "${YELLOW}  Effect:${NC}  CPU spikes to 80-100%, API latency degrades"
        echo ""
        python3 "$SCRIPT_DIR/inject_bad_query.py" $PROFILE_ARG
        ;;
    2|memory-sidecar)
        echo -e "${CYAN}  INJECTING SCENARIO 2: Memory-Stress Sidecar (OOM Kill)${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}  Target:${NC}  fraud-service"
        echo -e "${YELLOW}  Fault:${NC}   ML model sidecar leaking memory (5MB/2s)"
        echo -e "${YELLOW}  Effect:${NC}  Task OOM-killed, crash loop, fraud API down"
        echo ""
        python3 "$SCRIPT_DIR/inject_memory_sidecar.py" $PROFILE_ARG
        ;;
    3|ddos)
        echo -e "${CYAN}  INJECTING SCENARIO 3: DDoS Attack (HTTP Flood)${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}  Target:${NC}  claim-service (via internal VPC)"
        echo -e "${YELLOW}  Fault:${NC}   Attacker ECS tasks flooding HTTP requests"
        echo -e "${YELLOW}  Effect:${NC}  Request spike, high latency, possible 5xx"
        echo ""
        python3 "$SCRIPT_DIR/inject_ddos.py" $PROFILE_ARG $EXTRA_ARGS
        ;;
    *)
        echo -e "${RED}  Unknown scenario: $SCENARIO${NC}"
        echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
        usage
        ;;
esac

echo ""
echo -e "${GREEN}  Injection complete. Monitor the DevOps Agent for investigation.${NC}"
echo -e "${GREEN}  When ready to recover, run: ./recover.sh '$PROFILE'${NC}"
echo ""
