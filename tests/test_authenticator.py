"""Tests for Authenticator class."""

from unittest.mock import Mock, patch

import pytest
from certbot import errors

from certbot_dns_hostinger._internal.dns_hostinger import Authenticator


class TestAuthenticatorInit:
    """Test Authenticator initialization."""

    def test_authenticator_has_description(self):
        """Test that authenticator has a description."""
        assert hasattr(Authenticator, "description")
        assert "DNS TXT record" in Authenticator.description
        assert "Hostinger" in Authenticator.description

    def test_authenticator_has_ttl(self):
        """Test that authenticator has default TTL."""
        assert hasattr(Authenticator, "ttl")
        assert Authenticator.ttl == 60

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_authenticator_initialization(self, mock_super_init, mock_certbot_config):
        """Test authenticator initializes correctly."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        assert auth.credentials is None
        mock_super_init.assert_called_once()


class TestAuthenticatorMetadata:
    """Test authenticator metadata methods."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_more_info(self, mock_super_init, mock_certbot_config):
        """Test more_info returns description."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")
        info = auth.more_info()

        assert "DNS TXT record" in info
        assert "Hostinger API" in info

    def test_add_parser_arguments(self):
        """Test that parser arguments are added."""
        mock_add = Mock()

        Authenticator.add_parser_arguments(mock_add, default_propagation_seconds=30)

        # Should call super's add_parser_arguments and add credentials argument
        assert mock_add.called
        # Check that credentials argument was added
        calls = [str(call) for call in mock_add.call_args_list]
        assert any("credentials" in str(call) for call in calls)


class TestCredentials:
    """Test credential setup and validation."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_configure_credentials")
    def test_setup_credentials(self, mock_configure, mock_super_init, mock_certbot_config):
        """Test credentials setup."""
        mock_super_init.return_value = None
        mock_creds = Mock()
        mock_configure.return_value = mock_creds

        auth = Authenticator(mock_certbot_config, "dns-hostinger")
        auth._setup_credentials()

        assert auth.credentials == mock_creds
        mock_configure.assert_called_once_with(
            "credentials", "Hostinger credentials INI file", None, auth._validate_credentials
        )

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_validate_credentials_success(self, mock_super_init, mock_certbot_config, api_token):
        """Test successful credential validation."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        mock_creds = Mock()
        mock_creds.conf = Mock(return_value=api_token)
        mock_creds.confobj.filename = "/path/to/credentials.ini"

        # Should not raise exception
        auth._validate_credentials(mock_creds)
        mock_creds.conf.assert_called_once_with("api-token")

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_validate_credentials_missing_token(self, mock_super_init, mock_certbot_config):
        """Test credential validation fails with missing token."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        mock_creds = Mock()
        mock_creds.conf = Mock(return_value=None)  # Missing token
        mock_creds.confobj.filename = "/path/to/credentials.ini"

        with pytest.raises(errors.PluginError) as exc_info:
            auth._validate_credentials(mock_creds)

        assert "dns_hostinger_api_token is required" in str(exc_info.value)

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_validate_credentials_empty_token(self, mock_super_init, mock_certbot_config):
        """Test credential validation fails with empty token."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        mock_creds = Mock()
        mock_creds.conf = Mock(return_value="")  # Empty token
        mock_creds.confobj.filename = "/path/to/credentials.ini"

        with pytest.raises(errors.PluginError) as exc_info:
            auth._validate_credentials(mock_creds)

        assert "dns_hostinger_api_token is required" in str(exc_info.value)


class TestGetHostingerClient:
    """Test _get_hostinger_client method."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch("certbot_dns_hostinger._internal.dns_hostinger._HostingerClient")
    def test_get_client_with_credentials(
        self, mock_client_class, mock_super_init, mock_certbot_config, api_token
    ):
        """Test getting Hostinger client with valid credentials."""
        mock_super_init.return_value = None
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        # Setup credentials
        mock_creds = Mock()
        mock_creds.conf = Mock(return_value=api_token)
        auth.credentials = mock_creds

        client = auth._get_hostinger_client()

        assert client == mock_client_instance
        mock_client_class.assert_called_once_with(api_token)

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    def test_get_client_without_credentials(self, mock_super_init, mock_certbot_config):
        """Test getting Hostinger client without credentials fails."""
        mock_super_init.return_value = None

        auth = Authenticator(mock_certbot_config, "dns-hostinger")
        # Don't set credentials

        with pytest.raises(errors.Error) as exc_info:
            auth._get_hostinger_client()

        assert "Plugin has not been prepared" in str(exc_info.value)


class TestPerformChallenge:
    """Test _perform method for DNS challenge."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_perform_challenge(self, mock_get_client, mock_super_init, mock_certbot_config):
        """Test performing DNS challenge."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        domain = "bbdevs.com"
        validation_name = "_acme-challenge.bbdevs.com"
        validation = "challenge-content"

        auth._perform(domain, validation_name, validation)

        mock_client.add_txt_record.assert_called_once_with(
            domain, validation_name, validation, auth.ttl
        )

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_perform_uses_correct_ttl(self, mock_get_client, mock_super_init, mock_certbot_config):
        """Test that _perform uses the correct TTL."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")
        auth.ttl = 300  # Set custom TTL

        domain = "bbdevs.com"
        validation_name = "_acme-challenge.bbdevs.com"
        validation = "challenge-content"

        auth._perform(domain, validation_name, validation)

        # Verify TTL is passed correctly
        call_args = mock_client.add_txt_record.call_args
        assert call_args[0][3] == 300


class TestCleanupChallenge:
    """Test _cleanup method for DNS challenge."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_cleanup_challenge(self, mock_get_client, mock_super_init, mock_certbot_config):
        """Test cleaning up DNS challenge."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        domain = "bbdevs.com"
        validation_name = "_acme-challenge.bbdevs.com"
        validation = "challenge-content"

        auth._cleanup(domain, validation_name, validation)

        mock_client.del_txt_record.assert_called_once_with(domain, validation_name, validation)

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_cleanup_with_different_domain(
        self, mock_get_client, mock_super_init, mock_certbot_config
    ):
        """Test cleanup with subdomain."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        domain = "sso.bbdevs.com"
        validation_name = "_acme-challenge.sso.bbdevs.com"
        validation = "challenge-content"

        auth._cleanup(domain, validation_name, validation)

        # Verify cleanup is called with correct parameters
        mock_client.del_txt_record.assert_called_once_with(domain, validation_name, validation)
