# Release Process

This document describes how to release `certbot-dns-hostinger` to PyPI.

## Branch Strategy

- **master**: Development branch (version: `X.Y.Z.dev1`)
- **staging**: Release preparation (cherry-picked stable commits)
- **Tags**: Created from staging for releases (`vX.Y.Z`)

## Automated Release (Recommended)

### Prerequisites

1. **GitHub CLI** installed and authenticated: `gh auth login`
2. **PyPI Trusted Publishing** configured (see [Setup](#first-time-setup-checklist))
3. **Branch/tag rulesets** applied (see `.github/rulesets/`)

### Release Steps

```bash
# 1. Run the release orchestrator
./scripts/release_orchestrator.sh v1.2.3 <commit1> <commit2> ...

# Examples:
./scripts/release_orchestrator.sh v0.2.0 abc123 def456 ghi789
./scripts/release_orchestrator.sh v0.2.0 master~5..master  # range
```

### What Happens Automatically

1. **For each commit**:
   - Cherry-picks onto staging branch
   - Pushes to origin/staging
   - Waits for CI (test 3.11, test 3.12, lint) to pass
   - On failure: reverts commit, creates GitHub issue, aborts

2. **After all commits pass**:
   - Triggers `Create Release Tag` workflow
   - Updates version in `pyproject.toml`
   - Creates annotated tag `vX.Y.Z`
   - Creates GitHub Release with auto-generated notes
   - `publish.yml` triggers automatically to push to PyPI

### Manual Workflow Trigger

If you prefer to create the tag manually after cherry-picks:

```bash
gh workflow run "Create Release Tag" -f version=v1.2.3 -f create_release=true
```

Or via GitHub UI: **Actions → Create Release Tag → Run workflow**

---

## Manual Release (Fallback)

If automation fails, you can release manually:

### 1. Cherry-pick commits to staging

```bash
git checkout staging
git pull origin staging
git cherry-pick <commit-hash>
git push origin staging
# Wait for CI to pass, then repeat for each commit
```

### 2. Update version

```bash
# Edit pyproject.toml
version = "0.2.0"  # Remove .dev suffix

git add pyproject.toml
git commit -m "chore: release v0.2.0"
git push origin staging
```

### 3. Create and push tag

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### 4. Create GitHub Release

- Go to https://github.com/BackBenchDevs/certbot-dns-hostinger/releases/new
- Select tag: `v0.2.0`
- Generate release notes
- Publish

### 5. Bump version for next dev cycle

```bash
git checkout master
# Update version to 0.3.0.dev1
git add pyproject.toml
git commit -m "chore: bump version to 0.3.0.dev1"
git push origin master
```

---

## PyPI Publishing

### Trusted Publishing (Recommended)

No tokens needed. Configure at [PyPI](https://pypi.org/manage/account/publishing/):

| Field | Value |
|-------|-------|
| Project Name | `certbot-dns-hostinger` |
| Owner | `BackBenchDevs` |
| Repository | `certbot-dns-hostinger` |
| Workflow | `publish.yml` |
| Environment | `pypi` |

### Manual Upload (Fallback)

```bash
uv build
uv publish
```

---

## Rulesets

Apply rulesets via GitHub UI or API:

```bash
# Apply master ruleset
gh api repos/BackBenchDevs/certbot-dns-hostinger/rulesets \
  --method POST \
  --input .github/rulesets/master.json

# Apply staging ruleset
gh api repos/BackBenchDevs/certbot-dns-hostinger/rulesets \
  --method POST \
  --input .github/rulesets/staging.json

# Apply tag ruleset
gh api repos/BackBenchDevs/certbot-dns-hostinger/rulesets \
  --method POST \
  --input .github/rulesets/release-tags.json
```

---

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

| Type | Format | Example |
|------|--------|---------|
| Development | `X.Y.Z.dev1` | `0.2.0.dev1` |
| Release Candidate | `X.Y.Zrc1` | `0.2.0rc1` |
| Production | `X.Y.Z` | `0.2.0` |
| Patch | `X.Y.Z` | `0.2.1` |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cherry-pick conflict | Resolve manually, then retry |
| CI timeout | Check Actions logs, increase `CI_POLL_TIMEOUT` |
| "File already exists" on PyPI | Can't re-upload same version; bump and retry |
| Tag already exists | Delete tag or use different version |

---

## First-Time Setup Checklist

- [ ] Set up PyPI trusted publishing
- [ ] Install GitHub CLI: `gh auth login`
- [ ] Apply rulesets (see above)
- [ ] Make `release_orchestrator.sh` executable: `chmod +x scripts/release_orchestrator.sh`
- [ ] Test with a pre-release: `./scripts/release_orchestrator.sh v0.2.0-rc1 <commit>`

---

## Verify Release

```bash
# Check PyPI
pip index versions certbot-dns-hostinger

# Test install
pip install certbot-dns-hostinger
certbot plugins | grep hostinger
```
