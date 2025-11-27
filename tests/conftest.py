"""Pytest fixtures for certbot-dns-hostinger tests."""

import pytest
from unittest.mock import MagicMock, Mock
from typing import List, Dict, Any


@pytest.fixture
def api_token() -> str:
    """Return a test API token."""
    return "test_token_123456789"


@pytest.fixture
def test_domain() -> str:
    """Return a test domain."""
    return "bbdevs.com"


@pytest.fixture
def test_subdomain() -> str:
    """Return a test subdomain."""
    return "sso.bbdevs.com"


@pytest.fixture
def test_record_name() -> str:
    """Return a test record name for ACME challenge."""
    return "_acme-challenge.bbdevs.com"


@pytest.fixture
def test_record_content() -> str:
    """Return a test TXT record content."""
    return "test-acme-challenge-content-123"


@pytest.fixture
def test_ttl() -> int:
    """Return a test TTL value."""
    return 300


@pytest.fixture
def mock_dns_record() -> Dict[str, Any]:
    """Return a mock DNS record."""
    mock_record = Mock()
    mock_record.name = "_acme-challenge"
    mock_record.type = "TXT"
    mock_record.content = "old-challenge-content"
    mock_record.ttl = 300
    mock_record.is_disabled = False
    return mock_record


@pytest.fixture
def mock_dns_records() -> List[Any]:
    """Return a list of mock DNS records."""
    records = []

    # A record
    a_record = Mock()
    a_record.name = "@"
    a_record.type = "A"
    a_record.content = "192.0.2.1"
    a_record.ttl = 3600
    a_record.is_disabled = False
    records.append(a_record)

    # CNAME record
    cname_record = Mock()
    cname_record.name = "www"
    cname_record.type = "CNAME"
    cname_record.content = "bbdevs.com"
    cname_record.ttl = 3600
    cname_record.is_disabled = False
    records.append(cname_record)

    # Existing ACME challenge
    acme_record = Mock()
    acme_record.name = "_acme-challenge"
    acme_record.type = "TXT"
    acme_record.content = "old-challenge-content"
    acme_record.ttl = 300
    acme_record.is_disabled = False
    records.append(acme_record)

    return records


@pytest.fixture
def mock_api_client(mock_dns_records):
    """Return a mock Hostinger API client."""
    client = Mock()
    client.get_dns_records_v1 = Mock(return_value=mock_dns_records)
    client.update_dns_records_v1 = Mock(return_value=None)
    client.delete_dns_records_v1 = Mock(return_value=None)
    return client


@pytest.fixture
def mock_configuration():
    """Return a mock Hostinger API Configuration."""
    config = Mock()
    config.access_token = "test_token_123456789"
    return config


@pytest.fixture
def mock_certbot_config():
    """Return a mock certbot configuration."""
    config = Mock()
    config.verb = "certonly"
    config.config_dir = "/tmp/letsencrypt"
    config.work_dir = "/tmp/letsencrypt/work"
    config.logs_dir = "/tmp/letsencrypt/logs"
    return config


@pytest.fixture
def credentials_file(tmp_path, api_token):
    """Create a temporary credentials file."""
    creds_file = tmp_path / "hostinger.ini"
    creds_file.write_text(f"dns_hostinger_api_token = {api_token}\n")
    # Make file readable only by owner
    creds_file.chmod(0o600)
    return str(creds_file)


@pytest.fixture
def mock_hostinger_client(api_token):
    """Return a mock _HostingerClient instance."""
    from certbot_dns_hostinger._internal.dns_hostinger import _HostingerClient

    client = _HostingerClient(api_token)
    return client


@pytest.fixture
def sample_get_dns_response() -> List[Dict[str, Any]]:
    """Return a sample GET DNS records API response."""
    return [
        {
            "id": "1",
            "name": "@",
            "type": "A",
            "content": "192.0.2.1",
            "ttl": 3600,
            "is_disabled": False,
        },
        {
            "id": "2",
            "name": "www",
            "type": "CNAME",
            "content": "bbdevs.com",
            "ttl": 3600,
            "is_disabled": False,
        },
        {
            "id": "3",
            "name": "_acme-challenge",
            "type": "TXT",
            "content": "old-challenge",
            "ttl": 300,
            "is_disabled": False,
        },
    ]


@pytest.fixture
def sample_update_dns_request() -> Dict[str, Any]:
    """Return a sample UPDATE DNS records API request."""
    return {
        "zone": [
            {
                "name": "_acme-challenge",
                "type": "TXT",
                "ttl": 300,
                "records": [{"content": "new-challenge-content"}],
            }
        ],
        "overwrite": False,
    }


@pytest.fixture
def sample_delete_dns_request() -> Dict[str, Any]:
    """Return a sample DELETE DNS records API request."""
    return {"filters": [{"name": "_acme-challenge", "type": "TXT"}]}
