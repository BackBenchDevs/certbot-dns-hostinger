"""DNS Authenticator for Hostinger."""

import logging
import sys
from collections.abc import Callable
from typing import Any

from certbot import errors
from certbot.plugins import dns_common
from certbot.plugins.dns_common import CredentialsConfiguration

# Get our plugin logger and set to DEBUG level
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# Add debug logging for plugin operations
logger.debug("Hostinger DNS plugin logger configured at DEBUG level")

ACCOUNT_URL = "https://hpanel.hostinger.com/domains"


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Hostinger."""

    description = "Obtain certificates using a DNS TXT record (if you are using Hostinger for DNS)."
    ttl = 60

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        logger.info("Initializing Hostinger authenticator")
        super().__init__(*args, **kwargs)
        self.credentials: CredentialsConfiguration | None = None
        logger.info("Hostinger authenticator initialized")

    @classmethod
    def add_parser_arguments(
        cls, add: Callable[..., None], default_propagation_seconds: int = 30
    ) -> None:
        logger.info("Adding parser arguments")
        super().add_parser_arguments(add, default_propagation_seconds)
        add("credentials", help="Hostinger credentials INI file.")
        logger.info("Parser arguments added")

    def more_info(self) -> str:
        logger.info("Getting more info")
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the Hostinger API."
        )

    def _setup_credentials(self) -> None:
        """Setup credentials from the credentials file."""
        logger.info("Setting up credentials")
        self.credentials = self._configure_credentials(
            "credentials", "Hostinger credentials INI file", None, self._validate_credentials
        )
        logger.info("Credentials set up")

    def _validate_credentials(self, credentials: CredentialsConfiguration) -> None:
        logger.info("Validating credentials")
        """Validate that required credentials are present."""
        api_token = credentials.conf("api-token")
        if not api_token:
            raise errors.PluginError(
                "{}: dns_hostinger_api_token is required. "
                f"See {ACCOUNT_URL} for information about creating an API token.".format(
                    credentials.confobj.filename
                )
            )
        logger.info("Credentials validated")

    def _perform(self, domain: str, validation_name: str, validation: str) -> None:
        """Perform the DNS challenge."""
        logger.debug(f"Starting DNS challenge for domain: {domain}")
        logger.debug(f"Validation name: {validation_name}")
        logger.debug(f"Validation content: {validation}")
        logger.debug(f"TTL: {self.ttl}")

        self._get_hostinger_client().add_txt_record(domain, validation_name, validation, self.ttl)
        logger.info("DNS challenge performed successfully")
        logger.debug(f"DNS challenge completed for domain: {domain}")

    def _cleanup(self, domain: str, validation_name: str, validation: str) -> None:
        """Clean up the DNS challenge."""
        logger.debug(f"Starting DNS cleanup for domain: {domain}")
        logger.debug(f"Validation name: {validation_name}")
        logger.debug(f"Validation content: {validation}")

        self._get_hostinger_client().del_txt_record(domain, validation_name, validation)
        logger.info("DNS challenge cleaned up successfully")
        logger.debug(f"DNS cleanup completed for domain: {domain}")

    def _get_hostinger_client(self) -> "_HostingerClient":
        logger.info("Getting Hostinger client")
        """Returns an instance of the Hostinger client."""
        if not self.credentials:
            msg = "Plugin has not been prepared."
            raise errors.Error(msg)
        return _HostingerClient(self.credentials.conf("api-token"))
        logger.info("Hostinger client obtained")
        return None


class _HostingerClient:
    """Encapsulates all communication with the Hostinger API."""

    def __init__(self, api_token: str) -> None:
        logger.info("Initializing Hostinger client")
        self.api_token = api_token
        self._api_client = None
        logger.info("Hostinger client initialized")

    def _get_api_client(self):
        """Get the Hostinger API client."""
        if self._api_client is None:
            try:
                logger.info("Initializing Hostinger API client")
                from hostinger_api import ApiClient, Configuration, DNSZoneApi

                config = Configuration(access_token=self.api_token)
                api_client = ApiClient(config)
                self._api_client = DNSZoneApi(api_client)
                logger.info("Hostinger API client initialized")
            except ImportError as e:
                logger.exception("Encountered error initializing Hostinger API client")
                msg = (
                    "Could not import hostinger-api. Please install it with: "
                    "pip install hostinger-api"
                )
                raise errors.PluginError(
                    msg
                ) from e
        logger.info("Hostinger API client obtained")
        return self._api_client

    def _get_root_domain(self, domain: str) -> str:
        """
        Extract root domain from subdomain.

        Examples:
            sso.bbdevs.com -> bbdevs.com
            auth.sso.bbdevs.com -> bbdevs.com
            bbdevs.com -> bbdevs.com
            eduoraa.com -> eduoraa.com
        """
        parts = domain.split(".")
        if len(parts) >= 2:
            # Return last two parts (domain.tld)
            root = ".".join(parts[-2:])
            logger.debug(f"Extracted root domain: {root} from {domain}")
            return root
        return domain

    def add_txt_record(self, domain: str, record_name: str, record_content: str, ttl: int) -> None:
        """Add a TXT record using the Hostinger API."""
        logger.info("Adding TXT record")
        try:
            api_client = self._get_api_client()

            # Extract root domain for API calls (e.g., sso.bbdevs.com -> bbdevs.com)
            root_domain = self._get_root_domain(domain)

            # Extract subdomain from record_name for the record itself
            # e.g., "_acme-challenge.sso.bbdevs.com" -> "_acme-challenge.sso"
            if record_name.endswith(f".{root_domain}"):
                subdomain = record_name[: -len(f".{root_domain}")]
            elif record_name == root_domain:
                subdomain = "@"
            else:
                subdomain = record_name

            logger.debug(f"Using root domain: {root_domain}, subdomain: {subdomain}")

            # Import models
            from hostinger_api.models import (
                DNSV1ZoneDestroyRequest,
                DNSV1ZoneDestroyRequestFiltersInner,
                DNSV1ZoneUpdateRequest,
                DNSV1ZoneUpdateRequestZoneInner,
                DNSV1ZoneUpdateRequestZoneInnerRecordsInner,
            )

            # Step 1: GET - Read existing records to check for conflicts
            zone_records = api_client.get_dns_records_v1(root_domain)
            existing_acme = [z for z in zone_records if z.name == subdomain and z.type == "TXT"]
            if existing_acme:
                logger.info(f"Found {len(existing_acme)} existing {subdomain} TXT record(s)")

            # Step 2: DELETE - Remove any existing ACME challenge records to avoid conflicts
            if existing_acme:
                try:
                    delete_filter = DNSV1ZoneDestroyRequestFiltersInner(name=subdomain, type="TXT")
                    delete_request = DNSV1ZoneDestroyRequest(filters=[delete_filter])
                    api_client.delete_dns_records_v1(root_domain, delete_request)
                    logger.info(f"Deleted existing {subdomain} TXT record(s) from {root_domain}")
                except Exception as delete_error:
                    logger.warning(f"Error deleting existing records: {delete_error}")

            # Step 3: ADD - Add the new ACME challenge record
            new_zone = DNSV1ZoneUpdateRequestZoneInner(
                name=subdomain,
                type="TXT",
                ttl=ttl,
                records=[DNSV1ZoneUpdateRequestZoneInnerRecordsInner(content=record_content)],
            )

            # Use overwrite=False to only add this record without affecting others
            update_request = DNSV1ZoneUpdateRequest(zone=[new_zone], overwrite=False)
            api_client.update_dns_records_v1(root_domain, update_request)
            logger.info(f"Successfully added TXT record {subdomain} to {root_domain} zone")

        except Exception as e:
            logger.exception("Encountered error adding TXT record")
            msg = f"Encountered error adding TXT record: {e}"
            raise errors.PluginError(msg) from e

    def del_txt_record(self, domain: str, record_name: str, _record_content: str) -> None:
        """Delete a TXT record using the Hostinger API."""
        logger.info("Deleting TXT record")
        try:
            api_client = self._get_api_client()

            # Extract root domain for API calls (e.g., sso.bbdevs.com -> bbdevs.com)
            root_domain = self._get_root_domain(domain)

            # Extract subdomain from record_name for the record itself
            # e.g., "_acme-challenge.sso.bbdevs.com" -> "_acme-challenge.sso"
            if record_name.endswith(f".{root_domain}"):
                subdomain = record_name[: -len(f".{root_domain}")]
            elif record_name == root_domain:
                subdomain = "@"
            else:
                subdomain = record_name

            logger.debug(f"Deleting from root domain: {root_domain}, subdomain: {subdomain}")

            # Import models
            from hostinger_api.models import (
                DNSV1ZoneDestroyRequest,
                DNSV1ZoneDestroyRequestFiltersInner,
            )

            # Use DELETE endpoint with name+type filter to remove the specific record
            delete_filter = DNSV1ZoneDestroyRequestFiltersInner(name=subdomain, type="TXT")
            delete_request = DNSV1ZoneDestroyRequest(filters=[delete_filter])
            api_client.delete_dns_records_v1(root_domain, delete_request)
            logger.info(f"Successfully deleted TXT record {subdomain} from {root_domain} zone")

        except Exception as e:
            logger.warning(f"Encountered error deleting TXT record: {e}")
