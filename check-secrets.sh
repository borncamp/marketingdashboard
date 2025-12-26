#!/bin/bash

###############################################################################
# Security Check Script
# Verifies that no secrets will be committed to git
###############################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "🔒 Security Check - Verifying .gitignore Protection"
echo "=================================================="
echo ""

# Initialize git if needed
if [ ! -d .git ]; then
    git init --quiet
    echo "✓ Git repository initialized"
fi

# Check for sensitive files that would be committed
echo "Checking for sensitive files that would be tracked..."
echo ""

SENSITIVE_PATTERNS=(
    "\.env$"
    "\.env\..*"
    "secret.*\.(json|yaml|yml|txt)$"
    "credential.*\.(json|yaml|yml|txt)$"
    "\.pem$"
    "\.key$"
    "backup/.*\.env"
    "traefik/acme\.json"
)

FOUND_ISSUES=0

for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if git add -n . 2>/dev/null | grep -iE "$pattern" | grep -v "\.example" > /tmp/git-check.txt; then
        if [ -s /tmp/git-check.txt ]; then
            echo -e "${RED}✗ WARNING: Sensitive files matching '$pattern' would be tracked:${NC}"
            cat /tmp/git-check.txt
            echo ""
            FOUND_ISSUES=1
        fi
    fi
done

rm -f /tmp/git-check.txt

if [ $FOUND_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ No sensitive files would be tracked by git${NC}"
    echo ""
fi

# Verify .env.example files ARE tracked
echo "Verifying example files ARE tracked..."
EXAMPLE_FILES=(".env.example" "backend/.env.example" "frontend/.env.example")
ALL_EXAMPLES_OK=1

for file in "${EXAMPLE_FILES[@]}"; do
    if [ -f "$file" ]; then
        if git add -n "$file" 2>/dev/null | grep -q "$file"; then
            echo -e "${GREEN}✓ $file will be tracked${NC}"
        else
            echo -e "${RED}✗ $file will NOT be tracked (should be!)${NC}"
            ALL_EXAMPLES_OK=0
        fi
    fi
done

echo ""
echo "=================================================="

if [ $FOUND_ISSUES -eq 0 ] && [ $ALL_EXAMPLES_OK -eq 1 ]; then
    echo -e "${GREEN}✅ Security check PASSED${NC}"
    echo ""
    echo "Safe to commit:"
    echo "  • .env files are ignored"
    echo "  • .env.example files are tracked"
    echo "  • Secrets and credentials are protected"
    echo "  • SSL certificates are ignored"
    echo "  • Backup files are ignored"
    echo ""
    exit 0
else
    echo -e "${RED}❌ Security check FAILED${NC}"
    echo ""
    echo "Please fix the issues above before committing!"
    echo ""
    exit 1
fi
