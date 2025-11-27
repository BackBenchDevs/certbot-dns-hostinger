# Tests

This directory contains the comprehensive test suite for `certbot-dns-hostinger`.

## Test Structure

- `conftest.py` - Pytest fixtures and test utilities
- `test_root_domain.py` - Tests for root domain extraction logic
- `test_hostinger_client.py` - Tests for the Hostinger API client
- `test_authenticator.py` - Tests for the Certbot authenticator plugin
- `test_integration.py` - Integration tests for end-to-end flows
- `test_dns_hostinger.py` - Basic package structure and import tests

## Running Tests

### Using uv (Recommended)

```bash
# Sync all dependencies including dev/test deps
uv sync --all-extras

# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_root_domain.py

# Run with verbose output
uv run pytest -v

# Run with coverage report
uv run pytest --cov=certbot_dns_hostinger --cov-report=html
```

### Using pip

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=certbot_dns_hostinger --cov-report=html
```

## Test Coverage

The test suite aims for ≥80% code coverage. Coverage reports are generated in:
- Terminal: Shown after test run
- HTML: `htmlcov/index.html`
- XML: `coverage.xml` (for CI/CD)

## Writing Tests

### Fixtures

Common fixtures are available in `conftest.py`:
- `api_token` - Mock API token
- `test_domain` - Test domain name
- `mock_api_client` - Mock Hostinger API client
- `credentials_file` - Temporary credentials file
- `mock_dns_records` - Sample DNS records

### Example Test

```python
def test_add_txt_record(api_token, test_domain):
    """Test adding a TXT record."""
    client = _HostingerClient(api_token)
    client.add_txt_record(test_domain, "_acme-challenge.example.com", "content", 300)
    # assertions...
```

## CI/CD

Tests run automatically on GitHub Actions for:
- Python 3.9, 3.10, 3.11, 3.12
- On push to main/develop branches
- On pull requests

See `.github/workflows/tests.yml` for CI configuration.

