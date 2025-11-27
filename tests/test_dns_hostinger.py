"""Basic tests for certbot-dns-hostinger package structure and imports."""

import pytest
import os


class TestPackageStructure:
    """Test package directory structure."""

    def test_package_root_exists(self):
        """Test that package root directory exists."""
        assert os.path.exists("certbot_dns_hostinger")

    def test_internal_module_exists(self):
        """Test that _internal module directory exists."""
        assert os.path.exists("certbot_dns_hostinger/_internal")

    def test_main_module_exists(self):
        """Test that main plugin file exists."""
        assert os.path.exists("certbot_dns_hostinger/_internal/dns_hostinger.py")

    def test_init_files_exist(self):
        """Test that __init__.py files exist."""
        assert os.path.exists("certbot_dns_hostinger/__init__.py")
        assert os.path.exists("certbot_dns_hostinger/_internal/__init__.py")


class TestProjectFiles:
    """Test project configuration files."""

    def test_pyproject_exists(self):
        """Test that pyproject.toml exists."""
        assert os.path.exists("pyproject.toml")

    def test_readme_exists(self):
        """Test that README exists."""
        # Could be either .md or .rst
        assert os.path.exists("README.md") or os.path.exists("README.rst")

    def test_manifest_exists(self):
        """Test that MANIFEST.in exists."""
        assert os.path.exists("MANIFEST.in")


class TestImports:
    """Test that package imports work correctly."""

    def test_import_authenticator(self):
        """Test that Authenticator can be imported from package."""
        from certbot_dns_hostinger import Authenticator

        assert Authenticator is not None

    def test_authenticator_has_description(self):
        """Test that Authenticator has required attributes."""
        from certbot_dns_hostinger import Authenticator

        assert hasattr(Authenticator, "description")
        assert isinstance(Authenticator.description, str)

    def test_authenticator_has_ttl(self):
        """Test that Authenticator has TTL attribute."""
        from certbot_dns_hostinger import Authenticator

        assert hasattr(Authenticator, "ttl")
        assert isinstance(Authenticator.ttl, int)


class TestPackageMetadata:
    """Test package metadata from pyproject.toml."""

    def test_pyproject_has_project_section(self):
        """Test that pyproject.toml has [project] section."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
            assert "[project]" in content

    def test_pyproject_has_name(self):
        """Test that pyproject.toml defines package name."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
            assert 'name = "certbot-dns-hostinger"' in content

    def test_pyproject_has_dependencies(self):
        """Test that pyproject.toml defines dependencies."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
            assert "dependencies" in content
            assert "certbot" in content
            assert "hostinger-api" in content

    def test_pyproject_has_entry_point(self):
        """Test that pyproject.toml defines plugin entry point."""
        with open("pyproject.toml", "r") as f:
            content = f.read()
            assert '[project.entry-points."certbot.plugins"]' in content
            assert "dns-hostinger" in content


class TestTestInfrastructure:
    """Test that test infrastructure is set up correctly."""

    def test_tests_directory_exists(self):
        """Test that tests directory exists."""
        assert os.path.exists("tests")

    def test_conftest_exists(self):
        """Test that pytest conftest.py exists."""
        assert os.path.exists("tests/conftest.py")

    def test_pytest_ini_should_exist(self):
        """Test that pytest.ini should exist (may not be created yet)."""
        # This is a soft check - pytest.ini might not exist in early development
        if os.path.exists("pytest.ini"):
            with open("pytest.ini", "r") as f:
                content = f.read()
                assert "[pytest]" in content or "[tool:pytest]" in content


class TestCredentialsExample:
    """Test credentials example file."""

    def test_credentials_example_exists(self):
        """Test that credentials example file exists."""
        assert os.path.exists("credentials.ini.example")

    def test_credentials_example_format(self):
        """Test that credentials example has correct format."""
        with open("credentials.ini.example", "r") as f:
            content = f.read()
            assert "dns_hostinger_api_token" in content
