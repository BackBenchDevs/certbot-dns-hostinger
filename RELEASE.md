# Release Process

This document describes how to release `certbot-dns-hostinger` to PyPI.

## Automated Release via GitHub Actions

The package is automatically published to PyPI when a tag or release is created.

### Prerequisites

#### Option 1: Trusted Publishing (Recommended - No Tokens!)

PyPI supports [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) which uses OIDC to authenticate without API tokens.

1. Go to [PyPI account settings](https://pypi.org/manage/account/publishing/)
2. Scroll to "Pending publishers" or "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `certbot-dns-hostinger`
   - **Owner**: `BackBenchDevs`
   - **Repository name**: `certbot-dns-hostinger`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`

That's it! No tokens needed.

#### Option 2: API Token (Legacy)

1. Generate PyPI API token at https://pypi.org/manage/account/token/
2. Add to GitHub repository secrets:
   - Go to `Settings` > `Secrets and variables` > `Actions`
   - Click `New repository secret`
   - Name: `PYPI_API_TOKEN`
   - Value: Your PyPI token (starts with `pypi-`)

Then update `.github/workflows/publish.yml`:
```yaml
- name: Publish to PyPI
  uses: pypa/gh-action-pypi-publish@release/v1
  with:
    password: ${{ secrets.PYPI_API_TOKEN }}
```

### Release Steps

#### From Staging Branch (Production Release)

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "0.1.0"  # Remove .dev suffix
   ```

2. **Commit and push** to staging:
   ```bash
   git add pyproject.toml
   git commit -m "Release v0.1.0"
   git push origin staging
   ```

3. **Create and push tag**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. **Create GitHub Release**:
   - Go to https://github.com/BackBenchDevs/certbot-dns-hostinger/releases/new
   - Select tag: `v0.1.0`
   - Title: `v0.1.0`
   - Generate release notes or write changelog
   - Click "Publish release"

5. **GitHub Actions will automatically**:
   - Build the package using `uv build`
   - Run tests (from tests.yml workflow)
   - Publish to PyPI (from publish.yml workflow)

6. **Update version for next dev cycle** on master:
   ```bash
   git checkout master
   # Update version to 0.2.0.dev1
   git add pyproject.toml
   git commit -m "Bump version to 0.2.0.dev1"
   git push origin master
   ```

#### Test Release (TestPyPI)

To test the release process without publishing to production PyPI:

```bash
# Trigger workflow manually (goes to TestPyPI)
gh workflow run publish.yml
```

Or go to GitHub Actions > Publish to PyPI > Run workflow

### What Happens Automatically

When you push a tag (`v*`):

1. **Build Job**:
   - Checks out code
   - Installs uv
   - Builds package: `uv build`
   - Creates `dist/certbot_dns_hostinger-X.Y.Z.tar.gz` and `.whl`
   - Uploads artifacts

2. **Publish Job**:
   - Downloads build artifacts
   - Publishes to PyPI using trusted publishing or API token
   - Package appears at: https://pypi.org/project/certbot-dns-hostinger/

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Development**: `0.2.0.dev1`, `0.2.0.dev2`, etc.
- **Release Candidate**: `0.2.0rc1` (optional)
- **Production**: `0.1.0`, `0.2.0`, `1.0.0`, etc.
- **Patch**: `0.1.1`, `0.1.2`, etc.

### Branch Strategy

- **master**: Development (version: `X.Y.Z.dev1`)
- **staging**: Pre-release (version: `X.Y.Z` or `X.Y.Zrc1`)
- **Tags**: Created from staging for releases

### Manual Release (Fallback)

If automated release fails:

```bash
# Build
uv build

# Check built files
ls -lh dist/

# Upload to PyPI
uv publish

# Or to TestPyPI
uv publish --publish-url https://test.pypi.org/legacy/
```

### Verify Release

After release:

1. Check PyPI: https://pypi.org/project/certbot-dns-hostinger/
2. Test installation:
   ```bash
   pip install certbot-dns-hostinger
   certbot plugins | grep hostinger
   ```

### Rollback

If a release has issues:

1. **Yank the release** on PyPI (doesn't delete, just marks as broken)
2. **Fix the issue** on master
3. **Cherry-pick to staging** when stable
4. **Release new version** (can't re-upload same version)

### Troubleshooting

**"File already exists"**: Can't upload same version twice. Bump version and re-release.

**"Invalid credentials"**: Check GitHub secrets or PyPI trusted publisher setup.

**"Tests failed"**: Fix tests on master, cherry-pick to staging, try again.

## First-Time Setup Checklist

- [ ] Set up PyPI trusted publishing (or add API token to GitHub secrets)
- [ ] Verify tests pass on staging branch
- [ ] Update version in `pyproject.toml` (remove `.dev`)
- [ ] Create and push tag: `git tag v0.1.0 && git push origin v0.1.0`
- [ ] Create GitHub release
- [ ] Verify package on PyPI
- [ ] Test install: `pip install certbot-dns-hostinger`

