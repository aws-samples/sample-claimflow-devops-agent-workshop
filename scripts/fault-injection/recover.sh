#!/bin/bash
set -e

# ──────────────────────────────────────────────────────────────
# Recovery Script — DevOps Agent Demo
#
# Restores all services to healthy state after fault injection.
# Run this between scenarios or at the end of the demo.
#
# Usage:
#   ./recover.sh [aws-profile]
#   ./recover.sh [aws-profile] --verify-only
#
# Provide an AWS profile name to use named credentials, or omit it to use the
# ambient credentials in your environment (for example, in AWS CloudShell).
#
# Examples:
#   ./recover.sh                       # use ambient credentials (CloudShell)
#   ./recover.sh --verify-only
#   ./recover.sh my-profile
#   ./recover.sh my-profile --verify-only
# ──────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
    echo ""
    echo -e "${CYAN}Recovery — DevOps Agent Demo${NC}"
    echo ""
    echo "Usage: ./recover.sh [aws-profile] [--verify-only]"
    echo ""
    echo "Provide an AWS profile name to use named credentials, or omit it to use"
    echo "the ambient credentials in your environment (for example, in CloudShell)."
    echo ""
    echo "Options:"
    echo "  --verify-only    Only check service health, don't make changes"
    echo ""
    echo "Examples:"
    echo "  ./recover.sh"
    echo "  ./recover.sh --verify-only"
    echo "  ./recover.sh my-profile"
    echo "  ./recover.sh my-profile --verify-only"
    echo ""
    exit 1
}

# The first argument is an optional profile name. Anything starting with "-" is
# treated as an option, not a profile.
PROFILE=""
if [ $# -gt 0 ] && [[ "$1" != -* ]]; then
    PROFILE="$1"
    shift
fi

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
echo -e "${CYAN}  RECOVERING — Restoring All Services${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""

python3 "$SCRIPT_DIR/recover_all.py" $PROFILE_ARG $EXTRA_ARGS

echo ""
echo -e "${GREEN}  System recovered. Ready for next scenario or demo.${NC}"
echo ""
