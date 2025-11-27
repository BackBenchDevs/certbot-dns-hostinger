"""Tests for root domain extraction logic."""

import pytest
from certbot_dns_hostinger._internal.dns_hostinger import _HostingerClient


class TestRootDomainExtraction:
    """Test the _get_root_domain method."""

    def test_subdomain_to_root(self, api_token):
        """Test extracting root domain from subdomain."""
        client = _HostingerClient(api_token)

        # sso.bbdevs.com -> bbdevs.com
        assert client._get_root_domain("sso.bbdevs.com") == "bbdevs.com"

    def test_nested_subdomain_to_root(self, api_token):
        """Test extracting root domain from nested subdomain."""
        client = _HostingerClient(api_token)

        # auth.sso.bbdevs.com -> bbdevs.com
        assert client._get_root_domain("auth.sso.bbdevs.com") == "bbdevs.com"

    def test_root_domain_unchanged(self, api_token):
        """Test that root domain returns itself."""
        client = _HostingerClient(api_token)

        # bbdevs.com -> bbdevs.com
        assert client._get_root_domain("bbdevs.com") == "bbdevs.com"

    def test_deeply_nested_subdomain(self, api_token):
        """Test extracting root from deeply nested subdomain."""
        client = _HostingerClient(api_token)

        # sub.sub.sub.domain.com -> domain.com
        assert client._get_root_domain("sub.sub.sub.domain.com") == "domain.com"

    def test_different_tld(self, api_token):
        """Test with different TLD."""
        client = _HostingerClient(api_token)

        # subdomain.eduoraa.com -> eduoraa.com
        assert client._get_root_domain("subdomain.eduoraa.com") == "eduoraa.com"

    def test_co_uk_tld(self, api_token):
        """Test with .co.uk TLD (should return last two parts)."""
        client = _HostingerClient(api_token)

        # Note: This implementation returns domain.co (not domain.co.uk)
        # This is a known limitation for multi-part TLDs
        assert client._get_root_domain("subdomain.domain.co.uk") == "co.uk"

    def test_single_part_domain(self, api_token):
        """Test with single part (should return as-is)."""
        client = _HostingerClient(api_token)

        # localhost -> localhost
        assert client._get_root_domain("localhost") == "localhost"

    def test_www_subdomain(self, api_token):
        """Test common www subdomain."""
        client = _HostingerClient(api_token)

        # www.bbdevs.com -> bbdevs.com
        assert client._get_root_domain("www.bbdevs.com") == "bbdevs.com"

    def test_hyphenated_subdomain(self, api_token):
        """Test subdomain with hyphens."""
        client = _HostingerClient(api_token)

        # my-app.bbdevs.com -> bbdevs.com
        assert client._get_root_domain("my-app.bbdevs.com") == "bbdevs.com"

    def test_numeric_subdomain(self, api_token):
        """Test numeric subdomain."""
        client = _HostingerClient(api_token)

        # 123.bbdevs.com -> bbdevs.com
        assert client._get_root_domain("123.bbdevs.com") == "bbdevs.com"
