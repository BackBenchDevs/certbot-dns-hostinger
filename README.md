# Certbot DNS Plugin for Hostinger

[![PyPI version](https://img.shields.io/pypi/v/certbot-dns-hostinger.svg)](https://pypi.org/project/certbot-dns-hostinger/)
[![Python versions](https://img.shields.io/pypi/pyversions/certbot-dns-hostinger.svg)](https://pypi.org/project/certbot-dns-hostinger/)
[![License](https://img.shields.io/pypi/l/certbot-dns-hostinger.svg)](https://github.com/BackBenchDevs/certbot-dns-hostinger/blob/main/LICENSE)
[![Certbot version](https://img.shields.io/badge/certbot-%3E%3D4.2.0-blue.svg)](https://pypi.org/project/certbot/)
[![Downloads](https://pepy.tech/badge/certbot-dns-hostinger)](https://pepy.tech/project/certbot-dns-hostinger/)

This plugin automates the process of completing a `dns-01` challenge by creating, and subsequently removing, TXT records using the Hostinger API.

## Installation

```bash
pip install certbot-dns-hostinger
```

## Usage

```bash
certbot certonly \
    --dns-hostinger \
    --dns-hostinger-credentials /path/to/credentials.ini \
    -d example.com
```

## Named Arguments

`--dns-hostinger-credentials PATH`
- Hostinger credentials INI file. (Required)

## Credentials

Create a credentials file:

```ini
# /path/to/credentials.ini
dns_hostinger_api_token = <your-api-token>
```

The file should be readable by the Certbot process and secure (`chmod 600`).

## API Token

To obtain an API token:

1. Log in to your Hostinger account
2. Go to [https://hpanel.hostinger.com/domains](https://hpanel.hostinger.com/domains)
3. Navigate to API section
4. Generate a new API token with DNS management permissions

## Examples

Obtain a single certificate for all subdomains of a domain:

```bash
certbot certonly \
    --dns-hostinger \
    --dns-hostinger-credentials ~/.secrets/certbot/hostinger.ini \
    -d example.com \
    -d *.example.com
```

Use a custom propagation delay:

```bash
certbot certonly \
    --dns-hostinger \
    --dns-hostinger-credentials ~/.secrets/certbot/hostinger.ini \
    --dns-hostinger-propagation-seconds 120 \
    -d example.com
```

## Troubleshooting

If you encounter any issues, check:

1. API token is correct and has proper permissions
2. Domain is managed by Hostinger
3. Credentials file is readable and secure
4. Network connectivity to Hostinger API

For more information, see the [Certbot documentation](https://eff-certbot.readthedocs.io/).
