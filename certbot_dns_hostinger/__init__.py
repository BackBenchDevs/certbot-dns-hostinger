"""
Certbot DNS plugin for Hostinger.

This plugin automates the process of completing a dns-01 challenge by
creating, and subsequently removing, TXT records using the Hostinger API.

Named Arguments:
    --dns-hostinger-credentials PATH
        Hostinger credentials INI file. (Required)

Example:
    certbot certonly \\
        --dns-hostinger \\
        --dns-hostinger-credentials /path/to/credentials.ini \\
        -d example.com

Credentials file should contain:
    dns_hostinger_api_token = <your-api-token>
"""

from ._internal.dns_hostinger import Authenticator

__all__ = ["Authenticator"]
