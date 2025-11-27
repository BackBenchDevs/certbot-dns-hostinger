#!/usr/bin/env bash
#
# Release Orchestrator for certbot-dns-hostinger
#
# Cherry-picks commits from master to staging one-by-one, waits for CI to pass
# for each commit, then triggers the create-release-tag workflow.
#
# Usage:
#   ./scripts/release_orchestrator.sh v1.2.3 <commit1> [commit2] [commit3] ...
#   ./scripts/release_orchestrator.sh v1.2.3 abc123 def456 ghi789
#   ./scripts/release_orchestrator.sh v1.2.3 master~3..master  # range
#
# Requirements:
#   - GitHub CLI (gh) installed and authenticated
#   - Git configured with push access to origin
#   - Environment variables (or defaults used):
#     - GITHUB_REPOSITORY: owner/repo (auto-detected if in git repo)
#     - CI_POLL_INTERVAL: seconds between status checks (default: 20)
#     - CI_POLL_TIMEOUT: max seconds to wait for CI (default: 1800 = 30min)
#
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# Configuration
REPO="${GITHUB_REPOSITORY:-$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")}"
CI_POLL_INTERVAL="${CI_POLL_INTERVAL:-20}"
CI_POLL_TIMEOUT="${CI_POLL_TIMEOUT:-1800}"
REQUIRED_CHECKS=("test (3.11)" "test (3.12)" "lint")

# Validate inputs
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <version-tag> <commit1> [commit2] ..."
    echo "       $0 <version-tag> <commit-range>"
    echo ""
    echo "Examples:"
    echo "  $0 v1.2.3 abc123 def456"
    echo "  $0 v1.2.3 master~5..master"
    exit 1
fi

TAG="$1"
shift

# Validate tag format
if [[ ! "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
    log_error "Invalid tag format: $TAG (expected v*.*.* e.g. v1.2.3)"
    exit 1
fi

# Validate repository
if [[ -z "$REPO" ]]; then
    log_error "Could not determine repository. Set GITHUB_REPOSITORY or run from git repo."
    exit 1
fi

log_info "Repository: $REPO"
log_info "Target tag: $TAG"

# Expand commit range if provided (e.g., master~3..master)
COMMITS=()
for arg in "$@"; do
    if [[ "$arg" == *".."* ]]; then
        # It's a range, expand it
        while IFS= read -r commit; do
            COMMITS+=("$commit")
        done < <(git rev-list --reverse "$arg")
    else
        COMMITS+=("$arg")
    fi
done

if [[ ${#COMMITS[@]} -eq 0 ]]; then
    log_error "No commits to cherry-pick"
    exit 1
fi

log_info "Commits to cherry-pick: ${#COMMITS[@]}"
for c in "${COMMITS[@]}"; do
    log_info "  - $c ($(git log -1 --format='%s' "$c" 2>/dev/null || echo 'unknown'))"
done

echo ""
read -p "Proceed with cherry-pick to staging? [y/N] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Aborted by user"
    exit 0
fi

# Function to get CI status using check-runs API (works with GitHub Actions)
get_ci_status() {
    local sha="$1"
    local check_status
    
    # Get all check runs for this commit
    check_status=$(gh api "repos/$REPO/commits/$sha/check-runs" \
        --jq '{
            total: .total_count,
            completed: [.check_runs[] | select(.status == "completed")] | length,
            success: [.check_runs[] | select(.status == "completed" and .conclusion == "success")] | length,
            failure: [.check_runs[] | select(.status == "completed" and (.conclusion == "failure" or .conclusion == "cancelled"))] | length,
            pending: [.check_runs[] | select(.status != "completed")] | length,
            names: [.check_runs[].name]
        }' 2>/dev/null) || echo '{"total":0}'
    
    local total completed success failure pending
    total=$(echo "$check_status" | jq -r '.total // 0')
    completed=$(echo "$check_status" | jq -r '.completed // 0')
    success=$(echo "$check_status" | jq -r '.success // 0')
    failure=$(echo "$check_status" | jq -r '.failure // 0')
    pending=$(echo "$check_status" | jq -r '.pending // 0')
    
    # Check if all required checks are present and successful
    local required_found=0
    for check in "${REQUIRED_CHECKS[@]}"; do
        if echo "$check_status" | jq -e --arg name "$check" '.names | index($name)' >/dev/null 2>&1; then
            ((required_found++))
        fi
    done
    
    if [[ $failure -gt 0 ]]; then
        echo "failure"
    elif [[ $total -eq 0 ]] || [[ $required_found -lt ${#REQUIRED_CHECKS[@]} ]]; then
        echo "pending"
    elif [[ $pending -gt 0 ]]; then
        echo "pending"
    elif [[ $success -eq $completed ]] && [[ $completed -gt 0 ]]; then
        echo "success"
    else
        echo "pending"
    fi
}

# Function to wait for CI
wait_for_ci() {
    local sha="$1"
    local elapsed=0
    
    log_info "Waiting for CI checks on $sha..."
    
    while true; do
        local status
        status=$(get_ci_status "$sha")
        
        case "$status" in
            success)
                log_ok "CI passed for $sha"
                return 0
                ;;
            failure)
                log_error "CI failed for $sha"
                return 1
                ;;
            pending)
                printf "\r  ⏳ Status: pending (%ds / %ds)" "$elapsed" "$CI_POLL_TIMEOUT"
                ;;
        esac
        
        sleep "$CI_POLL_INTERVAL"
        elapsed=$((elapsed + CI_POLL_INTERVAL))
        
        if [[ $elapsed -ge $CI_POLL_TIMEOUT ]]; then
            echo ""
            log_error "Timeout waiting for CI ($CI_POLL_TIMEOUT seconds)"
            return 2
        fi
    done
}

# Ensure we're up to date
log_info "Fetching latest from origin..."
git fetch origin

# Checkout staging
log_info "Checking out staging branch..."
git checkout staging
git reset --hard origin/staging

# Track successful cherry-picks for potential rollback
SUCCESSFUL_PICKS=()

# Cherry-pick each commit
for commit in "${COMMITS[@]}"; do
    echo ""
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "Cherry-picking: $commit"
    log_info "Message: $(git log -1 --format='%s' "$commit")"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Try cherry-pick
    if ! git cherry-pick "$commit"; then
        log_error "Cherry-pick failed for $commit"
        log_error "Conflict detected. Aborting cherry-pick and resetting staging."
        
        git cherry-pick --abort 2>/dev/null || true
        git reset --hard origin/staging
        
        # Create issue for tracking
        gh issue create \
            --title "🚨 Cherry-pick failed: $(git log -1 --format='%s' "$commit" | head -c 50)" \
            --body "Cherry-pick of commit \`$commit\` onto staging failed due to conflicts.

**Commit:** $commit
**Message:** $(git log -1 --format='%s' "$commit")
**Author:** $(git log -1 --format='%an <%ae>' "$commit")

Please resolve manually and retry the release." \
            --label "release-blocker" 2>/dev/null || log_warn "Could not create issue"
        
        exit 2
    fi
    
    # Push this single commit
    log_info "Pushing to origin/staging..."
    git push origin staging
    
    # Get the new HEAD SHA
    NEW_SHA=$(git rev-parse HEAD)
    log_info "Pushed commit: $NEW_SHA"
    
    # Wait for CI
    echo ""
    if ! wait_for_ci "$NEW_SHA"; then
        log_error "CI failed or timed out for commit $commit"
        log_info "Reverting the failed commit..."
        
        git revert --no-edit HEAD
        git push origin staging
        
        # Create issue
        gh issue create \
            --title "🚨 Staging CI failed: $(git log -1 --format='%s' "$commit" | head -c 50)" \
            --body "CI failed on staging after cherry-picking commit \`$commit\`.

**Original commit:** $commit
**Staging commit:** $NEW_SHA
**Message:** $(git log -1 --format='%s' "$commit")

The commit has been automatically reverted. Please investigate and fix.

[View CI run](https://github.com/$REPO/commit/$NEW_SHA/checks)" \
            --label "release-blocker" 2>/dev/null || log_warn "Could not create issue"
        
        exit 3
    fi
    
    SUCCESSFUL_PICKS+=("$commit")
    log_ok "Successfully cherry-picked and validated: $commit"
done

echo ""
log_ok "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log_ok "All ${#COMMITS[@]} commits cherry-picked and validated!"
log_ok "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Trigger the create-release-tag workflow
echo ""
log_info "Triggering 'Create Release Tag' workflow for $TAG..."

if gh workflow run "Create Release Tag" -f version="$TAG" -f create_release=true -f prerelease=false; then
    log_ok "Workflow triggered successfully!"
    echo ""
    log_info "Monitor progress at:"
    log_info "  https://github.com/$REPO/actions/workflows/create-release-tag.yml"
else
    log_warn "Could not trigger workflow. You can trigger manually:"
    log_info "  gh workflow run 'Create Release Tag' -f version=$TAG"
fi

echo ""
log_ok "🎉 Release orchestration complete for $TAG"

