"""Tests for _HostingerClient class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from certbot import errors
from certbot_dns_hostinger._internal.dns_hostinger import _HostingerClient


class TestHostingerClientInit:
    """Test _HostingerClient initialization."""

    def test_client_initialization(self, api_token):
        """Test that client initializes correctly."""
        client = _HostingerClient(api_token)
        assert client.api_token == api_token
        assert client._api_client is None

    def test_client_stores_token(self, api_token):
        """Test that API token is stored."""
        client = _HostingerClient(api_token)
        assert hasattr(client, "api_token")
        assert client.api_token == api_token


class TestGetAPIClient:
    """Test _get_api_client method."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.Configuration")
    @patch("certbot_dns_hostinger._internal.dns_hostinger.ApiClient")
    @patch("certbot_dns_hostinger._internal.dns_hostinger.DNSZoneApi")
    def test_api_client_initialization(self, mock_dns_api, mock_api_client, mock_config, api_token):
        """Test that API client initializes on first call."""
        client = _HostingerClient(api_token)

        # First call should initialize
        api_client = client._get_api_client()

        mock_config.assert_called_once_with(access_token=api_token)
        mock_api_client.assert_called_once()
        mock_dns_api.assert_called_once()
        assert api_client is not None

    @patch("certbot_dns_hostinger._internal.dns_hostinger.Configuration")
    @patch("certbot_dns_hostinger._internal.dns_hostinger.ApiClient")
    @patch("certbot_dns_hostinger._internal.dns_hostinger.DNSZoneApi")
    def test_api_client_caching(self, mock_dns_api, mock_api_client, mock_config, api_token):
        """Test that API client is cached after first initialization."""
        client = _HostingerClient(api_token)

        # First call
        api_client1 = client._get_api_client()
        # Second call should return cached client
        api_client2 = client._get_api_client()

        # Should only initialize once
        mock_config.assert_called_once()
        mock_api_client.assert_called_once()
        mock_dns_api.assert_called_once()
        assert api_client1 is api_client2

    @patch(
        "certbot_dns_hostinger._internal.dns_hostinger.DNSZoneApi",
        side_effect=ImportError("Module not found"),
    )
    def test_api_client_import_error(self, mock_dns_api, api_token):
        """Test that ImportError is caught and raises PluginError."""
        client = _HostingerClient(api_token)

        with pytest.raises(errors.PluginError) as exc_info:
            client._get_api_client()

        assert "Could not import hostinger-api" in str(exc_info.value)


class TestAddTxtRecord:
    """Test add_txt_record method."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_add_txt_record_simple_domain(
        self,
        mock_get_client,
        api_token,
        test_domain,
        test_record_name,
        test_record_content,
        test_ttl,
    ):
        """Test adding TXT record for simple domain."""
        # Setup mocks
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record(test_domain, test_record_name, test_record_content, test_ttl)

        # Verify API calls
        mock_api.get_dns_records_v1.assert_called_once_with(test_domain)
        mock_api.update_dns_records_v1.assert_called_once()

    @patch.object(_HostingerClient, "_get_api_client")
    def test_add_txt_record_with_existing_acme_record(
        self, mock_get_client, api_token, test_domain, mock_dns_records
    ):
        """Test adding TXT record when ACME challenge record already exists."""
        # Setup mocks
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=mock_dns_records)
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record(test_domain, "_acme-challenge.bbdevs.com", "new-content", 300)

        # Verify DELETE was called to remove existing record
        mock_api.delete_dns_records_v1.assert_called_once()
        mock_api.update_dns_records_v1.assert_called_once()

    @patch.object(_HostingerClient, "_get_api_client")
    def test_add_txt_record_subdomain(self, mock_get_client, api_token):
        """Test adding TXT record for subdomain uses root domain."""
        # Setup mocks
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        # Request for sso.bbdevs.com should use bbdevs.com zone
        client.add_txt_record("sso.bbdevs.com", "_acme-challenge.sso.bbdevs.com", "content", 300)

        # Verify API was called with root domain
        mock_api.get_dns_records_v1.assert_called_once_with("bbdevs.com")
        mock_api.update_dns_records_v1.assert_called_once()

        # Verify the subdomain in the update call
        call_args = mock_api.update_dns_records_v1.call_args
        assert call_args[0][0] == "bbdevs.com"  # First positional arg should be root domain

    @patch.object(_HostingerClient, "_get_api_client")
    def test_add_txt_record_uses_overwrite_false(self, mock_get_client, api_token, test_domain):
        """Test that add_txt_record uses overwrite=False."""
        # Setup mocks
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record(test_domain, "_acme-challenge.bbdevs.com", "content", 300)

        # Verify update was called with a request object
        mock_api.update_dns_records_v1.assert_called_once()
        call_args = mock_api.update_dns_records_v1.call_args
        request_obj = call_args[0][1]  # Second positional arg is the request object

        # The request object should have overwrite=False
        assert hasattr(request_obj, "overwrite")
        assert request_obj.overwrite is False

    @patch.object(_HostingerClient, "_get_api_client")
    def test_add_txt_record_api_error(self, mock_get_client, api_token, test_domain):
        """Test that API errors are caught and re-raised as PluginError."""
        # Setup mocks to raise an exception
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        with pytest.raises(errors.PluginError) as exc_info:
            client.add_txt_record(test_domain, "_acme-challenge.bbdevs.com", "content", 300)

        assert "Encountered error adding TXT record" in str(exc_info.value)


class TestDelTxtRecord:
    """Test del_txt_record method."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_del_txt_record_simple_domain(self, mock_get_client, api_token, test_domain):
        """Test deleting TXT record for simple domain."""
        # Setup mocks
        mock_api = Mock()
        mock_api.delete_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.del_txt_record(test_domain, "_acme-challenge.bbdevs.com", "content")

        # Verify DELETE was called
        mock_api.delete_dns_records_v1.assert_called_once_with(test_domain, pytest.any)

    @patch.object(_HostingerClient, "_get_api_client")
    def test_del_txt_record_subdomain(self, mock_get_client, api_token):
        """Test deleting TXT record for subdomain uses root domain."""
        # Setup mocks
        mock_api = Mock()
        mock_api.delete_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        # Request for sso.bbdevs.com should use bbdevs.com zone
        client.del_txt_record("sso.bbdevs.com", "_acme-challenge.sso.bbdevs.com", "content")

        # Verify API was called with root domain
        mock_api.delete_dns_records_v1.assert_called_once()
        call_args = mock_api.delete_dns_records_v1.call_args
        assert call_args[0][0] == "bbdevs.com"  # First arg should be root domain

    @patch.object(_HostingerClient, "_get_api_client")
    def test_del_txt_record_uses_filters(self, mock_get_client, api_token, test_domain):
        """Test that del_txt_record uses filters for deletion."""
        # Setup mocks
        mock_api = Mock()
        mock_api.delete_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.del_txt_record(test_domain, "_acme-challenge.bbdevs.com", "content")

        # Verify delete was called with filters
        mock_api.delete_dns_records_v1.assert_called_once()
        call_args = mock_api.delete_dns_records_v1.call_args
        request_obj = call_args[0][1]  # Second arg is the request object

        # The request object should have filters
        assert hasattr(request_obj, "filters")
        assert len(request_obj.filters) > 0

    @patch.object(_HostingerClient, "_get_api_client")
    def test_del_txt_record_api_error_caught(self, mock_get_client, api_token, test_domain):
        """Test that API errors during deletion are caught and logged as warnings."""
        # Setup mocks to raise an exception
        mock_api = Mock()
        mock_api.delete_dns_records_v1 = Mock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # Should not raise exception, just log warning
        client.del_txt_record(test_domain, "_acme-challenge.bbdevs.com", "content")

        # Verify delete was attempted
        mock_api.delete_dns_records_v1.assert_called_once()


class TestSubdomainExtraction:
    """Test subdomain extraction logic in add_txt_record and del_txt_record."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_extract_subdomain_from_acme_challenge(self, mock_get_client, api_token):
        """Test extracting subdomain from _acme-challenge record name."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # For sso.bbdevs.com, record name is _acme-challenge.sso.bbdevs.com
        # Should extract "_acme-challenge.sso" as subdomain for bbdevs.com zone
        client.add_txt_record("sso.bbdevs.com", "_acme-challenge.sso.bbdevs.com", "content", 300)

        # Verify the call used root domain
        mock_api.get_dns_records_v1.assert_called_once_with("bbdevs.com")

        # Verify the update contains the correct subdomain
        call_args = mock_api.update_dns_records_v1.call_args
        request_obj = call_args[0][1]
        zone_record = request_obj.zone[0]
        assert zone_record.name == "_acme-challenge.sso"

    @patch.object(_HostingerClient, "_get_api_client")
    def test_root_domain_uses_at_symbol(self, mock_get_client, api_token):
        """Test that root domain uses @ for subdomain."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # For root domain bbdevs.com with record name bbdevs.com
        # Should use "@" as subdomain
        client.add_txt_record("bbdevs.com", "bbdevs.com", "content", 300)

        # Verify the update contains @ as subdomain
        call_args = mock_api.update_dns_records_v1.call_args
        request_obj = call_args[0][1]
        zone_record = request_obj.zone[0]
        assert zone_record.name == "@"
