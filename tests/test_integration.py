"""Integration tests for certbot-dns-hostinger plugin."""

from unittest.mock import Mock, patch

import pytest
from certbot import errors

from certbot_dns_hostinger._internal.dns_hostinger import Authenticator, _HostingerClient


class TestFullCertificateFlow:
    """Test full certificate issuance flow."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_add_and_cleanup_challenge(
        self, mock_get_client, mock_super_init, mock_certbot_config, api_token
    ):
        """Test complete add and cleanup flow for a single domain."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        domain = "bbdevs.com"
        validation_name = "_acme-challenge.bbdevs.com"
        validation = "test-challenge-content"

        # Perform challenge
        auth._perform(domain, validation_name, validation)

        # Verify record was added
        mock_client.add_txt_record.assert_called_once_with(
            domain, validation_name, validation, auth.ttl
        )

        # Cleanup challenge
        auth._cleanup(domain, validation_name, validation)

        # Verify record was deleted
        mock_client.del_txt_record.assert_called_once_with(domain, validation_name, validation)


class TestWildcardCertificates:
    """Test wildcard certificate scenarios."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_wildcard_domain_challenge(self, mock_get_client, mock_super_init, mock_certbot_config):
        """Test challenge for wildcard domain (*.bbdevs.com)."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        # For *.bbdevs.com, certbot uses bbdevs.com as domain
        domain = "bbdevs.com"
        validation_name = "_acme-challenge.bbdevs.com"
        validation = "wildcard-challenge"

        auth._perform(domain, validation_name, validation)

        mock_client.add_txt_record.assert_called_once()
        call_args = mock_client.add_txt_record.call_args
        assert call_args[0][0] == domain
        assert call_args[0][1] == validation_name


class TestSubdomainCertificates:
    """Test subdomain certificate scenarios."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_subdomain_uses_root_domain_zone(self, mock_get_client, api_token):
        """Test that subdomain certificates use root domain zone."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # Certificate for sso.bbdevs.com
        domain = "sso.bbdevs.com"
        validation_name = "_acme-challenge.sso.bbdevs.com"
        validation = "subdomain-challenge"

        client.add_txt_record(domain, validation_name, validation, 300)

        # Should use root domain (bbdevs.com) for API calls
        mock_api.get_dns_records_v1.assert_called_once_with("bbdevs.com")
        mock_api.update_dns_records_v1.assert_called_once()

        # Verify domain used in update call
        update_call_args = mock_api.update_dns_records_v1.call_args
        assert update_call_args[0][0] == "bbdevs.com"

    @patch.object(_HostingerClient, "_get_api_client")
    def test_nested_subdomain_uses_root_domain(self, mock_get_client, api_token):
        """Test that nested subdomains use root domain zone."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # Certificate for auth.sso.bbdevs.com
        domain = "auth.sso.bbdevs.com"
        validation_name = "_acme-challenge.auth.sso.bbdevs.com"
        validation = "nested-subdomain-challenge"

        client.add_txt_record(domain, validation_name, validation, 300)

        # Should use root domain (bbdevs.com) for API calls
        mock_api.get_dns_records_v1.assert_called_once_with("bbdevs.com")


class TestConcurrentChallenges:
    """Test multiple domains in single certificate."""

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_multiple_domain_challenges(
        self, mock_get_client, mock_super_init, mock_certbot_config
    ):
        """Test handling multiple domains (e.g., bbdevs.com and *.bbdevs.com)."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        # First domain: bbdevs.com
        auth._perform("bbdevs.com", "_acme-challenge.bbdevs.com", "challenge-1")

        # Second domain: *.bbdevs.com (uses same base domain)
        auth._perform("bbdevs.com", "_acme-challenge.bbdevs.com", "challenge-2")

        # Should have called add_txt_record twice
        assert mock_client.add_txt_record.call_count == 2

    @patch("certbot_dns_hostinger._internal.dns_hostinger.dns_common.DNSAuthenticator.__init__")
    @patch.object(Authenticator, "_get_hostinger_client")
    def test_different_domains_in_san_cert(
        self, mock_get_client, mock_super_init, mock_certbot_config
    ):
        """Test SAN certificate with different domains."""
        mock_super_init.return_value = None
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        auth = Authenticator(mock_certbot_config, "dns-hostinger")

        # Multiple domains in SAN
        domains = [
            ("bbdevs.com", "_acme-challenge.bbdevs.com"),
            ("eduoraa.com", "_acme-challenge.eduoraa.com"),
        ]

        for domain, validation_name in domains:
            auth._perform(domain, validation_name, f"challenge-{domain}")

        # Should have called add_txt_record for each domain
        assert mock_client.add_txt_record.call_count == len(domains)


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_api_error_during_add_record(self, mock_get_client, api_token):
        """Test that API errors during add are properly raised."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        with pytest.raises(errors.PluginError) as exc_info:
            client.add_txt_record("bbdevs.com", "_acme-challenge.bbdevs.com", "content", 300)

        assert "Encountered error adding TXT record" in str(exc_info.value)

    @patch.object(_HostingerClient, "_get_api_client")
    def test_api_error_during_delete_is_logged(self, mock_get_client, api_token):
        """Test that API errors during delete are caught and logged."""
        mock_api = Mock()
        mock_api.delete_dns_records_v1 = Mock(side_effect=Exception("API Error"))
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)

        # Should not raise exception
        client.del_txt_record("bbdevs.com", "_acme-challenge.bbdevs.com", "content")

        # Verify delete was attempted
        mock_api.delete_dns_records_v1.assert_called_once()


class TestConflictingRecords:
    """Test handling of conflicting DNS records."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_replaces_existing_acme_challenge(self, mock_get_client, api_token, mock_dns_records):
        """Test that existing ACME challenge is replaced."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=mock_dns_records)
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record("bbdevs.com", "_acme-challenge.bbdevs.com", "new-challenge", 300)

        # Should call DELETE to remove existing record
        mock_api.delete_dns_records_v1.assert_called_once()

        # Then call UPDATE to add new record
        mock_api.update_dns_records_v1.assert_called_once()

    @patch.object(_HostingerClient, "_get_api_client")
    def test_preserves_other_dns_records(self, mock_get_client, api_token, mock_dns_records):
        """Test that non-ACME DNS records are not affected."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=mock_dns_records)
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record("bbdevs.com", "_acme-challenge.bbdevs.com", "challenge", 300)

        # Verify update uses overwrite=False
        update_call_args = mock_api.update_dns_records_v1.call_args
        request_obj = update_call_args[0][1]
        assert request_obj.overwrite is False


class TestDifferentTLDs:
    """Test with different TLD domains."""

    @patch.object(_HostingerClient, "_get_api_client")
    def test_com_domain(self, mock_get_client, api_token):
        """Test with .com domain."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record("example.com", "_acme-challenge.example.com", "content", 300)

        mock_api.get_dns_records_v1.assert_called_once_with("example.com")

    @patch.object(_HostingerClient, "_get_api_client")
    def test_org_domain(self, mock_get_client, api_token):
        """Test with .org domain."""
        mock_api = Mock()
        mock_api.get_dns_records_v1 = Mock(return_value=[])
        mock_api.delete_dns_records_v1 = Mock()
        mock_api.update_dns_records_v1 = Mock()
        mock_get_client.return_value = mock_api

        client = _HostingerClient(api_token)
        client.add_txt_record("example.org", "_acme-challenge.example.org", "content", 300)

        mock_api.get_dns_records_v1.assert_called_once_with("example.org")
